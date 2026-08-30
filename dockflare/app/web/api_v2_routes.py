# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# dockflare/app/web/api_v2_routes.py
import copy
import hashlib
import logging
import time
import json
from datetime import datetime, timezone, timedelta
import secrets
import uuid
from flask import Blueprint, jsonify, request, current_app, url_for
from flask_login import login_required

from app import config, docker_client, tunnel_state, cloudflared_agent_state, publish_state_event
from app.core.state_manager import (
    managed_rules, access_groups, agents, state_lock, save_state,
    add_agent, get_agent, update_agent, list_agents, remove_agent, add_agent_key, revoke_agent_key, find_agent_id_by_key, list_agent_keys, get_agent_key_info,
    get_services_snapshot, cleanup_expired_revoked_keys, get_revoked_keys_summary,
    save_identity_provider, get_identity_provider, delete_identity_provider, list_identity_providers, get_idp_by_cloudflare_id, get_idp_id_by_name,
    agent_inventory_contains_rule, find_container_rule,
    mark_rule_tunnel_sync_pending, restore_rule_lifecycle
)
from app.core import agent_key_store
from app.core import agent_decommission
from app.core.tunnel_manager import (
    start_cloudflared_container,
    stop_cloudflared_container,
    update_cloudflare_config
)
from app.core.cloudflare_api import (
    get_all_account_cloudflare_tunnels,
    get_dns_records_for_tunnel,
    create_cloudflare_dns_record,
    delete_cloudflare_dns_record,
    get_zone_id_from_name,
    delete_tunnel_via_api,
    list_account_zones,
    get_account_zone_inventory,
    resolve_account_zone
)
from app.core.zone_resolver import ZoneResolutionError
from app.core.access_manager import (
    delete_cloudflare_access_application,
    create_cloudflare_access_application,
    update_cloudflare_access_application,
    generate_access_app_config_hash,
    find_cloudflare_access_application_by_domain,
    handle_access_policy_from_labels,
    get_access_group_allowed_idps,
    resolve_access_group_policies
)
from app.core.reconciler import reconcile_state_threaded
from app.core.docker_handler import is_valid_hostname, is_valid_service
from app.core.utils import get_rule_key, get_source_rule_key, get_label, normalize_access_group_value, normalize_path_value
#----------------------------------------------------------!
# UI endpoints are protected by session auth   nicht vergessen, immer checken bei änderungen.. don't waste time            !
#----------------------------------------------------------!
api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

_AGENT_ENDPOINT_ALLOWLIST = {
    'api_v2.agents_register',
    'api_v2.agents_get_commands',
    'api_v2.agents_post_events',
    'api_v2.agents_decommission_ack',
}

_UI_ENDPOINT_ALLOWLIST = {
    'api_v2.manage_auth_settings',
    'api_v2.manage_auth_providers',
    'api_v2.manage_auth_provider',
    'api_v2.manage_auth_users',
    'api_v2.manage_auth_user',
    'api_v2.api_get_idp_types',
    'api_v2.api_list_idps',
    'api_v2.api_sync_idps',
    'api_v2.api_create_idp',
    'api_v2.api_get_idp',
    'api_v2.api_update_idp',
    'api_v2.api_delete_idp',
    'api_v2.get_zone_policies_api',
}


@api_v2_bp.before_request
def _enforce_master_api_key():
    endpoint = request.endpoint
    if not endpoint or not endpoint.startswith('api_v2.'):
        return
    if request.method == 'OPTIONS':
        return

    if endpoint in _AGENT_ENDPOINT_ALLOWLIST:
        return
    
    if endpoint in _UI_ENDPOINT_ALLOWLIST:
        return

    expected_key = current_app.config.get('MASTER_API_KEY') or config.MASTER_API_KEY
    if not expected_key:
        logging.warning("MASTER_AUTH: Master API key not configured; rejecting %s", endpoint)
        return jsonify({"status": "error", "message": "master_api_key_not_configured"}), 503
    provided_token = _extract_bearer_token()
    if provided_token and secrets.compare_digest(provided_token, expected_key):
        return
    logging.warning("MASTER_AUTH: Unauthorized request for %s from %s", endpoint, request.remote_addr)
    return jsonify({"status": "error", "message": "unauthorized"}), 401

_MANUAL_RULE_LIMITER = {}
MANUAL_RULE_WINDOW_SECONDS = 60
MANUAL_RULE_MAX_REQUESTS = 5

def serialize_rule(rule_data):
    if not rule_data:
        return None
    serialized = copy.deepcopy(rule_data)
    if "delete_at" in serialized and isinstance(serialized["delete_at"], datetime):
        dt_obj = serialized["delete_at"]
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        else:
            dt_obj = dt_obj.astimezone(timezone.utc)
        serialized["delete_at"] = dt_obj.isoformat()
    return serialized


_PUBLIC_AGENT_FIELDS = {
    "id", "display_name", "version", "status", "last_seen",
    "assigned_tunnel_id", "assigned_tunnel_name", "migration_status",
    "tunnel_status", "connector_version", "connector_origin_ip",
    "connector_platform", "connector_colos",
    "decommission_operation_id", "decommission_state", "capabilities",
}
_PUBLIC_AGENT_KEY_FIELDS = {
    "owner", "created_at", "status", "last_used_at", "bound_agent_id",
    "revoked_at",
}
_PUBLIC_TUNNEL_FIELDS = {"id", "name", "status", "created_at", "deleted_at"}


def _agent_key_reference(key_token):
    """Return a stable non-secret identifier for an Agent API key."""
    return hashlib.sha256(key_token.encode("utf-8")).hexdigest()


def _resolve_agent_key_identifier(identifier):
    """Resolve a public key reference, retaining raw-key API compatibility."""
    keys = list_agent_keys()
    if identifier in keys:
        return identifier
    for key_token in keys:
        if secrets.compare_digest(_agent_key_reference(key_token), identifier):
            return key_token
    return None


def _serialize_agent_keys(keys):
    return {
        _agent_key_reference(key_token): {
            field: copy.deepcopy(metadata[field])
            for field in _PUBLIC_AGENT_KEY_FIELDS
            if field in metadata
        }
        for key_token, metadata in keys.items()
        if isinstance(key_token, str) and isinstance(metadata, dict)
    }


def _serialize_agent(agent_id, agent_data, now_dt, heartbeat_timeout):
    source = agent_data if isinstance(agent_data, dict) else {}
    result = {
        field: copy.deepcopy(source[field])
        for field in _PUBLIC_AGENT_FIELDS
        if field in source
    }
    result["id"] = agent_id
    online = False
    try:
        last_seen = result.get("last_seen")
        if last_seen:
            last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
            if last_seen_dt.tzinfo is None:
                last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
            online = (now_dt - last_seen_dt.astimezone(timezone.utc)).total_seconds() <= heartbeat_timeout
    except (TypeError, ValueError):
        online = False
    result["online"] = online
    result["health"] = "connected" if online else "disconnected"
    return result


def _serialize_tunnels(tunnels):
    return [
        {field: tunnel[field] for field in _PUBLIC_TUNNEL_FIELDS if field in tunnel}
        for tunnel in tunnels or []
        if isinstance(tunnel, dict)
    ]

def _ensure_agent_api_key(agent_id, agent_record, token):
    key_info = get_agent_key_info(token)
    if not key_info:
        logging.warning("AGENT_AUTH: Token missing from key registry during agent verification.")
        return False

    status = key_info.get("status", "active")
    if status != "active":
        logging.warning(f"AGENT_AUTH: Token for agent {agent_id} is not active (status={status}).")
        return False

    bound_agent_id = key_info.get("bound_agent_id")
    stored_token = agent_record.get("api_key")
    if bound_agent_id and bound_agent_id != agent_id:
        logging.warning(f"AGENT_AUTH: Key binding mismatch for agent {agent_id}.")
        return False
    if stored_token is not None and stored_token != token:
        logging.warning(f"AGENT_AUTH: Token mismatch for agent {agent_id}.")
        return False

    meta_update = dict(key_info)
    now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    meta_update["last_used_at"] = now_iso
    if not bound_agent_id:
        logging.warning("AGENT_AUTH: Unbound key rejected outside registration.")
        return False
    add_agent_key(token, meta_update)
    return True

def get_effective_tunnel_id():
    return tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID

@api_v2_bp.route('/services', methods=['GET'])
def list_services():
    snapshot = get_services_snapshot()
    return jsonify({"services": snapshot})

@api_v2_bp.route('/overview', methods=['GET'])
def get_overview_data():
    all_account_tunnels = _serialize_tunnels(get_all_account_cloudflare_tunnels())
    tunnel_status = {
        tunnel["id"]: {"status": tunnel.get("status") or "unknown", "name": tunnel.get("name")}
        for tunnel in all_account_tunnels
        if tunnel.get("id")
    }
    with state_lock:
        rules_for_api = {
            rule_key: serialize_rule(rule_data)
            for rule_key, rule_data in managed_rules.items()
        }
        api_tunnel_state = {
            field: copy.deepcopy(tunnel_state[field])
            for field in ("id", "name", "status", "status_message")
            if field in tunnel_state
        }

    now_dt = datetime.now(timezone.utc)
    heartbeat_timeout = getattr(config, "AGENT_HEARTBEAT_TIMEOUT", 60)
    agents_list_api = {
        agent_id: _serialize_agent(agent_id, agent_data, now_dt, heartbeat_timeout)
        for agent_id, agent_data in list_agents().items()
    }
    for agent_id, processed in agents_list_api.items():
        assigned_tunnel_id = processed.get("assigned_tunnel_id")
        if assigned_tunnel_id in tunnel_status:
            processed["tunnel_status"] = tunnel_status[assigned_tunnel_id]
        if not assigned_tunnel_id:
            continue
        try:
            from app.core.cloudflare_api import get_tunnel_connector_info
            connector = get_tunnel_connector_info(assigned_tunnel_id)
            if connector:
                processed.update({
                    "connector_version": connector.get("version"),
                    "connector_origin_ip": connector.get("origin_ip"),
                    "connector_platform": connector.get("platform"),
                    "connector_colos": connector.get("colos"),
                })
        except Exception as connector_error:
            logging.warning("Could not enrich agent %s with connector info: %s", agent_id, connector_error)

    log_stream_url = "/stream-logs"
    try:
        log_stream_url = url_for('web.stream_logs_route', _external=False)
    except RuntimeError as e:
        logging.error(f"RuntimeError generating url_for for 'web.stream_logs_route': {e}. Falling back to static path.")

    cf_account_id = current_app.config.get("CF_ACCOUNT_ID")
    cf_zone_id = current_app.config.get("CF_ZONE_ID")
    return jsonify({
        "tunnel_state": api_tunnel_state,
        "agent_state": {},
        "initialization": {
            "complete": bool(api_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID),
            "in_progress": not (api_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID)
            and api_tunnel_state.get("status_message", "").lower().startswith("init"),
        },
        "cloudflared_container_name": current_app.config.get('CLOUDFLARED_CONTAINER_NAME'),
        "docker_available": docker_client is not None,
        "external_cloudflared": config.USE_EXTERNAL_CLOUDFLARED,
        "external_tunnel_id": config.EXTERNAL_TUNNEL_ID,
        "rules": rules_for_api,
        "all_account_tunnels": all_account_tunnels,
        "config_status": {
            "cf_account_id_configured": bool(cf_account_id),
            "cf_zone_id_configured": bool(cf_zone_id),
        },
        "reconciliation_info": getattr(current_app, 'reconciliation_info', {
            "in_progress": False, "progress": 0, "total_items": 0,
            "processed_items": 0, "status": "Not started"
        }),
        "agents": agents_list_api,
        "agent_keys": _serialize_agent_keys(list_agent_keys()),
        "log_stream_path": log_stream_url
    })

@api_v2_bp.route('/zones', methods=['GET'])
def list_zones_api():
    force_refresh = request.args.get('refresh') == '1'
    inventory = get_account_zone_inventory(force_refresh=force_refresh)
    if inventory["status"] in {"unavailable", "partial"}:
        return jsonify({"error": "inventory_unavailable", **inventory}), 503
    response = jsonify(inventory["zones"])
    response.headers["X-DockFlare-Zone-Inventory"] = inventory["status"]
    return response

@api_v2_bp.route('/zone-policies', methods=['GET'])
@login_required
def get_zone_policies_api():
    from app.core.access_manager import check_for_tld_access_policy
    from app.core.cache import get_redis_client
    import json
    
    redis_client = get_redis_client()
    cache_key = "zone_policies_cache"
    cache_ttl = 300  # 5 minutes

    if redis_client:
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logging.info("Returning zone policies from Redis cache")
                return jsonify(json.loads(cached_data))
        except Exception as e:
            logging.warning(f"Failed to read from Redis cache: {e}")

    zone_policies = []
    try:
        zones = list_account_zones()
        for zone in zones or []:
            zone_name = zone.get('name')
            if zone_name:
                cf_app_id = check_for_tld_access_policy(zone_name)
                zone_policies.append({
                    'zone_name': zone_name,
                    'zone_id': zone.get('id'),
                    'has_default_policy': bool(cf_app_id),
                    'cf_app_id': cf_app_id or None
                })

        response_data = {"success": True, "zone_policies": zone_policies}

        # Cache the result
        if redis_client:
            try:
                redis_client.setex(cache_key, cache_ttl, json.dumps(response_data))
                logging.info(f"Cached zone policies in Redis (TTL: {cache_ttl}s)")
            except Exception as e:
                logging.warning(f"Failed to write to Redis cache: {e}")

        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error fetching zone default policies: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

def _check_manual_rule_rate_limit():
    ip = request.remote_addr or 'global'
    now = time.time()
    record = _MANUAL_RULE_LIMITER.get(ip)
    if record:
        if now - record["start"] > MANUAL_RULE_WINDOW_SECONDS:
            _MANUAL_RULE_LIMITER[ip] = {"start": now, "count": 1}
            return True
        if record["count"] >= MANUAL_RULE_MAX_REQUESTS:
            return False
        record["count"] += 1
        return True
    _MANUAL_RULE_LIMITER[ip] = {"start": now, "count": 1}
    return True

def _build_ingress_for_tunnel(tunnel_id):
    entries = []
    from app.core.state_manager import list_agents, get_agent_rules
    with state_lock:
        for rk, r in managed_rules.items():
            if r.get("status") == "active" and r.get("source") == "manual" and r.get("tunnel_id") == tunnel_id:
                e = {"hostname": r.get("hostname"), "service": r.get("service")}
                if r.get("path"):
                    e["path"] = r.get("path")
                entries.append(e)
    agents_map = list_agents()
    for aid, a in agents_map.items():
        if a.get("assigned_tunnel_id") == tunnel_id:
            arules = get_agent_rules(aid)
            for rk, r in arules.items():
                e = {"hostname": r.get("hostname"), "service": r.get("service")}
                if r.get("path"):
                    e["path"] = r.get("path")
                entries.append(e)
    entries.append({"service": "http_status:404"})
    return entries

@api_v2_bp.route('/rules/manual', methods=['POST'])
def create_manual_rule_api():
    if not docker_client:
        return jsonify({"error": "system_unavailable"}), 503
    if not _check_manual_rule_rate_limit():
        return jsonify({"error": "rate_limited"}), 429
    data = request.get_json(silent=True) or {}
    hostname_raw = data.get('hostname')
    service_raw = data.get('service')
    tunnel_id_raw = data.get('tunnel_id')
    path_value = data.get('path')
    zone_id_override = data.get('zone_id')
    zone_name_override = data.get('zone_name')
    if not isinstance(hostname_raw, str) or not isinstance(service_raw, str) or not isinstance(tunnel_id_raw, str):
        return jsonify({"error": "validation_failed"}), 400
    hostname = hostname_raw.strip()
    service = service_raw.strip()
    tunnel_id = tunnel_id_raw.strip()
    if not hostname or not tunnel_id or not is_valid_hostname(hostname) or not is_valid_service(service):
        return jsonify({"error": "validation_failed"}), 400
    normalized_path = None
    if isinstance(path_value, str):
        trimmed = path_value.strip()
        if trimmed:
            if not trimmed.startswith('/'):
                trimmed = '/' + trimmed
            if len(trimmed) > 1 and trimmed.endswith('/'):
                trimmed = trimmed.rstrip('/')
            normalized_path = trimmed
    try:
        selected_zone = resolve_account_zone(
            hostname,
            explicit_zone_id=zone_id_override,
            explicit_zone_name=zone_name_override,
            allow_unverified_default=False,
        )
    except ZoneResolutionError as exc:
        status = 503 if exc.code == "inventory_unavailable" else 409
        return jsonify({"error": exc.code, "candidates": exc.candidates}), status
    zone_id = selected_zone.get('id')
    zone_name = selected_zone.get('name')
    tunnels = get_all_account_cloudflare_tunnels()
    tunnel_info = next((t for t in tunnels if t.get('id') == tunnel_id), None)
    if not tunnel_info:
        return jsonify({"error": "tunnel_not_found"}), 404
    tunnel_name = tunnel_info.get('name')
    rule_key = get_rule_key(hostname, normalized_path)
    access_groups_input = data.get('access_group_ids')
    if access_groups_input is None:
        access_groups_input = data.get('access_group_id')
    if isinstance(access_groups_input, str):
        access_group_ids_list = [access_groups_input.strip()] if access_groups_input.strip() else []
    elif isinstance(access_groups_input, list):
        access_group_ids_list = [str(item).strip() for item in access_groups_input if str(item).strip()]
    else:
        access_group_ids_list = []
    state_changed = False
    previous_tunnel_id = None
    previous_rule_snapshot = None
    master_tunnel_id = get_effective_tunnel_id()
    with state_lock:
        existing = managed_rules.get(rule_key)
        previous_rule_snapshot = copy.deepcopy(existing) if existing else None
        if existing and existing.get("status") == "active":
            existing_tunnel = existing.get("tunnel_id") or master_tunnel_id
            if existing.get("source") != "manual" or existing_tunnel != tunnel_id:
                return jsonify({"error": "hostname_conflict", "rule_key": rule_key, "existing_tunnel_id": existing_tunnel}), 409
            previous_tunnel_id = existing_tunnel
            new_values = {
                "hostname": hostname,
                "path": normalized_path,
                "service": service,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "zone_resolution_source": selected_zone.get("source"),
                "tunnel_id": tunnel_id,
                "tunnel_name": tunnel_name,
                "access_group_id": access_group_ids_list or None
            }
            for key, val in new_values.items():
                if existing.get(key) != val:
                    existing[key] = val
                    state_changed = True
            if state_changed:
                save_state()
        else:
            managed_rules[rule_key] = {
                "hostname": hostname,
                "path": normalized_path,
                "service": service,
                "container_id": None,
                "status": "active",
                "delete_at": None,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "zone_resolution_source": selected_zone.get("source"),
                "no_tls_verify": False,
                "origin_server_name": None,
                "http_host_header": None,
                "http2_origin": False,
                "disable_chunked_encoding": False,
                "access_app_id": None,
                "access_policy_type": None,
                "access_app_config_hash": None,
                "access_policy_ui_override": False,
                "rule_ui_override": False,
                "source": "manual",
                "access_group_id": access_group_ids_list or None,
                "tunnel_id": tunnel_id,
                "tunnel_name": tunnel_name
            }
            save_state()
            state_changed = True

    if access_group_ids_list:
        from app import config
        rule = managed_rules.get(rule_key)
        if rule:
            use_reusable = False
            cf_access_policies_or_ids = []
            session_duration = "24h"
            app_launcher_visible = False
            auto_redirect_to_identity = False
            allowed_idps = get_access_group_allowed_idps(access_group_ids_list)

            for group_id in access_group_ids_list:
                if group_id in access_groups:
                    group = access_groups[group_id]
                    group_session = group.get("session_duration", "24h")
                    if group_session:
                        session_duration = group_session
                    app_launcher_visible = group.get("app_launcher_visible", False)
                    auto_redirect_to_identity = group.get("auto_redirect_to_identity", False)
                else:
                    logging.warning(f"API: Access group '{group_id}' selected but not found in state")

            cf_access_policies_or_ids, use_reusable = resolve_access_group_policies(
                access_group_ids_list,
                config.USE_REUSABLE_POLICIES
            )

            if cf_access_policies_or_ids:
                try:
                    existing_access_app_id = rule.get("access_app_id")
                    if existing_access_app_id:
                        logging.info(f"API: Updating existing Access Application ID '{existing_access_app_id}' for rule {rule_key}")
                        from app.core.access_manager import update_cloudflare_access_application
                        new_access_data = update_cloudflare_access_application(
                            existing_access_app_id,
                            hostname,
                            f"DockFlare-{hostname}",
                            session_duration,
                            app_launcher_visible,
                            [hostname],
                            cf_access_policies_or_ids,
                            allowed_idps,
                            auto_redirect_to_identity=auto_redirect_to_identity,
                            use_reusable=use_reusable
                        )
                        if new_access_data:
                            logging.info(f"API: Successfully updated Access Application for {rule_key}")
                        else:
                            logging.error(f"API: Failed to update Access Application for {rule_key}")
                    else:
                        logging.info(f"API: Creating new Access Application for rule {rule_key}")
                        from app.core.access_manager import create_cloudflare_access_application
                        new_access_data = create_cloudflare_access_application(
                            hostname,
                            f"DockFlare-{hostname}",
                            session_duration,
                            app_launcher_visible,
                            [hostname],
                            cf_access_policies_or_ids,
                            allowed_idps,
                            auto_redirect_to_identity=auto_redirect_to_identity,
                            use_reusable=use_reusable
                        )
                        if new_access_data and new_access_data.get('id'):
                            new_app_id = new_access_data['id']
                            rule["access_app_id"] = new_app_id
                            rule["access_policy_type"] = "reusable" if use_reusable else "inline"
                            save_state()
                            logging.info(f"API: Created Access Application ID '{new_app_id}' for {rule_key}")
                        else:
                            logging.error(f"API: Failed to create Access Application for {rule_key}")
                except Exception as e:
                    logging.error(f"API: Error creating/updating Access Application for {rule_key}: {e}", exc_info=True)

    if state_changed:
        publish_state_event('snapshot_refresh')
    dns_result = None
    try:
        dns_result = create_cloudflare_dns_record(zone_id, hostname, tunnel_id)
    except Exception as dns_error:
        logging.error(f"Failed to ensure DNS for manual rule {rule_key}: {dns_error}")

    update_needed = state_changed or (previous_tunnel_id and previous_tunnel_id != tunnel_id)
    tunnel_update_success = True
    if update_needed:
        tunnel_update_success = bool(update_cloudflare_config(tunnel_id))
    if previous_tunnel_id and previous_tunnel_id != tunnel_id:
        update_cloudflare_config(previous_tunnel_id)
    if state_changed and previous_tunnel_id is None and master_tunnel_id and master_tunnel_id != tunnel_id:
        update_cloudflare_config(master_tunnel_id)
    dns_success = bool(dns_result) and dns_result not in {"semaphore_timeout", "existing_record_unconfirmed"}
    if not dns_success or not tunnel_update_success:
        with state_lock:
            if previous_rule_snapshot is None:
                managed_rules.pop(rule_key, None)
            else:
                managed_rules[rule_key] = previous_rule_snapshot
            save_state()
        update_cloudflare_config(tunnel_id)
        if previous_tunnel_id:
            update_cloudflare_config(previous_tunnel_id)
        previous_tuple = None
        if previous_rule_snapshot:
            previous_tuple = (
                previous_rule_snapshot.get("hostname"),
                previous_rule_snapshot.get("zone_id"),
                previous_rule_snapshot.get("tunnel_id") or master_tunnel_id,
            )
        with state_lock:
            new_tuple_still_owned = any(
                rule.get("status") == "active"
                and rule.get("hostname") == hostname
                and rule.get("zone_id") == zone_id
                and (rule.get("tunnel_id") or master_tunnel_id) == tunnel_id
                for rule in managed_rules.values()
            )
        if dns_success and previous_tuple != (hostname, zone_id, tunnel_id) and not new_tuple_still_owned:
            delete_cloudflare_dns_record(zone_id, hostname, tunnel_id)
        return jsonify({"error": "cloudflare_mutation_failed", "dns_updated": dns_success, "tunnel_updated": tunnel_update_success}), 502
    if previous_rule_snapshot:
        old_tuple = (
            previous_rule_snapshot.get("hostname"),
            previous_rule_snapshot.get("zone_id"),
            previous_rule_snapshot.get("tunnel_id") or master_tunnel_id,
        )
        new_tuple = (hostname, zone_id, tunnel_id)
        with state_lock:
            old_tuple_still_owned = any(
                rule.get("status") == "active"
                and rule.get("hostname") == old_tuple[0]
                and rule.get("zone_id") == old_tuple[1]
                and (rule.get("tunnel_id") or master_tunnel_id) == old_tuple[2]
                for rule in managed_rules.values()
            )
        if old_tuple != new_tuple and not old_tuple_still_owned and all(old_tuple) and not old_tuple[0].startswith('*.'):
            delete_cloudflare_dns_record(old_tuple[1], old_tuple[0], old_tuple[2])
    status_code = 201 if state_changed else 200
    return jsonify({"rule_key": rule_key}), status_code

@api_v2_bp.route('/reconciliation-status', methods=['GET'])
def get_reconciliation_status():
    reconciliation_info_data = getattr(current_app, 'reconciliation_info', {})
    return jsonify({
        "in_progress": reconciliation_info_data.get("in_progress", False),
        "progress": reconciliation_info_data.get("progress", 0),
        "total_items": reconciliation_info_data.get("total_items", 0),
        "processed_items": reconciliation_info_data.get("processed_items", 0),
        "status": reconciliation_info_data.get("status", "Not started")
    })

@api_v2_bp.route('/reconcile', methods=['POST'])
def trigger_reconciliation():
    """
    Trigger a full reconciliation run asynchronously.
    """
    try:
        logging.info("API: Received request to trigger reconciliation via /api/v2/reconcile")
        reconcile_state_threaded()
        logging.info("API: Reconciliation triggered via /api/v2/reconcile")
        return jsonify({"status": "success", "message": "Reconciliation started."}), 202
    except Exception as e:
        logging.error(f"API: Exception while triggering reconciliation: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Exception during reconciliation trigger: {e}"}), 500

# ----------------------
# Agent / Multi-server endpoints
# ----------------------

def _extract_bearer_token():
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get('Authorization', '')
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    return None

def _authenticate_agent_request():
    """
    Validate an incoming agent request by API key.
    Returns tuple: (key, owner_agent_id_or_label or None)
    """
    token = _extract_bearer_token()
    if not token:
        return None, None
    key_info = get_agent_key_info(token)
    if not key_info:
        logging.warning("AGENT_AUTH: Rejected request with unknown token.")
        return None, None
    if key_info.get("status", "active") != "active":
        logging.warning("AGENT_AUTH: Rejected request with inactive token.")
        return None, None
    owner = find_agent_id_by_key(token)
    return token, owner

def process_agent_container_start(payload, agent_id, defer_side_effects=False):
    """
    Process a container_start event from an agent.
    Similar to process_container_start but works with provided labels.
    """
    try:
        with current_app.app_context():
            container_data = payload.get("container", {})
            labels = container_data.get("labels", {})
            container_id = container_data.get("id", "unknown")
            container_name = container_data.get("name", "unknown")

            logging.info(f"AGENT_PROCESS_START: Processing container {container_name} ({container_id[:12]}) from agent {agent_id}")

            is_enabled = get_label(labels, "enable", "false").lower() in ["true", "1", "t", "yes"]
            if not is_enabled:
                logging.debug(f"AGENT_PROCESS: Ignoring: {container_name} ({container_id[:12]}): 'enable' label not true.")
                return None
            
            hostnames_to_process = []

            default_path_label = get_label(labels, "path")
            default_originsrvname_label = get_label(labels, "originsrvname")
            default_http_host_header_label = get_label(labels, "httpHostHeader")

            default_access_groups = get_label(labels, "access.groups")
            default_access_group = get_label(labels, "access.group") if not default_access_groups else None
            default_access_policy_type_label = get_label(labels, "access.policy")

            if default_access_policy_type_label == "bypass" and not default_access_group and not default_access_groups:
                logging.info(f"AGENT_PROCESS: Legacy label 'dockflare.access.policy=bypass' detected for {container_name}. Migrating to 'dockflare.access.group=public-default-bypass'.")
                default_access_group = ["public-default-bypass"]
                default_access_policy_type_label = None
            elif default_access_group and not default_access_groups:
                if isinstance(default_access_group, str) and default_access_group == "bypass":
                    logging.info(f"AGENT_PROCESS: Legacy group 'bypass' detected for {container_name}. Migrating to 'public-default-bypass'.")
                    default_access_group = "public-default-bypass"
                elif isinstance(default_access_group, list) and "bypass" in default_access_group:
                    logging.info(f"AGENT_PROCESS: Legacy group 'bypass' detected in list for {container_name}. Migrating to 'public-default-bypass'.")
                    default_access_group = ["public-default-bypass" if g == "bypass" else g for g in default_access_group]
            elif default_access_policy_type_label == "authenticate" and not default_access_group and not default_access_groups:
                from app.core.cloudflare_api import get_cloudflare_account_email
                account_email = get_cloudflare_account_email()
                if account_email:
                    logging.info(f"AGENT_PROCESS: Legacy label 'dockflare.access.policy=authenticate' detected for {container_name}. Migrating to 'dockflare.access.group=authenticated-default' (restricted to {account_email}).")
                    default_access_group = ["authenticated-default"]
                    default_access_policy_type_label = None
                else:
                    logging.warning(f"AGENT_PROCESS: Cannot migrate 'dockflare.access.policy=authenticate' for {container_name}. Cloudflare account email not available. Skipping access policy creation. Use 'dockflare.access.group=<group>' instead.")
                    default_access_policy_type_label = None

            if default_access_groups:
                default_access_group = [gid.strip() for gid in default_access_groups.split(',')]
            elif default_access_group:
                default_access_group = [default_access_group.strip()] if isinstance(default_access_group, str) else default_access_group
            default_access_app_name_label = get_label(labels, "access.name")
            default_access_session_duration_label = get_label(labels, "access.session_duration", "24h")
            default_access_app_launcher_visible_label = get_label(labels, "access.app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
            default_access_allowed_idps_label_str = get_label(labels, "access.allowed_idps")
            default_access_auto_redirect_label = get_label(labels, "access.auto_redirect_to_identity", "false").lower() in ["true", "1", "t", "yes"]
            default_access_custom_rules_label_str = get_label(labels, "access.custom_rules")

            hostname_label = get_label(labels, "hostname")
            service_label = get_label(labels, "service")
            zone_name_label = get_label(labels, "zonename")
            no_tls_verify_label = get_label(labels, "no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]
            http2_origin_label = get_label(labels, "http2_origin", "false").lower() in ["true", "1", "t", "yes"]
            disable_chunked_encoding_label = get_label(labels, "disable_chunked_encoding", "false").lower() in ["true", "1", "t", "yes"]
            match_sni_to_host_label = get_label(labels, "match_sni_to_host", "false").lower() in ["true", "1", "t", "yes"]

            if hostname_label and service_label:
                if is_valid_hostname(hostname_label) and is_valid_service(service_label):
                    hostnames_to_process.append({
                        "hostname": hostname_label,
                        "service": service_label,
                        "zone_name": zone_name_label,
                        "path": default_path_label,
                        "no_tls_verify": no_tls_verify_label,
                        "origin_server_name": default_originsrvname_label.strip() if default_originsrvname_label else None,
                        "http_host_header": default_http_host_header_label.strip() if default_http_host_header_label else None,
                        "http2_origin": http2_origin_label,
                        "disable_chunked_encoding": disable_chunked_encoding_label,
                        "match_sni_to_host": match_sni_to_host_label,
                        "access_group": default_access_group,
                        "access_policy_type": default_access_policy_type_label,
                        "access_app_name": default_access_app_name_label,
                        "access_session_duration": default_access_session_duration_label,
                        "access_app_launcher_visible": default_access_app_launcher_visible_label,
                        "access_allowed_idps_str": default_access_allowed_idps_label_str,
                        "access_auto_redirect": default_access_auto_redirect_label,
                        "access_custom_rules_str": default_access_custom_rules_label_str
                    })

            index = 0
            while True:
                hostname_indexed = get_label(labels, f"{index}.hostname")
                if not hostname_indexed:
                    break

                service_indexed = get_label(labels, f"{index}.service", service_label)
                if not service_indexed:
                    logging.warning(f"AGENT_PROCESS: Indexed hostname {hostname_indexed} for {container_name} missing service, skipping index {index}.")
                    index += 1
                    continue

                path_indexed = get_label(labels, f"{index}.path", default_path_label)
                zone_name_indexed = get_label(labels, f"{index}.zonename", zone_name_label)
                no_tls_verify_indexed_val = get_label(labels, f"{index}.no_tls_verify", str(no_tls_verify_label).lower())
                no_tls_verify_indexed = no_tls_verify_indexed_val.lower() in ["true", "1", "t", "yes"]
                originsrvname_indexed_val = get_label(labels, f"{index}.originsrvname", default_originsrvname_label)
                http_host_header_indexed_val = get_label(labels, f"{index}.httpHostHeader", default_http_host_header_label)
                http2_origin_indexed_val = get_label(labels, f"{index}.http2_origin", str(http2_origin_label).lower())
                http2_origin_indexed = http2_origin_indexed_val.lower() in ["true", "1", "t", "yes"]
                disable_chunked_encoding_indexed_val = get_label(labels, f"{index}.disable_chunked_encoding", str(disable_chunked_encoding_label).lower())
                disable_chunked_encoding_indexed = disable_chunked_encoding_indexed_val.lower() in ["true", "1", "t", "yes"]
                match_sni_to_host_indexed_val = get_label(labels, f"{index}.match_sni_to_host", str(match_sni_to_host_label).lower())
                match_sni_to_host_indexed = match_sni_to_host_indexed_val.lower() in ["true", "1", "t", "yes"]

                access_groups_indexed = get_label(labels, f"{index}.access.groups")
                raw_access_group_indexed = get_label(labels, f"{index}.access.group") if not access_groups_indexed else None
                access_policy_type_indexed = get_label(labels, f"{index}.access.policy", default_access_policy_type_label)

                if access_policy_type_indexed == "bypass" and not raw_access_group_indexed and not access_groups_indexed:
                    logging.info(f"AGENT_PROCESS: Legacy label 'dockflare.{index}.access.policy=bypass' detected for {container_name}. Migrating to 'dockflare.{index}.access.group=public-default-bypass'.")
                    access_group_indexed = ["public-default-bypass"]
                    access_policy_type_indexed = None
                elif access_policy_type_indexed == "authenticate" and not raw_access_group_indexed and not access_groups_indexed:
                    from app.core.cloudflare_api import get_cloudflare_account_email
                    account_email = get_cloudflare_account_email()
                    if account_email:
                        logging.info(f"AGENT_PROCESS: Legacy label 'dockflare.{index}.access.policy=authenticate' detected for {container_name}. Migrating to 'dockflare.{index}.access.group=authenticated-default' (restricted to {account_email}).")
                        access_group_indexed = ["authenticated-default"]
                        access_policy_type_indexed = None
                    else:
                        logging.warning(f"AGENT_PROCESS: Cannot migrate 'dockflare.{index}.access.policy=authenticate' for {container_name}. Cloudflare account email not available. Skipping access policy creation. Use 'dockflare.{index}.access.group=<group>' instead.")
                        access_policy_type_indexed = None
                        access_group_indexed = None
                else:
                    if access_groups_indexed:
                        parsed_groups = [gid.strip() for gid in access_groups_indexed.split(',') if gid and gid.strip()]
                    else:
                        parsed_groups = normalize_access_group_value(raw_access_group_indexed)
                    if not parsed_groups:
                        parsed_groups = list(default_access_group) if isinstance(default_access_group, list) else default_access_group
                    if parsed_groups and any(g == "bypass" for g in parsed_groups):
                        logging.info(f"AGENT_PROCESS: Legacy group 'bypass' detected in index {index} for {container_name}. Migrating to 'public-default-bypass'.")
                        parsed_groups = ["public-default-bypass" if g == "bypass" else g for g in parsed_groups]
                    access_group_indexed = parsed_groups

                if access_group_indexed and not isinstance(access_group_indexed, list):
                    access_group_indexed = normalize_access_group_value(access_group_indexed)
                access_app_name_indexed = get_label(labels, f"{index}.access.name", default_access_app_name_label)
                access_session_duration_indexed = get_label(labels, f"{index}.access.session_duration", default_access_session_duration_label)
                acc_launcher_val_idx = get_label(labels, f"{index}.access.app_launcher_visible", str(default_access_app_launcher_visible_label).lower())
                access_app_launcher_visible_indexed = acc_launcher_val_idx.lower() in ["true", "1", "t", "yes"]
                access_allowed_idps_indexed_str = get_label(labels, f"{index}.access.allowed_idps", default_access_allowed_idps_label_str)
                acc_redirect_val_idx = get_label(labels, f"{index}.access.auto_redirect_to_identity", str(default_access_auto_redirect_label).lower())
                access_auto_redirect_indexed = acc_redirect_val_idx.lower() in ["true", "1", "t", "yes"]
                access_custom_rules_indexed_str = get_label(labels, f"{index}.access.custom_rules", default_access_custom_rules_label_str)

                if is_valid_hostname(hostname_indexed) and is_valid_service(service_indexed):
                    hostnames_to_process.append({
                        "hostname": hostname_indexed,
                        "service": service_indexed,
                        "zone_name": zone_name_indexed,
                        "path": path_indexed,
                        "no_tls_verify": no_tls_verify_indexed,
                        "origin_server_name": originsrvname_indexed_val.strip() if originsrvname_indexed_val else None,
                        "http_host_header": http_host_header_indexed_val.strip() if http_host_header_indexed_val else None,
                        "http2_origin": http2_origin_indexed,
                        "disable_chunked_encoding": disable_chunked_encoding_indexed,
                        "match_sni_to_host": match_sni_to_host_indexed,
                        "access_group": access_group_indexed,
                        "access_policy_type": access_policy_type_indexed,
                        "access_app_name": access_app_name_indexed,
                        "access_session_duration": access_session_duration_indexed,
                        "access_app_launcher_visible": access_app_launcher_visible_indexed,
                        "access_allowed_idps_str": access_allowed_idps_indexed_str,
                        "access_auto_redirect": access_auto_redirect_indexed,
                        "access_custom_rules_str": access_custom_rules_indexed_str
                    })
                index += 1

            if not hostnames_to_process:
                logging.warning(f"AGENT_PROCESS: No valid hostname configs for {container_name} ({container_id[:12]}).")
                return None

            logging.info(f"AGENT_PROCESS: Found {len(hostnames_to_process)} hostname configurations for container {container_name}")

            state_changed_locally = False
            needs_tunnel_config_update = False

            agent_record = get_agent(agent_id)
            assigned_tunnel_name = agent_record.get("assigned_tunnel_name") if agent_record else "Unknown"
            assigned_tunnel_id = agent_record.get("assigned_tunnel_id") if agent_record else None

            logging.info(f"AGENT_PROCESS: Processing {len(hostnames_to_process)} hostname configs for agent {agent_id}")

            policy_jobs_map = {}
            dns_targets = {}
            zone_inventory = None
            for config_item in hostnames_to_process:
                hostname = config_item["hostname"]
                service = config_item["service"]
                path_from_item = config_item.get("path")
                rule_key = get_rule_key(hostname, path_from_item)
                source_rule_key = get_source_rule_key(hostname, path_from_item)

                with state_lock:
                    matched_key, matched_rule = find_container_rule(source_rule_key, "agent", agent_id)
                    if matched_rule and matched_rule.get("rule_ui_override", False):
                        changed, reactivated = restore_rule_lifecycle(matched_rule, container_id)
                        if matched_rule.get("source_rule_key") is None and matched_key == rule_key:
                            matched_rule["source_rule_key"] = source_rule_key
                            matched_rule["lifecycle_generation"] = int(matched_rule.get("lifecycle_generation") or 0) + 1
                            changed = True
                        if reactivated:
                            mark_rule_tunnel_sync_pending(matched_rule)
                            needs_tunnel_config_update = True
                        state_changed_locally |= changed
                        if matched_rule.get("hostname") and matched_rule.get("zone_id"):
                            dns_targets[matched_rule["hostname"]] = {"zone_id": matched_rule["zone_id"]}
                        logging.info(
                            "UI-overridden agent rule %s: lifecycle observation accepted for container %s; UI configuration preserved.",
                            matched_key,
                            container_id[:12],
                        )
                        continue

                zone_name_from_item = config_item["zone_name"]
                no_tls_verify_from_item = config_item["no_tls_verify"]
                origin_server_name_from_item = config_item.get("origin_server_name")
                http_host_header_from_item = config_item.get("http_host_header")
                http2_origin_from_item = config_item.get("http2_origin", False)
                disable_chunked_encoding_from_item = config_item.get("disable_chunked_encoding", False)
                match_sni_to_host_from_item = config_item.get("match_sni_to_host", False)

                if zone_inventory is None:
                    zone_inventory = get_account_zone_inventory()
                try:
                    selected_zone = resolve_account_zone(
                        hostname,
                        explicit_zone_name=zone_name_from_item or None,
                        zones=zone_inventory["zones"],
                        inventory_status=zone_inventory["status"],
                        allow_unverified_default=True,
                    )
                except ZoneResolutionError as exc:
                    logging.error(f"AGENT_PROCESS: Zone resolution failed for {rule_key} ({exc.code}). Skipping.")
                    continue
                target_zone_id = selected_zone["id"]
                zone_name_from_item = selected_zone.get("name")
                config_item["zone_name"] = zone_name_from_item
                config_item["zone_resolution_source"] = selected_zone.get("source")

                with state_lock:
                    existing_rule = managed_rules.get(rule_key)

                    if existing_rule and existing_rule.get("source") == "manual":
                        logging.info(f"AGENT_PROCESS: Rule {rule_key} is manual, skipping.")
                        continue
                    if existing_rule and (existing_rule.get("source") != "agent" or existing_rule.get("agent_id") != agent_id):
                        logging.warning("AGENT_PROCESS: Rule %s ownership mismatch for agent %s; observation ignored.", rule_key, agent_id)
                        continue

                    if existing_rule:
                        original_existing_rule = copy.deepcopy(existing_rule)
                        if existing_rule.get("source_rule_key") is None:
                            existing_rule["source_rule_key"] = source_rule_key
                            existing_rule["lifecycle_generation"] = int(existing_rule.get("lifecycle_generation") or 0) + 1
                        logging.debug(f"AGENT_PROCESS_UPD_RULE: Updating rule for {rule_key}")

                        rule_data_changed = False
                        if existing_rule.get("service") != service:
                            existing_rule["service"] = service
                            rule_data_changed = True
                        if existing_rule.get("path") != path_from_item:
                            existing_rule["path"] = path_from_item
                            rule_data_changed = True
                        if existing_rule.get("container_id") != container_id:
                            existing_rule["container_id"] = container_id
                            rule_data_changed = True
                        if existing_rule.get("zone_id") != target_zone_id:
                            existing_rule["zone_id"] = target_zone_id
                            rule_data_changed = True
                        if existing_rule.get("no_tls_verify") != no_tls_verify_from_item:
                            existing_rule["no_tls_verify"] = no_tls_verify_from_item
                            rule_data_changed = True
                        if existing_rule.get("origin_server_name") != origin_server_name_from_item:
                            existing_rule["origin_server_name"] = origin_server_name_from_item
                            rule_data_changed = True
                        http_host_header_from_item = config_item.get("http_host_header")
                        if existing_rule.get("http_host_header") != http_host_header_from_item:
                            existing_rule["http_host_header"] = http_host_header_from_item
                            rule_data_changed = True
                        if existing_rule.get("http2_origin") != http2_origin_from_item:
                            existing_rule["http2_origin"] = http2_origin_from_item
                            rule_data_changed = True
                        if existing_rule.get("disable_chunked_encoding") != disable_chunked_encoding_from_item:
                            existing_rule["disable_chunked_encoding"] = disable_chunked_encoding_from_item
                            rule_data_changed = True
                        if existing_rule.get("match_sni_to_host") != match_sni_to_host_from_item:
                            existing_rule["match_sni_to_host"] = match_sni_to_host_from_item
                            rule_data_changed = True
                        if existing_rule.get("tunnel_name") != assigned_tunnel_name:
                            existing_rule["tunnel_name"] = assigned_tunnel_name
                            rule_data_changed = True
                        if existing_rule.get("tunnel_id") != assigned_tunnel_id:
                            existing_rule["tunnel_id"] = assigned_tunnel_id
                            rule_data_changed = True
                        if existing_rule.get("zone_name") != zone_name_from_item:
                            existing_rule["zone_name"] = zone_name_from_item
                            rule_data_changed = True
                        if existing_rule.get("zone_resolution_source") != selected_zone.get("source"):
                            existing_rule["zone_resolution_source"] = selected_zone.get("source")
                            rule_data_changed = True

                        existing_rule["source"] = "agent"
                        existing_rule["agent_id"] = agent_id

                        if existing_rule.get("status") == "pending_deletion":
                            existing_rule["status"] = "active"
                            existing_rule["delete_at"] = None
                            rule_data_changed = True

                        tunnel_fields = (
                            "hostname", "path", "service", "zone_id", "no_tls_verify",
                            "origin_server_name", "http_host_header", "http2_origin",
                            "disable_chunked_encoding", "match_sni_to_host", "tunnel_id",
                        )
                        requires_tunnel_update = (
                            original_existing_rule.get("status") != existing_rule.get("status")
                            or any(original_existing_rule.get(field) != existing_rule.get(field) for field in tunnel_fields)
                        )
                        if requires_tunnel_update:
                            mark_rule_tunnel_sync_pending(existing_rule)
                            needs_tunnel_config_update = True
                        if original_existing_rule != existing_rule:
                            state_changed_locally = True

                    else:
                        logging.debug(f"AGENT_PROCESS_NEW_RULE: Adding NEW rule for {rule_key}")
                        managed_rules[rule_key] = {
                            "hostname": hostname,
                            "path": path_from_item,
                            "service": service,
                            "container_id": container_id,
                            "status": "active",
                            "delete_at": None,
                            "zone_id": target_zone_id,
                            "zone_name": zone_name_from_item,
                            "zone_resolution_source": selected_zone.get("source"),
                            "no_tls_verify": no_tls_verify_from_item,
                            "origin_server_name": origin_server_name_from_item,
                            "http_host_header": config_item.get("http_host_header"),
                            "http2_origin": http2_origin_from_item,
                            "disable_chunked_encoding": disable_chunked_encoding_from_item,
                            "match_sni_to_host": match_sni_to_host_from_item,
                            "access_app_id": None,
                            "access_policy_type": None,
                            "access_app_config_hash": None,
                            "access_policy_ui_override": False,
                            "rule_ui_override": False,
                            "source": "agent",
                            "access_group_id": None,
                            "agent_id": agent_id,
                            "tunnel_name": assigned_tunnel_name,
                            "tunnel_id": assigned_tunnel_id,
                            "source_rule_key": source_rule_key,
                            "tunnel_sync_pending": True,
                            "tunnel_sync_last_attempt_at": None,
                            "tunnel_sync_attempts": 0,
                            "lifecycle_generation": 0,
                        }
                        existing_rule = managed_rules[rule_key]
                        state_changed_locally = True
                        needs_tunnel_config_update = True

                    dns_targets[hostname] = {
                        "zone_id": target_zone_id,
                        "zone_name": zone_name_from_item
                    }

                    if existing_rule.get("access_policy_ui_override", False):
                        logging.info(f"AGENT_PROCESS: Access policy for {rule_key} is UI-managed. Skipping.")
                    else:
                        policy_jobs_map[rule_key] = copy.deepcopy(config_item)

            policy_jobs = list(policy_jobs_map.items())

            plan = {
                "agent_id": agent_id,
                "state_changed": state_changed_locally,
                "needs_tunnel_config_update": needs_tunnel_config_update,
                "policy_jobs": policy_jobs,
                "dns_targets": dns_targets,
                "tunnel_id": assigned_tunnel_id,
            }
            if defer_side_effects:
                return plan

            if state_changed_locally:
                save_state()
                publish_state_event('snapshot_refresh')
            _execute_agent_start_plan(plan)
            return plan
    except Exception as e:
        logging.error(f"AGENT_PROCESS_START: Exception in process_agent_container_start: {e}", exc_info=True)
        raise


def _execute_agent_start_plan(plan):
    """Apply Cloudflare work only after the associated Agent state is durable."""
    if not plan:
        return
    policy_changed = False
    for rule_key, policy_payload in plan.get("policy_jobs", []):
        if handle_access_policy_from_labels(rule_key, copy.deepcopy(policy_payload)):
            policy_changed = True
    if policy_changed:
        save_state()
        publish_state_event('snapshot_refresh')

    if not plan.get("needs_tunnel_config_update"):
        return
    agent_id = plan["agent_id"]
    agent_tunnel_id = plan.get("tunnel_id")
    if not agent_tunnel_id:
        logging.error("AGENT_PROCESS: Agent %s has no tunnel ID; synchronization remains pending.", agent_id)
        return
    try:
        if not update_cloudflare_config(agent_tunnel_id):
            logging.error("AGENT_PROCESS: Failed to update tunnel config for agent %s", agent_id)
            return
        for hostname, details in plan.get("dns_targets", {}).items():
            zone_id = details.get("zone_id")
            if zone_id and not hostname.startswith('*.'):
                create_cloudflare_dns_record(zone_id, hostname, agent_tunnel_id)
            elif not zone_id:
                logging.error("AGENT_PROCESS: Could not determine Zone ID for DNS record %s", hostname)
        sync_changed = False
        with state_lock:
            for rule in managed_rules.values():
                if rule.get("source") == "agent" and rule.get("agent_id") == agent_id and rule.get("tunnel_id") == agent_tunnel_id and rule.get("tunnel_sync_pending"):
                    rule["tunnel_sync_pending"] = False
                    rule["tunnel_sync_last_attempt_at"] = None
                    rule["tunnel_sync_attempts"] = 0
                    rule["lifecycle_generation"] = int(rule.get("lifecycle_generation") or 0) + 1
                    sync_changed = True
        if sync_changed:
            save_state()
        logging.info("AGENT_PROCESS: Successfully updated tunnel config for agent %s", agent_id)
    except Exception:
        logging.exception("AGENT_PROCESS: Failed to update tunnel config for agent %s", agent_id)


def _coalesce_agent_start_plans(plans):
    """Coalesce one accepted report into at most one tunnel write per Agent tunnel."""
    combined = {}
    for plan in plans:
        key = (plan.get("agent_id"), plan.get("tunnel_id"))
        merged = combined.setdefault(key, {
            "agent_id": plan.get("agent_id"),
            "tunnel_id": plan.get("tunnel_id"),
            "state_changed": False,
            "needs_tunnel_config_update": False,
            "policy_jobs": [],
            "dns_targets": {},
        })
        merged["state_changed"] |= bool(plan.get("state_changed"))
        merged["needs_tunnel_config_update"] |= bool(plan.get("needs_tunnel_config_update"))
        merged["policy_jobs"].extend(plan.get("policy_jobs", []))
        merged["dns_targets"].update(plan.get("dns_targets", {}))
    return list(combined.values())


def process_agent_container_stop(payload, agent_id, received_at=None, persist=True):
    """
    Process a container_stop event from an agent.
    """
    with current_app.app_context():
        container_data = payload.get("container", {})
        container_id = container_data.get("id", "unknown")

        logging.info(f"AGENT_PROCESS_STOP: Processing stop for container {container_id[:12]} from agent {agent_id}")

        with state_lock:
            rule_keys_affected = []
            for r_key, details in managed_rules.items():
                if details.get("container_id") == container_id and \
                    details.get("status") == "active" and \
                    details.get("source") == "agent" and \
                    details.get("agent_id") == agent_id:
                    rule_keys_affected.append(r_key)

            if rule_keys_affected:
                grace_period = current_app.config.get('GRACE_PERIOD_SECONDS', 28800)
                for rule_key in rule_keys_affected:
                    rule = managed_rules[rule_key]
                    if rule.get("status") != "pending_deletion":
                        rule["status"] = "pending_deletion"
                        grace_delta = timedelta(seconds=grace_period)
                        rule["delete_at"] = (received_at or datetime.now(timezone.utc)) + grace_delta
                        rule["lifecycle_generation"] = int(rule.get("lifecycle_generation") or 0) + 1
                        logging.info(f"AGENT_PROCESS_STOP: Rule for {rule_key} scheduled for deletion (grace period: {grace_period}s)")
                if persist:
                    save_state()
                    publish_state_event('snapshot_refresh')
                logging.info(f"AGENT_PROCESS_STOP: Scheduled {len(rule_keys_affected)} rules for deletion from agent {agent_id}")
                return True
            else:
                logging.info(f"AGENT_PROCESS_STOP: No active agent-managed rules found for container {container_id[:12]} from agent {agent_id}")
        return False

@api_v2_bp.route('/agents/generate-key', methods=['POST', 'GET'])
def agents_generate_key():
    """
    Admin endpoint to create an agent API key.
    POST Payload: { "owner": "<agent_id or label (optional)>" }
    GET: returns a simple HTML form for manual key generation.
    Returns the raw key token (store it securely).
    """
    if request.method == 'GET':
        return jsonify({"status": "error", "message": "HTML key generation is disabled."}), 405
   
    if request.is_json:
        data = request.get_json() or {}
        owner = data.get('owner')
    else:
        owner = request.form.get('owner')

    key_token = secrets.token_urlsafe(32)
    created_at = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    meta = {
        "owner": owner,
        "created_at": created_at,
        "status": "active",
        "last_used_at": None,
        "bound_agent_id": None
    }
    add_agent_key(key_token, meta)
    return jsonify({"status": "success", "key": key_token, "meta": meta}), 201

@api_v2_bp.route('/agents/revoke-key', methods=['POST'])
def agents_revoke_key():
    """
    Admin endpoint to revoke an agent API key.
    Payload: { "key": "<key_token>" }
    """
    data = request.get_json() or {}
    key_identifier = data.get('key')
    if not key_identifier:
        return jsonify({"status": "error", "message": "Missing 'key' in payload."}), 400
    key = _resolve_agent_key_identifier(key_identifier)
    if not key:
        return jsonify({"status": "error", "message": "Key not found."}), 404
    ok = revoke_agent_key(key)
    if ok:
        affected_agents = []
        agents_snapshot = list_agents()
        now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
        for agent_id, agent_data in agents_snapshot.items():
            if agent_data.get("api_key") == key:
                agent_meta = dict(agent_data.get("meta") or {})
                agent_meta["last_key_revoked_at"] = now_iso
                update_agent(agent_id, {"api_key": None, "status": "pending", "meta": agent_meta})
                affected_agents.append(agent_id)
        return jsonify({"status": "success", "message": "Key revoked.", "affected_agents": affected_agents}), 200
    else:
        return jsonify({"status": "error", "message": "Key not found."}), 404

@api_v2_bp.route('/agents/keys/<key_id>', methods=['DELETE'])
def delete_agent_key_permanently(key_id):
    """
    Admin endpoint to permanently delete a revoked agent API key.
    Only revoked keys can be permanently deleted.
    """
    if not key_id:
        return jsonify({"status": "error", "message": "Missing key ID"}), 400

    
    key_token = _resolve_agent_key_identifier(key_id)
    key_info = get_agent_key_info(key_token) if key_token else None
    if not key_info:
        return jsonify({"status": "error", "message": "Key not found"}), 404

    
    if key_info.get("status") != "revoked":
        return jsonify({"status": "error", "message": "Can only permanently delete revoked keys"}), 400

    
    owner = key_info.get("owner", "unknown")
    revoked_at = key_info.get("revoked_at", "unknown")
    logging.info("ADMIN: Permanently deleting revoked Agent key (owner: %s, revoked: %s)", owner, revoked_at)
    
    agent_key_store.remove_key(key_token)

    return jsonify({
        "status": "success",
        "message": "Key permanently deleted",
        "deleted_key": _agent_key_reference(key_token)[:8] + "...",
        "owner": owner
    }), 200

@api_v2_bp.route('/agents/keys/revoked', methods=['DELETE'])
def delete_all_revoked_keys():
    """
    Admin endpoint to permanently delete all revoked agent API keys.
    """
    all_keys = list_agent_keys()
    revoked_keys = {k: v for k, v in all_keys.items() if v.get("status") == "revoked"}

    if not revoked_keys:
        return jsonify({"status": "success", "message": "No revoked keys to delete"}), 200

    deleted_count = 0
    deleted_keys = []

    for key_id, key_info in revoked_keys.items():
        try:
            owner = key_info.get("owner", "unknown")
            revoked_at = key_info.get("revoked_at", "unknown")
            logging.info(f"ADMIN: Bulk deleting revoked key {key_id[:8]}... (owner: {owner}, revoked: {revoked_at})")

            agent_key_store.remove_key(key_id)
            deleted_keys.append({"key": key_id[:8] + "...", "owner": owner})
            deleted_count += 1
        except Exception as e:
            logging.error(f"Failed to delete revoked key {key_id[:8]}: {e}")

    logging.info(f"ADMIN: Bulk deleted {deleted_count} revoked keys")

    return jsonify({
        "status": "success",
        "message": f"Permanently deleted {deleted_count} revoked keys",
        "deleted_count": deleted_count,
        "deleted_keys": deleted_keys
    }), 200

@api_v2_bp.route('/agents/keys/cleanup', methods=['POST'])
def trigger_key_cleanup():
    """
    Admin endpoint to manually trigger cleanup of expired revoked keys.
    """
    data = request.get_json() or {}
    retention_days = data.get('retention_days', 30)

    if not isinstance(retention_days, int) or retention_days < 1:
        return jsonify({"status": "error", "message": "retention_days must be a positive integer"}), 400

    try:
        result = cleanup_expired_revoked_keys(retention_days)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Manual cleanup failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Cleanup failed: {str(e)}"}), 500

@api_v2_bp.route('/agents/cf-service-token/setup', methods=['POST'])
def agents_cf_service_token_setup():
    from app.core.service_token_manager import ensure_agent_service_token
    public_url = config.DOCKFLARE_PUBLIC_URL
    if not public_url:
        return jsonify({"status": "error", "message": "DOCKFLARE_PUBLIC_URL is not configured"}), 400
    try:
        result = ensure_agent_service_token(public_url)
        return jsonify({
            "status": "success",
            "client_id": result["client_id"],
            "app_uuid": result["app_uuid"],
            "policy_id": result["policy_id"],
        }), 200
    except Exception as e:
        logging.error("CF service token setup failed: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/agents/cf-service-token/status', methods=['GET'])
def agents_cf_service_token_status():
    from app.core.service_token_manager import get_agent_service_token
    token = get_agent_service_token()
    if token:
        return jsonify({
            "status": "success",
            "configured": True,
            "client_id": token["client_id"],
            "app_uuid": token["app_uuid"],
            "policy_id": token.get("policy_id"),
        }), 200
    return jsonify({"status": "success", "configured": False}), 200


@api_v2_bp.route('/agents/cf-service-token', methods=['DELETE'])
def agents_cf_service_token_delete():
    from app.core.service_token_manager import delete_agent_service_token
    try:
        delete_agent_service_token()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error("CF service token delete failed: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/agents/deploy-info/<key_id>', methods=['GET'])
def agents_deploy_info(key_id):
    from app.core.service_token_manager import generate_compose_content, generate_deploy_script
    key_token = _resolve_agent_key_identifier(key_id)
    key_info = get_agent_key_info(key_token) if key_token else None
    if not key_info:
        return jsonify({"status": "error", "message": "Key not found"}), 404
    if key_info.get("status") != "active":
        return jsonify({"status": "error", "message": "Key is not active"}), 400

    public_url = config.DOCKFLARE_PUBLIC_URL
    if not public_url:
        return jsonify({"status": "error", "message": "DOCKFLARE_PUBLIC_URL is not configured"}), 400

    try:
        script_content = generate_deploy_script(key_token, public_url)
        compose_content = generate_compose_content(key_token, public_url)
        return jsonify({
            "status": "success",
            "script_content": script_content,
            "compose_content": compose_content,
        }), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error("Deploy info generation failed: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/agents/deploy-script/<key_id>', methods=['GET'])
def agents_deploy_script(key_id):
    from app.core.service_token_manager import generate_deploy_script
    key_token = _resolve_agent_key_identifier(key_id)
    key_info = get_agent_key_info(key_token) if key_token else None
    if not key_info:
        return jsonify({"status": "error", "message": "Key not found"}), 404
    if key_info.get("status") != "active":
        return jsonify({"status": "error", "message": "Key is not active"}), 400

    public_url = config.DOCKFLARE_PUBLIC_URL
    if not public_url:
        return jsonify({"status": "error", "message": "DOCKFLARE_PUBLIC_URL is not configured"}), 400

    try:
        script = generate_deploy_script(key_token, public_url)
        from flask import Response
        return Response(script, mimetype="text/x-shellscript")
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error("Deploy script generation failed: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@api_v2_bp.route('/agents', methods=['GET'])
def agents_list_api():
    """
    Admin endpoint to list known agents and keys.
    """
    now_dt = datetime.now(timezone.utc)
    heartbeat_timeout = getattr(config, "AGENT_HEARTBEAT_TIMEOUT", 60)
    agents_map = {
        agent_id: _serialize_agent(agent_id, agent_data, now_dt, heartbeat_timeout)
        for agent_id, agent_data in list_agents().items()
    }

    try:
        from app.core.cloudflare_api import get_tunnel_connector_info
        for a_id, a in agents_map.items():
            tunnel_id = a.get("assigned_tunnel_id")
            if tunnel_id:
                connector = get_tunnel_connector_info(tunnel_id)
                if connector:
                    a["connector_version"] = connector.get("version")
                    a["connector_origin_ip"] = connector.get("origin_ip")
                    a["connector_platform"] = connector.get("platform")
                    a["connector_colos"] = connector.get("colos")
    except Exception as e:
        logging.warning("Could not enrich agents with connector info: %s", e)

    return jsonify({
        "agents": agents_map,
        "agent_keys": _serialize_agent_keys(list_agent_keys()),
    }), 200

def _agent_json_response(http_status, code, message=None, **fields):
    body = {"status": "success" if http_status < 400 else "error", "code": code}
    if message:
        body["message"] = str(message)[:256]
    body.update(fields)
    return jsonify(body), http_status


def _register_agent_request():
    token, _owner = _authenticate_agent_request()
    if not token:
        return _agent_json_response(401, "unauthorized")
    if request.content_length and request.content_length > config.AGENT_MAX_REQUEST_BYTES:
        return _agent_json_response(413, "payload_too_large")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _agent_json_response(400, "invalid_payload")

    key_info = get_agent_key_info(token) or {}
    bound_agent_id = key_info.get("bound_agent_id")
    supplied_agent_id = data.get("agent_id")
    if bound_agent_id and supplied_agent_id and supplied_agent_id != bound_agent_id:
        return _agent_json_response(403, "agent_key_mismatch")
    agent_id = bound_agent_id or str(uuid.uuid4())
    existing = get_agent(agent_id)
    if bound_agent_id and not existing:
        return _agent_json_response(403, "agent_key_mismatch")

    explicit_versions = "supported_protocol_versions" in data
    versions = data.get("supported_protocol_versions")
    if explicit_versions:
        if not isinstance(versions, list) or not versions or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in versions
        ):
            return _agent_json_response(400, "invalid_payload")
        supported = sorted(set(versions).intersection({1, 2}), reverse=True)
        if not supported:
            return _agent_json_response(409, "unsupported_protocol")
        protocol_version = supported[0]
    else:
        protocol_version = 1

    received_at = datetime.now(timezone.utc).isoformat()
    session_id = secrets.token_urlsafe(32) if protocol_version == 2 else None
    display_name = data.get("display_name") or data.get("hostname") or f"agent-{agent_id[:8]}"
    capabilities = data.get("capabilities") if isinstance(data.get("capabilities"), list) else []
    capabilities = [value for value in capabilities if isinstance(value, str) and len(value) <= 64][:32]
    record = dict(existing or {})
    record.update({
        "id": agent_id,
        "display_name": record.get("display_name") if record.get("custom_name") else display_name,
        "version": data.get("agent_version") or data.get("version"),
        "last_seen": received_at,
        "status": record.get("status") or ("pending" if config.AGENT_ENROLLMENT_REQUIRED else "enrolled"),
        "protocol_version": protocol_version,
        "agent_session_id": session_id,
        "last_event_sequence": 0,
        "last_report_sequence": 0,
        "last_complete_containers": record.get("last_complete_containers"),
        "commands": record.get("commands", []),
        "meta": record.get("meta", {}),
        "capabilities": capabilities,
    })
    with state_lock:
        previous = agents.get(agent_id)
        agents[agent_id] = record
        if not save_state():
            if previous is None:
                agents.pop(agent_id, None)
            else:
                agents[agent_id] = previous
            return _agent_json_response(503, "persistence_failed")

    meta_update = dict(key_info)
    meta_update.update({"bound_agent_id": agent_id, "status": "active", "last_used_at": received_at})
    add_agent_key(token, meta_update)
    return _agent_json_response(
        200 if existing else 201,
        "registered",
        agent_id=agent_id,
        protocol_version=protocol_version,
        agent_session_id=session_id,
    )


def filter_reportable_labels(labels):
    if not isinstance(labels, dict):
        raise ValueError("labels")
    if len(labels) > config.AGENT_MAX_LABELS:
        raise OverflowError("labels")
    filtered = {}
    for key, value in labels.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("labels")
        if len(key.encode("utf-8")) > config.AGENT_MAX_LABEL_KEY_BYTES or len(value.encode("utf-8")) > config.AGENT_MAX_LABEL_VALUE_BYTES:
            raise OverflowError("labels")
        if key.startswith(("dockflare.", "cloudflare.tunnel.")):
            filtered[key] = value
    return filtered


def _validated_agent_container(value):
    if not isinstance(value, dict):
        raise ValueError("container")
    container_id = value.get("id")
    container_name = value.get("name", "unknown")
    if not isinstance(container_id, str) or not container_id:
        raise ValueError("container_id")
    if len(container_id.encode("utf-8")) > config.AGENT_MAX_CONTAINER_ID_BYTES:
        raise OverflowError("container_id")
    if not isinstance(container_name, str):
        raise ValueError("container_name")
    if len(container_name.encode("utf-8")) > config.AGENT_MAX_CONTAINER_NAME_BYTES:
        raise OverflowError("container_name")
    return {
        "id": container_id,
        "name": container_name,
        "labels": filter_reportable_labels(value.get("labels", {})),
        "status": str(value.get("status", "unknown"))[:32],
    }


def _container_source_bindings(container):
    labels = container.get("labels", {})
    bindings = set()
    hostname = get_label(labels, "hostname")
    if hostname:
        try:
            bindings.add((container["id"], get_source_rule_key(hostname, get_label(labels, "path"))))
        except ZoneResolutionError:
            pass
    index = 0
    while True:
        indexed_hostname = get_label(labels, f"{index}.hostname")
        if not indexed_hostname:
            break
        try:
            bindings.add((container["id"], get_source_rule_key(indexed_hostname, get_label(labels, f"{index}.path", get_label(labels, "path")))))
        except ZoneResolutionError:
            pass
        index += 1
    return bindings


def _agent_event_summary(event_type, received_at, protocol_version, sequence, result_code, container_id=None):
    return {
        "type": event_type,
        "received_at": received_at.isoformat(),
        "protocol_version": protocol_version,
        "sequence": sequence,
        "container_id": container_id[:12] if container_id else None,
        "result": result_code,
    }


def _handle_agent_event_request(agent_id):
    received_at = datetime.now(timezone.utc)
    token, _owner = _authenticate_agent_request()
    if not token:
        return _agent_json_response(401, "unauthorized")
    if request.content_length and request.content_length > config.AGENT_MAX_REQUEST_BYTES:
        return _agent_json_response(413, "payload_too_large")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _agent_json_response(400, "invalid_payload")
    event_type = payload.get("type")
    if not isinstance(event_type, str) or len(event_type.encode("utf-8")) > config.AGENT_MAX_EVENT_TYPE_BYTES or event_type not in {"container_start", "container_stop", "status_report", "heartbeat", "hello", "tunnel_status"}:
        return _agent_json_response(400, "invalid_payload")
    agent = get_agent(agent_id)
    if not agent or not _ensure_agent_api_key(agent_id, agent, token):
        return _agent_json_response(403, "agent_key_mismatch")
    if agent.get("decommission_operation_id"):
        return _agent_json_response(409, "agent_decommissioning")

    is_v2 = agent.get("protocol_version") == 2
    stream_field = "report_sequence" if event_type == "status_report" else "event_sequence"
    last_field = "last_report_sequence" if event_type == "status_report" else "last_event_sequence"
    sequence = None
    if is_v2:
        if payload.get("protocol_version") != 2 or payload.get("agent_session_id") != agent.get("agent_session_id"):
            return _agent_json_response(409, "registration_required")
        sequence = payload.get(stream_field)
        if isinstance(sequence, bool) or not isinstance(sequence, int) or not 1 <= sequence <= 9223372036854775807:
            return _agent_json_response(400, "invalid_payload")
        previous_sequence = int(agent.get(last_field) or 0)
        if sequence == previous_sequence:
            return _agent_json_response(200, "duplicate_sequence")
        if sequence < previous_sequence:
            return _agent_json_response(409, "stale_sequence")

    valid_containers = []
    inventory_complete = False
    inventory_malformed = False
    tunnel_status_update = None
    result_code = "accepted_noop"
    try:
        if event_type in {"container_start", "container_stop"}:
            valid_containers = [_validated_agent_container(payload.get("container"))]
        elif event_type == "status_report":
            raw_containers = payload.get("containers") if is_v2 else payload.get("containers", (payload.get("container") or {}).get("containers"))
            if is_v2 and payload.get("inventory_complete") is False and "containers" not in payload:
                raw_containers = []
            if not isinstance(raw_containers, list):
                raise ValueError("containers")
            if len(raw_containers) > config.AGENT_MAX_CONTAINERS:
                raise OverflowError("containers")
            for value in raw_containers:
                try:
                    valid_containers.append(_validated_agent_container(value))
                except ValueError:
                    inventory_malformed = True
            inventory_complete = bool(
                is_v2
                and payload.get("inventory_complete") is True
                and payload.get("inventory_scope") == "dockflare_enabled_running"
                and not inventory_malformed
            )
        elif event_type == "tunnel_status":
            tunnel_data = payload.get("tunnel") if isinstance(payload.get("tunnel"), dict) else payload
            tunnel_status_update = {
                "status": str(tunnel_data.get("status") or tunnel_data.get("state") or "unknown")[:64],
                "name": str(tunnel_data.get("name") or "")[:255],
                "version": str(tunnel_data.get("version") or "")[:128],
            }
    except OverflowError:
        return _agent_json_response(413, "payload_too_large")
    except ValueError:
        return _agent_json_response(400, "invalid_payload")

    with state_lock:
        rules_before = copy.deepcopy(managed_rules)
        agents_before = copy.deepcopy(agents)
    side_effect_plans = []
    try:
        if event_type == "container_start":
            plan = process_agent_container_start({"container": valid_containers[0]}, agent_id, defer_side_effects=True)
            if plan:
                side_effect_plans.append(plan)
            result_code = "accepted"
        elif event_type == "container_stop":
            process_agent_container_stop({"container": valid_containers[0]}, agent_id, received_at, persist=False)
            result_code = "accepted"
        elif event_type == "status_report":
            bindings = set()
            for container in valid_containers:
                bindings.update(_container_source_bindings(container))
            for container in valid_containers:
                plan = process_agent_container_start({"container": container}, agent_id, defer_side_effects=True)
                if plan:
                    side_effect_plans.append(plan)
            if inventory_complete:
                grace_period = current_app.config.get("GRACE_PERIOD_SECONDS", 28800)
                with state_lock:
                    for rule in managed_rules.values():
                        if rule.get("source") != "agent" or rule.get("agent_id") != agent_id or rule.get("status") != "active":
                            continue
                        source_key = rule.get("source_rule_key")
                        present = (rule.get("container_id"), source_key) in bindings if source_key else any(c["id"] == rule.get("container_id") for c in valid_containers)
                        if not present:
                            rule["status"] = "pending_deletion"
                            rule["delete_at"] = received_at + timedelta(seconds=grace_period)
                            rule["lifecycle_generation"] = int(rule.get("lifecycle_generation") or 0) + 1
                result_code = "accepted"
            else:
                result_code = "inventory_incomplete"
        elif event_type == "tunnel_status":
            result_code = "accepted"
    except Exception:
        with state_lock:
            managed_rules.clear()
            managed_rules.update(rules_before)
            agents.clear()
            agents.update(agents_before)
        logging.exception("AGENT_EVENT: Failed to stage event %s for agent %s", event_type, agent_id)
        return _agent_json_response(500, "processing_failed")

    with state_lock:
        current_agent = agents.get(agent_id)
        if not current_agent:
            return _agent_json_response(409, "registration_required")
        current_agent["last_seen"] = received_at.isoformat()
        if is_v2:
            current_agent[last_field] = sequence
        if event_type == "status_report" and inventory_complete:
            current_agent["last_complete_containers"] = valid_containers
        if tunnel_status_update is not None:
            current_agent["tunnel_status"] = tunnel_status_update
            current_agent["tunnel_last_seen"] = received_at.isoformat()
            current_agent["tunnel_version"] = tunnel_status_update["version"]
        container_id = valid_containers[0]["id"] if len(valid_containers) == 1 else None
        current_agent["last_event"] = _agent_event_summary(event_type, received_at, 2 if is_v2 else 1, sequence, result_code, container_id)
        if not save_state():
            managed_rules.clear()
            managed_rules.update(rules_before)
            agents.clear()
            agents.update(agents_before)
            return _agent_json_response(503, "persistence_failed")
    publish_state_event("snapshot_refresh")
    for plan in _coalesce_agent_start_plans(side_effect_plans):
        _execute_agent_start_plan(plan)
    http_status = 200 if result_code == "accepted" else 202
    return _agent_json_response(http_status, result_code)


@api_v2_bp.route('/agents/register', methods=['POST'])
def agents_register():
    """
    Agent registration endpoint.
    Agent authenticates with Authorization: Bearer <API_KEY>
    Body may include optional 'agent_id', 'display_name', 'version'.
    Returns agent_id and enrollment status.
    """
    return _register_agent_request()

@api_v2_bp.route('/agents/<agent_id>/commands', methods=['GET'])
def agents_get_commands(agent_id):
    """
    Agents poll this endpoint to fetch pending commands.
    Auth via API key.
    Returns list of pending commands and clears them.
    """
    token, owner = _authenticate_agent_request()
    if not token:
        return jsonify({"status": "error", "message": "Missing or invalid Authorization header."}), 401

    agent = get_agent(agent_id)
    if not agent:
        return jsonify({"status": "error", "message": "Agent not found."}), 404

    if not _ensure_agent_api_key(agent_id, agent, token):
        return jsonify({"status": "error", "message": "API key mismatch for agent."}), 403
    agent = get_agent(agent_id)

    commands = list(agent.get("commands", []))
    durable_command = agent_decommission.command_for_agent(agent_id)
    if durable_command:
        commands.append(durable_command)
    # clear commands after delivery
    update_agent(agent_id, {"commands": [], "last_seen": datetime.now(timezone.utc).isoformat()})
    return jsonify({"status": "success", "commands": commands}), 200


@api_v2_bp.route('/agents/<agent_id>/decommission/<operation_id>/ack', methods=['POST'])
def agents_decommission_ack(agent_id, operation_id):
    token = _extract_bearer_token()
    if not token:
        return _agent_json_response(401, "unauthorized")
    if request.content_length and request.content_length > config.AGENT_MAX_REQUEST_BYTES:
        return _agent_json_response(413, "payload_too_large")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _agent_json_response(400, "invalid_payload")
    key_info = get_agent_key_info(token) or {}
    if not key_info:
        return _agent_json_response(401, "unauthorized")
    agent = get_agent(agent_id)
    operation = agent_decommission.get_operation(operation_id)
    if not agent:
        duplicate_final = (
            operation
            and operation.get("agent_id") == agent_id
            and operation.get("state") in agent_decommission.TERMINAL_STATES
            and key_info.get("bound_agent_id") == agent_id
            and key_info.get("status") == "revoked"
            and payload.get("command_id") in operation.get("acknowledged_commands", [])
        )
        if duplicate_final:
            return _agent_json_response(200, "acknowledged", operation=agent_decommission.serialize_operation(operation))
        return _agent_json_response(403, "agent_key_mismatch")
    if not _ensure_agent_api_key(agent_id, agent, token):
        return _agent_json_response(403, "agent_key_mismatch")
    if agent.get("protocol_version") == 2 and payload.get("agent_session_id") != agent.get("agent_session_id"):
        return _agent_json_response(409, "registration_required")
    try:
        operation, should_cleanup = agent_decommission.record_ack(agent_id, operation_id, payload)
        if should_cleanup:
            operation = agent_decommission.run_master_cleanup(operation_id)
        elif operation.get("state") == "shutdown_scheduled":
            operation = agent_decommission.complete_finalization(operation_id)
        return _agent_json_response(
            200,
            "acknowledged",
            operation=agent_decommission.serialize_operation(operation),
        )
    except agent_decommission.DecommissionError as error:
        return _agent_json_response(error.http_status, error.code)

@api_v2_bp.route('/agents/<agent_id>/events', methods=['POST'])
def agents_post_events(agent_id):
    """
    Agents POST events (container start/stop, tunnel status).
    Auth via API key.
    """
    return _handle_agent_event_request(agent_id)

    logging.info(f"AGENTS_EVENTS: Received request for agent {agent_id}")
    token, owner = _authenticate_agent_request()
    if not token:
        logging.info(f"AGENTS_EVENTS: Authentication failed for agent {agent_id}")
        return jsonify({"status": "error", "message": "Missing or invalid Authorization header."}), 401

    payload = request.get_json() or {}
    if not payload:
        logging.info(f"AGENTS_EVENTS: Empty payload for agent {agent_id}")
        return jsonify({"status": "error", "message": "Empty payload."}), 400

    agent = get_agent(agent_id)
    if not agent:
        logging.info(f"AGENTS_EVENTS: Agent not found: {agent_id}")
        return jsonify({"status": "error", "message": "Agent not found."}), 404

    if not _ensure_agent_api_key(agent_id, agent, token):
        logging.info(f"AGENTS_EVENTS: API key mismatch for agent {agent_id}")
        return jsonify({"status": "error", "message": "API key mismatch for agent."}), 403
    agent = get_agent(agent_id)

    logging.info(f"AGENTS_EVENTS: Processing event for agent {agent_id}: {payload.get('type')}")

    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    update_agent(agent_id, {"last_seen": now, "last_event": payload})
    
    event_type = payload.get("type")
    if event_type == "container_start":
        logging.info(f"AGENTS_EVENTS: Processing container_start event for agent {agent_id}")
        process_agent_container_start(payload, agent_id)
    elif event_type == "container_stop":
        process_agent_container_stop(payload, agent_id)
    elif event_type == "status_report":
        
        logging.info(f"AGENTS_EVENTS: Processing status_report from agent {agent_id}")

        containers = payload.get("containers") or (payload.get("container", {}) or {}).get("containers") or []
        
        try:
            update_agent(agent_id, {"last_containers": containers})
        except Exception as e:
            logging.error(f"Failed to store container data for agent {agent_id}: {e}")
        try:
            reported_ids = set()
            for c in containers:
        
                container_payload = {"container": {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "labels": c.get("labels", {})
                }}
                try:
                    process_agent_container_start(container_payload, agent_id)
                    if c.get("id"):
                        reported_ids.add(c.get("id"))
                except Exception as e:
                    logging.error(f"AGENTS_EVENTS: Failed to process reported container for agent {agent_id}: {e}", exc_info=True)
        
            try:
                grace_period = current_app.config.get('GRACE_PERIOD_SECONDS', 28800)
                with state_lock:
                    rules_marked = 0
                    for rule_key, rule in list(managed_rules.items()):
                        if rule.get("source") == "agent" and rule.get("agent_id") == agent_id:
                            cont_id = rule.get("container_id")
                            if cont_id and cont_id not in reported_ids and rule.get("status") == "active":
                                rule["status"] = "pending_deletion"
                                rule["delete_at"] = datetime.now(timezone.utc) + timedelta(seconds=grace_period)
                                rules_marked += 1
                    if rules_marked:
                        logging.info(f"AGENTS_EVENTS: Marked {rules_marked} agent-managed rules for agent {agent_id} as pending_deletion due to missing containers in status_report.")
                        save_state()
                        publish_state_event('snapshot_refresh')
            except Exception as e:
                logging.error(f"AGENTS_EVENTS: Error while marking missing agent rules pending_deletion for {agent_id}: {e}", exc_info=True)
        except Exception as e:
            logging.error(f"AGENTS_EVENTS: Error processing status_report from agent {agent_id}: {e}", exc_info=True)
       
        try:
            from app.core.reconciler import reconcile_agent_report
            import threading as _threading
            _threading.Thread(target=reconcile_agent_report, args=(agent_id, containers), name=f"ReconcileAgent-{agent_id}", daemon=True).start()
            logging.info(f"AGENTS_EVENTS: Launched reconcile_agent_report for agent {agent_id}")
        except Exception as _re_exc:
            logging.error(f"AGENTS_EVENTS: Failed to start reconcile_agent_report for agent {agent_id}: {_re_exc}", exc_info=True)

        try:
            from app.core.migration_service import TunnelMigrationService

            agent_record = get_agent(agent_id)
            if agent_record:
                assigned_tunnel_id = agent_record.get("assigned_tunnel_id")
                migration_status = agent_record.get("migration_status")

                if (assigned_tunnel_id and
                    containers and
                    (not migration_status or not migration_status.get("completed_at"))):

                    def run_migration_analysis():
                        try:
                            result = TunnelMigrationService.trigger_migration_analysis(
                                agent_id, assigned_tunnel_id, containers
                            )
                            logging.info(f"MIGRATION: Analysis result for agent {agent_id}: {result}")
                        except Exception as e:
                            logging.error(f"MIGRATION: Error during migration analysis for agent {agent_id}: {e}")

                    _threading.Thread(target=run_migration_analysis, name=f"MigrationAnalysis-{agent_id}", daemon=True).start()

        except Exception as _mig_exc:
            logging.error(f"AGENTS_EVENTS: Failed to trigger migration analysis for agent {agent_id}: {_mig_exc}", exc_info=True)

    elif event_type in ["heartbeat", "hello"]:
        logging.debug(f"AGENTS_EVENTS: Heartbeat received from agent {agent_id}")
    elif event_type == "tunnel_status":
        try:
            tunnel_info = payload.get("tunnel") or payload
            status = tunnel_info.get("status") or payload.get("status") or tunnel_info.get("state") or "unknown"
            name = tunnel_info.get("name") or payload.get("name")
            version = tunnel_info.get("version") or payload.get("version")
            now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            update_agent(agent_id, {
                "tunnel_status": {"status": status, "name": name, "version": version},
                "tunnel_last_seen": now,
                "tunnel_version": version
            })
            logging.info(f"AGENTS_EVENTS: Updated tunnel_status for agent {agent_id}: {status}")
        except Exception as e:
            logging.error(f"AGENTS_EVENTS: Failed processing tunnel_status for agent {agent_id}: {e}", exc_info=True)

    return jsonify({"status": "success", "message": "Event received and processed."}), 202

@api_v2_bp.route('/agents/<agent_id>/enroll', methods=['POST'])
def agents_enroll(agent_id):
    """
    Admin endpoint to enroll an agent and assign a tunnel.
    Payload: { "tunnel_name": "<tunnel_name>" }
    On success, Master will create tunnel via Cloudflare API and return token; a start_tunnel command is queued for the agent.
    """
    data = request.get_json() or {}
    tunnel_name = data.get("tunnel_name")
    if not tunnel_name:
        return jsonify({"status": "error", "message": "Missing 'tunnel_name' in payload."}), 400

    agent = get_agent(agent_id)
    if not agent:
        return jsonify({"status": "error", "message": "Agent not found."}), 404
    if agent.get("decommission_operation_id"):
        return jsonify({"status": "error", "message": "Agent decommission is in progress."}), 409

    old_tunnel_id = agent.get("assigned_tunnel_id")
    try:
        from app.core.cloudflare_api import find_tunnel_via_api, create_tunnel_via_api
        found_id, found_token = find_tunnel_via_api(tunnel_name)
        if not found_id:
            created_id, created_token = create_tunnel_via_api(tunnel_name)
            tunnel_id = created_id
            token = created_token
            tunnel_ownership = "created_exclusive"
        else:
            tunnel_id = found_id
            token = found_token
            tunnel_ownership = "adopted"

        if not tunnel_id:
            return jsonify({"status": "error", "message": "Failed to create/find tunnel."}), 500

        cmd = {"action": "start_tunnel", "tunnel_name": tunnel_name, "tunnel_id": tunnel_id, "token": token}
        existing_cmds = agent.get("commands", [])
        existing_cmds.append(cmd)
        update_agent(agent_id, {
            "assigned_tunnel_name": tunnel_name,
            "assigned_tunnel_id": tunnel_id,
            "assigned_tunnel_token": token,
            "assigned_tunnel_ownership": tunnel_ownership,
            "status": "enrolled",
            "commands": existing_cmds,
            "last_enrolled_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
        })

        with state_lock:
            rules_updated = False
            for rule in managed_rules.values():
                if rule.get("source") == "agent" and rule.get("agent_id") == agent_id:
                    if rule.get("tunnel_name") != tunnel_name or rule.get("tunnel_id") != tunnel_id:
                        rule["tunnel_name"] = tunnel_name
                        rule["tunnel_id"] = tunnel_id
                        rule["tunnel_sync_pending"] = True
                        rule["lifecycle_generation"] = int(rule.get("lifecycle_generation") or 0) + 1
                        rules_updated = True
            if rules_updated:
                logging.info(f"Updated {len([r for r in managed_rules.values() if r.get('agent_id') == agent_id])} rules for agent {agent_id} with tunnel name '{tunnel_name}'.")
                save_state()

        old_updated = not old_tunnel_id or old_tunnel_id == tunnel_id or update_cloudflare_config(old_tunnel_id)
        new_updated = update_cloudflare_config(tunnel_id)
        if old_updated and new_updated:
            dns_targets = []
            with state_lock:
                for rule in managed_rules.values():
                    if rule.get("source") == "agent" and rule.get("agent_id") == agent_id:
                        rule["tunnel_sync_pending"] = False
                        rule["tunnel_sync_attempts"] = 0
                        rule["tunnel_sync_last_attempt_at"] = None
                        if rule.get("hostname") and rule.get("zone_id"):
                            dns_targets.append((rule["zone_id"], rule["hostname"]))
                save_state()
            for zone_id, hostname in dns_targets:
                if not hostname.startswith("*."):
                    create_cloudflare_dns_record(zone_id, hostname, tunnel_id)

        return jsonify({"status": "success", "message": "Agent enrolled and command queued.", "command": cmd}), 200
    except Exception as e:
        logging.error(f"Error enrolling agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Exception during enrollment: {e}"}), 500


def _start_agent_decommission_response(agent_id):
    try:
        operation, _created = agent_decommission.start_decommission(agent_id)
        public_operation = agent_decommission.serialize_operation(operation)
        return jsonify({
            "status": "accepted",
            "operation_id": operation["operation_id"],
            "operation": public_operation,
            "status_url": f"/api/v2/agent-decommissions/{operation['operation_id']}",
        }), 202
    except agent_decommission.DecommissionError as error:
        return jsonify({"status": "error", "code": error.code, "message": error.code}), error.http_status


@api_v2_bp.route('/agents/<agent_id>/decommission', methods=['POST'])
def agents_decommission_start(agent_id):
    return _start_agent_decommission_response(agent_id)


@api_v2_bp.route('/agents/<agent_id>/decommission-preview', methods=['GET'])
def agents_decommission_preview(agent_id):
    try:
        return jsonify({
            "status": "success",
            "preview": agent_decommission.preview_decommission(agent_id),
        }), 200
    except agent_decommission.DecommissionError as error:
        return jsonify({"status": "error", "code": error.code, "message": error.code}), error.http_status


@api_v2_bp.route('/agent-decommissions/<operation_id>', methods=['GET'])
def agents_decommission_status(operation_id):
    operation = agent_decommission.get_operation(operation_id)
    if not operation:
        return jsonify({"status": "error", "code": "operation_not_found", "message": "operation_not_found"}), 404
    return jsonify({"status": "success", "operation": agent_decommission.serialize_operation(operation)}), 200


@api_v2_bp.route('/agent-decommissions/<operation_id>/retry', methods=['POST'])
def agents_decommission_retry(operation_id):
    try:
        operation = agent_decommission.retry_operation(operation_id)
        return jsonify({"status": "accepted", "operation": agent_decommission.serialize_operation(operation)}), 202
    except agent_decommission.DecommissionError as error:
        return jsonify({"status": "error", "code": error.code, "message": error.code}), error.http_status


@api_v2_bp.route('/agent-decommissions/<operation_id>/force', methods=['POST'])
def agents_decommission_force(operation_id):
    try:
        operation = agent_decommission.force_cleanup(operation_id)
        return jsonify({"status": "success", "operation": agent_decommission.serialize_operation(operation)}), 200
    except agent_decommission.DecommissionError as error:
        return jsonify({"status": "error", "code": error.code, "message": error.code}), error.http_status

@api_v2_bp.route('/agents/<agent_id>/remove', methods=['POST'])
def agents_remove(agent_id):
    return _start_agent_decommission_response(agent_id)


def _agent_decommission_blocks_action(agent_record):
    return bool(agent_record and agent_record.get("decommission_operation_id"))

@api_v2_bp.route('/agents/<agent_id>/trigger-migration', methods=['POST'])
def trigger_agent_migration(agent_id):
    try:
        from app.core.migration_service import TunnelMigrationService
        from app.core.state_manager import get_agent

        agent_record = get_agent(agent_id)
        if not agent_record:
            return jsonify({"status": "error", "message": "Agent not found."}), 404
        if _agent_decommission_blocks_action(agent_record):
            return jsonify({"status": "error", "message": "Agent decommission is in progress."}), 409

        assigned_tunnel_id = agent_record.get("assigned_tunnel_id")
        if not assigned_tunnel_id:
            return jsonify({"status": "error", "message": "Agent not assigned to a tunnel."}), 400
        
        containers = agent_record.get("last_containers", [])
        if not containers:
            return jsonify({"status": "error", "message": "No container data available. The agent must report container data before migration can be triggered. Please ensure the agent is running and connected, then wait for the next heartbeat (typically 30 seconds)."}), 400

        result = TunnelMigrationService.trigger_migration_analysis(
            agent_id, assigned_tunnel_id, containers
        )

        return jsonify({
            "status": "success",
            "message": "Migration analysis triggered successfully.",
            "result": result
        }), 200

    except Exception as e:
        logging.error(f"Failed to trigger migration for agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to trigger migration: {str(e)}"}), 500

@api_v2_bp.route('/agents/<agent_id>/redeploy-tunnel', methods=['POST'])
def redeploy_agent_tunnel(agent_id):
    try:
        from app.core.state_manager import get_agent, queue_agent_command

        agent_record = get_agent(agent_id)
        if not agent_record:
            return jsonify({"status": "error", "message": "Agent not found."}), 404
        if _agent_decommission_blocks_action(agent_record):
            return jsonify({"status": "error", "message": "Agent decommission is in progress."}), 409

        if agent_record.get("status") != "enrolled":
            return jsonify({"status": "error", "message": "Agent not enrolled."}), 400

        tunnel_name = agent_record.get("assigned_tunnel_name")
        tunnel_id = agent_record.get("assigned_tunnel_id")
        tunnel_token = agent_record.get("assigned_tunnel_token")

        if not all([tunnel_name, tunnel_id, tunnel_token]):
            return jsonify({"status": "error", "message": "Agent missing tunnel configuration."}), 400

        command = {
            "action": "restart_tunnel",
            "tunnel_name": tunnel_name,
            "tunnel_id": tunnel_id,
            "tunnel_token": tunnel_token
        }

        queue_agent_command(agent_id, command)

        return jsonify({
            "status": "success",
            "message": "Tunnel redeploy command queued successfully."
        }), 200

    except Exception as e:
        logging.error(f"Failed to queue redeploy command for agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to queue redeploy command: {str(e)}"}), 500

@api_v2_bp.route('/agents/<agent_id>/roll-key', methods=['POST'])
def roll_agent_api_key(agent_id):
    try:
        from app.core.state_manager import get_agent, update_agent, revoke_agent_key, add_agent_key
        import secrets
        from datetime import datetime, timezone

        agent_record = get_agent(agent_id)
        if not agent_record:
            return jsonify({"status": "error", "message": "Agent not found."}), 404
        if _agent_decommission_blocks_action(agent_record):
            return jsonify({"status": "error", "message": "Agent decommission is in progress."}), 409

        old_api_key = agent_record.get("api_key")

        new_api_key = secrets.token_urlsafe(32)

        success = update_agent(agent_id, {"api_key": new_api_key})
        if not success:
            return jsonify({"status": "error", "message": "Failed to update agent with new API key."}), 500

        if old_api_key:
            revoke_agent_key(old_api_key)

        now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
        add_agent_key(new_api_key, {
            "bound_agent_id": agent_id,
            "created_at": now_iso,
            "last_used_at": None,
            "rolled_from": old_api_key[:8] + "..." if old_api_key else None
        })

        return jsonify({
            "status": "success",
            "message": f"API key rolled successfully for agent '{agent_record.get('display_name', agent_id)}'.",
            "new_key": new_api_key
        }), 200

    except Exception as e:
        logging.error(f"Failed to roll API key for agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to roll API key: {str(e)}"}), 500

@api_v2_bp.route('/agents/<agent_id>/rename', methods=['POST'])
def rename_agent(agent_id):
    try:
        from app.core.state_manager import get_agent, update_agent

        agent_record = get_agent(agent_id)
        if not agent_record:
            return jsonify({"status": "error", "message": "Agent not found."}), 404
        if _agent_decommission_blocks_action(agent_record):
            return jsonify({"status": "error", "message": "Agent decommission is in progress."}), 409

        data = request.get_json() or {}
        display_name = data.get('display_name', '').strip()

        if not display_name:
            return jsonify({"status": "error", "message": "Display name is required."}), 400

        update_agent(agent_id, {
            "display_name": display_name,
            "custom_name": True
        })

        return jsonify({
            "status": "success",
            "message": "Agent renamed successfully."
        }), 200

    except Exception as e:
        logging.error(f"Failed to rename agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Failed to rename agent: {str(e)}"}), 500

@api_v2_bp.route('/agent/start', methods=['POST'])
def agent_start():
    if config.USE_EXTERNAL_CLOUDFLARED:
        return jsonify({"status": "error", "message": "Cannot start agent: configured for external cloudflared."}),
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client not available."}),
        
    start_cloudflared_container()
    time.sleep(0.5)
    return jsonify({
        "status": "success",
        "message": "Agent start command issued.",
        "agent_state": cloudflared_agent_state.copy()
    }), 202 

@api_v2_bp.route('/agent/stop', methods=['POST'])
def agent_stop():
    if config.USE_EXTERNAL_CLOUDFLARED:
        return jsonify({"status": "error", "message": "Cannot stop agent: configured for external cloudflared."}),
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client not available."}),

    stop_cloudflared_container()
    time.sleep(0.5)
    return jsonify({
        "status": "success",
        "message": "Agent stop command issued.",
        "agent_state": cloudflared_agent_state.copy()
    }), 202 

@api_v2_bp.route('/rules/manual/<path:rule_key>', methods=['DELETE'])
def delete_manual_rule(rule_key):
    if not docker_client:
        return jsonify({"status": "error", "message": "System not ready."}),

    zone_id_for_delete = None
    access_app_id_for_delete = None
    hostname_for_dns_operations = None
    rule_deleted_from_state = False
    tunnel_id_for_delete = None

    with state_lock:
        rule_details = managed_rules.get(rule_key)
        if not rule_details or rule_details.get("source") != "manual":
            return jsonify({"status": "error", "message": f"Manual rule '{rule_key}' not found or not a manual rule."}),
        
        zone_id_for_delete = rule_details.get("zone_id")
        access_app_id_for_delete = rule_details.get("access_app_id")
        hostname_for_dns_operations = rule_details.get("hostname")
        tunnel_id_for_delete = rule_details.get("tunnel_id") or get_effective_tunnel_id()
        
        del managed_rules[rule_key]
        save_state()
        rule_deleted_from_state = True

    dns_deleted_ok = True 
    access_app_deleted_ok = True 

    should_delete_dns = True
    if hostname_for_dns_operations:
        with state_lock:
            for other_rule in managed_rules.values():
                if other_rule.get("hostname") == hostname_for_dns_operations:
                    should_delete_dns = False
                    break
    else:
        should_delete_dns = False 

    if should_delete_dns and zone_id_for_delete and tunnel_id_for_delete:
        if not delete_cloudflare_dns_record(zone_id_for_delete, hostname_for_dns_operations, tunnel_id_for_delete):
            dns_deleted_ok = False
            logging.error(f"API: Failed to delete DNS record for {hostname_for_dns_operations} from manual rule {rule_key}.")

    should_delete_access_app = True
    if access_app_id_for_delete:
        with state_lock:
            for other_rule_key, other_rule in managed_rules.items():
                if other_rule.get("access_app_id") == access_app_id_for_delete:
                    should_delete_access_app = False
                    logging.info(f"API: Access App ID {access_app_id_for_delete} for rule {rule_key} is shared by rule {other_rule_key}. Not deleting.")
                    break
        if should_delete_access_app:
            if not delete_cloudflare_access_application(access_app_id_for_delete):
                access_app_deleted_ok = False
                logging.error(f"API: Failed to delete Access App {access_app_id_for_delete} from manual rule {rule_key}.")
    
    config_update_success = update_cloudflare_config(tunnel_id_for_delete)

    publish_state_event('snapshot_refresh')

    if config_update_success:
        message = f"Manual rule {rule_key} deleted."
        if not dns_deleted_ok:
            message += " DNS deletion failed or skipped."
        if not access_app_deleted_ok:
            message += " Access App deletion failed or skipped."
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "warning", "message": f"Manual rule {rule_key} removed from state, but Cloudflare tunnel config update FAILED."}), 207 # Multi-Status

@api_v2_bp.route('/rules/<path:rule_key>/force-delete', methods=['POST']) 
def force_delete_rule(rule_key):
    effective_tunnel_id = get_effective_tunnel_id()
    if not effective_tunnel_id:
        return jsonify({"status": "error", "message": "Tunnel not initialized."}),

    zone_id_for_delete = None
    access_app_id_for_delete = None
    hostname_for_dns = None
    rule_details_copy = None

    with state_lock:
        rule_details = managed_rules.get(rule_key)
        if not rule_details:
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' not found."}),
        
        rule_details_copy = rule_details.copy() 
        zone_id_for_delete = rule_details_copy.get("zone_id")
        access_app_id_for_delete = rule_details_copy.get("access_app_id")
        hostname_for_dns = rule_details_copy.get("hostname")
        
        del managed_rules[rule_key]
        save_state()

    dns_deleted = True 
    if zone_id_for_delete and hostname_for_dns:
        is_dns_shared = False
        with state_lock:
            for other_rule in managed_rules.values():
                if other_rule.get("hostname") == hostname_for_dns:
                    is_dns_shared = True
                    break
        if not is_dns_shared:
            if not delete_cloudflare_dns_record(zone_id_for_delete, hostname_for_dns, effective_tunnel_id):
                dns_deleted = False
        else:
            logging.info(f"API Force Delete: DNS for {hostname_for_dns} (rule {rule_key}) not deleted as it's shared.")

    access_app_deleted = True 
    if access_app_id_for_delete:
        is_app_shared = False
        with state_lock:
            for other_rule in managed_rules.values():
                if other_rule.get("access_app_id") == access_app_id_for_delete:
                    is_app_shared = True
                    break
        if not is_app_shared:
            if not delete_cloudflare_access_application(access_app_id_for_delete):
                access_app_deleted = False
        else:
            logging.info(f"API Force Delete: Access App {access_app_id_for_delete} (rule {rule_key}) not deleted as it's shared.")

    config_updated = update_cloudflare_config()

    status_code = 200
    results = {
        "dns_deleted": dns_deleted,
        "access_app_deleted": access_app_deleted,
        "config_updated": config_updated
    }
    if not all(results.values()):
        status_code = 207 

    return jsonify({
        "status": "success" if status_code == 200 else "warning",
        "message": f"Rule '{rule_key}' force deleted. See details.",
        "details": results
    }), status_code

@api_v2_bp.route('/rules/<path:rule_key>/access-policy', methods=['PUT'])
def update_rule_access_policy(rule_key):
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client unavailable."}),

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON payload."}),

    new_policy_type = data.get('access_policy_type') 
    auth_email = data.get('auth_email', '').strip()
    session_duration = data.get('session_duration', '24h') 
    app_launcher_visible = data.get('app_launcher_visible', False)
    allowed_idps_str = data.get('allowed_idps_str') 
    auto_redirect = data.get('auto_redirect', False)
    
    action_status_message = f"Processing UI policy update for {rule_key}..."
    state_changed_locally = False
    operation_successful = False
    final_rule_state = None

    with state_lock:
        current_rule = managed_rules.get(rule_key)
        if not current_rule:
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' not found."}),
        
        hostname_for_access_app = current_rule.get("hostname")
        if not hostname_for_access_app:
            hostname_for_access_app = rule_key.split('|')[0]
            if not hostname_for_access_app:
                return jsonify({"status": "error", "message": f"Cannot determine hostname for Access App for rule '{rule_key}'."}),

        rule_path = normalize_path_value(current_rule.get("path"))
        application_domain = hostname_for_access_app if not rule_path else f"{hostname_for_access_app}{rule_path}"

        path_identifier = ""
        if rule_path:
            path_identifier = rule_path.lstrip('/') or "root"
            path_identifier = path_identifier.replace('/', '-').replace(' ', '-')

        current_access_app_id = current_rule.get("access_app_id")
        session_duration = data.get('session_duration', current_rule.get("access_session_duration", "24h"))
        app_launcher_visible = data.get('app_launcher_visible', current_rule.get("access_app_launcher_visible", False))
        allowed_idps_str = data.get('allowed_idps_str', current_rule.get("access_allowed_idps_str"))
        auto_redirect = data.get('auto_redirect', current_rule.get("access_auto_redirect", False))

        desired_app_name = f"DockFlare-{hostname_for_access_app}"
        if path_identifier:
            desired_app_name = f"{desired_app_name}-{path_identifier}"
        cf_access_policies = []
        final_policy_type_for_state = new_policy_type
        custom_rules_for_hash = None

        if new_policy_type == "none" or new_policy_type == "public_no_policy":
            if current_access_app_id:
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = None
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                    operation_successful = True
                else: action_status_message = f"Error: Failed to delete Access App for {rule_key}."
            else: 
                if current_rule.get("access_policy_type") is not None:
                    current_rule["access_policy_type"] = None
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
            final_policy_type_for_state = None
        
        elif new_policy_type == "default_tld":
            if current_access_app_id: 
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None 
                    state_changed_locally = True
                    operation_successful = True
                else: action_status_message = f"Error: Failed to delete Access App for {rule_key} for TLD switch."
            else:
                if current_rule.get("access_policy_type") != "default_tld":
                    current_rule["access_app_id"] = None 
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
            final_policy_type_for_state = "default_tld"

        elif new_policy_type == "bypass":
            cf_access_policies = [{"name": "API Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            custom_rules_for_hash = json.dumps(cf_access_policies)
        
        elif new_policy_type == "authenticate_email":
            if not auth_email:
                return jsonify({"status": "error", "message": "Auth Email required for 'authenticate_email' policy."}),
            cf_access_policies = [
                {"name": f"API Allow Email {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
                {"name": "API Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
            ]
            custom_rules_for_hash = json.dumps(cf_access_policies)
        
        if new_policy_type in ["bypass", "authenticate_email"]:
            if not cf_access_policies:
                return jsonify({"status": "error", "message": "Internal: No policies defined."}),
            
            new_config_hash = generate_access_app_config_hash(
                final_policy_type_for_state, session_duration, app_launcher_visible,
                allowed_idps_str, auto_redirect, custom_access_rules_str=custom_rules_for_hash
            )
            allowed_idps_list_for_app = [idp.strip() for idp in allowed_idps_str.split(',') if idp.strip()] if allowed_idps_str else None

            effective_app_id_for_operation = current_access_app_id
            if not effective_app_id_for_operation: 
                existing_cf_app = find_cloudflare_access_application_by_domain(application_domain)
                if existing_cf_app and existing_cf_app.get("id"):
                    effective_app_id_for_operation = existing_cf_app.get("id")
                    logging.info(f"Found existing Access App ID '{effective_app_id_for_operation}' on Cloudflare for {application_domain}. Will update.")
                    current_rule["access_app_id"] = effective_app_id_for_operation 
                    state_changed_locally = True
            
            if effective_app_id_for_operation:
                if current_rule.get("access_policy_type") != final_policy_type_for_state or \
                   current_rule.get("access_app_config_hash") != new_config_hash or \
                   current_rule.get("access_app_id") != effective_app_id_for_operation: 
                    
                    updated_app = update_cloudflare_access_application(
                        effective_app_id_for_operation, application_domain, desired_app_name,
                        session_duration, app_launcher_visible, [application_domain],
                        cf_access_policies, allowed_idps_list_for_app, auto_redirect
                    )
                    if updated_app:
                        current_rule["access_app_id"] = updated_app.get("id")
                        current_rule["access_policy_type"] = final_policy_type_for_state
                        current_rule["access_app_config_hash"] = new_config_hash
                        current_rule["access_session_duration"] = session_duration
                        current_rule["access_app_launcher_visible"] = app_launcher_visible
                        current_rule["access_allowed_idps_str"] = allowed_idps_str
                        current_rule["access_auto_redirect"] = auto_redirect
                        current_rule["auth_email"] = auth_email if final_policy_type_for_state == "authenticate_email" else None
                        state_changed_locally = True
                        operation_successful = True
                    else:
                        action_status_message = f"Error: Failed to update Access App for {rule_key}."
                else:
                    operation_successful = True
                    action_status_message = "No change in policy needed."
            else:
                created_app = create_cloudflare_access_application(
                    application_domain, desired_app_name,
                    session_duration, app_launcher_visible, [application_domain],
                    cf_access_policies, allowed_idps_list_for_app, auto_redirect
                )
                if created_app and created_app.get("id"):
                    current_rule["access_app_id"] = created_app.get("id")
                    current_rule["access_policy_type"] = final_policy_type_for_state
                    current_rule["access_app_config_hash"] = new_config_hash
                    current_rule["access_session_duration"] = session_duration
                    current_rule["access_app_launcher_visible"] = app_launcher_visible
                    current_rule["access_allowed_idps_str"] = allowed_idps_str
                    current_rule["access_auto_redirect"] = auto_redirect
                    current_rule["auth_email"] = auth_email if final_policy_type_for_state == "authenticate_email" else None
                    state_changed_locally = True
                    operation_successful = True
                else:
                    action_status_message = f"Error: Failed to create Access App for {rule_key}."

        if operation_successful:
            current_rule["access_policy_ui_override"] = True 
            state_changed_locally = True 

        if state_changed_locally:
            save_state()
        
        final_rule_state = serialize_rule(current_rule)

    if operation_successful:
        return jsonify({"status": "success", "message": f"Access policy for {rule_key} updated to {final_policy_type_for_state}.", "rule": final_rule_state}), 200
    else:
        return jsonify({"status": "error", "message": action_status_message, "rule": final_rule_state}), 500

@api_v2_bp.route('/rules/<path:rule_key>/access-policy/revert-to-labels', methods=['POST'])
def revert_rule_access_policy_to_labels(rule_key):
    app_id_to_delete_if_any = None
    state_changed_for_revert = False
    initial_rule_source = None

    with state_lock:
        current_rule = managed_rules.get(rule_key)
        if not current_rule:
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' not found."}),
        
        initial_rule_source = current_rule.get("source")
        if not current_rule.get("access_policy_ui_override", False):
            return jsonify({"status": "info", "message": f"Access policy for '{rule_key}' is not UI-overridden. No action taken."}),


        if initial_rule_source == "manual":
            app_id_to_delete_if_any = current_rule.get("access_app_id")
            current_rule["access_policy_ui_override"] = False
            current_rule["access_app_id"] = None
            current_rule["access_policy_type"] = None 
            current_rule["access_app_config_hash"] = None
            current_rule["access_session_duration"] = "24h" # Default
            current_rule["access_app_launcher_visible"] = False
            current_rule["access_allowed_idps_str"] = None
            current_rule["access_auto_redirect"] = False
            current_rule["auth_email"] = None
            state_changed_for_revert = True
            logging.info(f"API: Reverting manual rule '{rule_key}' access policy to none/public.")
        elif initial_rule_source in {"docker", "agent"}:
            current_rule["access_policy_ui_override"] = False
            state_changed_for_revert = True
            logging.info(f"API: Reverting container-backed rule '{rule_key}' access policy to be label-driven.")
        else: 
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' has unknown source '{initial_rule_source}'."}), 500

        if state_changed_for_revert:
            current_rule["lifecycle_generation"] = int(current_rule.get("lifecycle_generation") or 0) + 1
            save_state()

    if initial_rule_source == "manual" and app_id_to_delete_if_any:
        is_shared = False
        with state_lock:
            for r_key, r_val in managed_rules.items():
                if r_key != rule_key and r_val.get("access_app_id") == app_id_to_delete_if_any:
                    is_shared = True
                    break
        if not is_shared:
            if delete_cloudflare_access_application(app_id_to_delete_if_any):
                logging.info(f"API: Deleted Access App {app_id_to_delete_if_any} for reverted manual rule '{rule_key}'.")
            else:
                logging.warning(f"API: Failed to delete Access App {app_id_to_delete_if_any} for reverted manual rule '{rule_key}'.")
        else:
            logging.info(f"API: Access App {app_id_to_delete_if_any} for reverted manual rule '{rule_key}' is shared, not deleting.")

    if initial_rule_source == "docker" and docker_client:
        reconcile_state_threaded()
    elif initial_rule_source == "agent":
        agent_id = current_rule.get("agent_id")
        agent = get_agent(agent_id)
        containers = agent.get("last_complete_containers") if agent else None
        if agent_inventory_contains_rule(containers, current_rule):
            from app.core.reconciler import reconcile_agent_report
            reconcile_agent_report(agent_id, containers)
    return jsonify({"status": "success", "message": f"Access policy for '{rule_key}' reverted."}),

@api_v2_bp.route('/tunnels/account', methods=['GET'])
def get_account_tunnels_api():
    tunnels = get_all_account_cloudflare_tunnels()
    return jsonify({"tunnels": tunnels})

@api_v2_bp.route('/tunnels/<tunnel_id>/dns-records', methods=['GET'])
def get_tunnel_dns_records_api(tunnel_id):
    if not tunnel_id:
        return jsonify({"error": "Tunnel ID is required"}), 400
    
    all_found_dns_records = []
    zone_ids_to_scan = set()
    cf_zone_id = current_app.config.get('CF_ZONE_ID')
    if cf_zone_id:
        zone_ids_to_scan.add(cf_zone_id)
    with state_lock:
        zone_ids_to_scan.update(
            rule.get("zone_id")
            for rule in managed_rules.values()
            if rule.get("status") == "active" and rule.get("zone_id")
        )
    
    scan_zone_names_list = current_app.config.get('TUNNEL_DNS_SCAN_ZONE_NAMES', [])
    if isinstance(scan_zone_names_list, str) and scan_zone_names_list: 
        scan_zone_names_list = [z.strip() for z in scan_zone_names_list.split(',')]

    for zone_name in scan_zone_names_list:
        resolved_zone_id = get_zone_id_from_name(zone_name)
        if resolved_zone_id:
            zone_ids_to_scan.add(resolved_zone_id)
    
    if not zone_ids_to_scan:
        return jsonify({"dns_records": [], "message": "No zones configured or resolved for DNS scan."})

    for z_id in zone_ids_to_scan:
        records_in_zone = get_dns_records_for_tunnel(z_id, tunnel_id)
        if records_in_zone:
            all_found_dns_records.extend(records_in_zone)
    
    all_found_dns_records.sort(key=lambda r: r.get("name", "").lower()) 
    return jsonify({"dns_records": all_found_dns_records})

@api_v2_bp.route('/ping', methods=['GET'])
def ping_api():
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time()),
        "version": current_app.config.get('APP_VERSION', 'unknown'), 
        "message": "DockFlare API is responsive."
    })

@api_v2_bp.route('/debug-info', methods=['GET']) 
def debug_info_api():
    try:
        headers = {k: v for k, v in request.headers.items()}
        env_vars = {
            "wsgi.url_scheme": request.environ.get('wsgi.url_scheme'),
            "HTTP_X_FORWARDED_PROTO": request.environ.get('HTTP_X_FORWARDED_PROTO')
        }
        return jsonify({
            "request_info": {
                "scheme": request.scheme, "is_secure": request.is_secure,
                "host": request.host, "path": request.path, "url": request.url,
                "remote_addr": request.remote_addr, "headers": headers
            },
            "environment_info": env_vars,
            "flask_config_preferred_url_scheme": current_app.config.get('PREFERRED_URL_SCHEME'),
            "timestamp": int(time.time())
        })
    except Exception as e:
        logging.error(f"Error in /api/v2/debug-info route: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An internal error occurred."}), 500

def _save_encrypted_config(config_data, fernet_cipher):
    try:
        from app.web.config_loader import config_file_path
        import json
        encrypted_payload = fernet_cipher.encrypt(json.dumps(config_data).encode('utf-8'))
        with open(config_file_path(), 'wb') as f:
            f.write(encrypted_payload)
        return True
    except Exception as e:
        logging.error(f"Failed to save encrypted config: {e}", exc_info=True)
        return False

@api_v2_bp.route('/auth/settings', methods=['GET', 'PUT'])
@login_required
def manage_auth_settings():
    from app.web.config_loader import load_encrypted_config_with_cipher
    config_data, fernet = load_encrypted_config_with_cipher()
    if config_data is None:
        return jsonify({"error": "config_not_loaded"}), 500

    if request.method == 'GET':
        auth_settings = config_data.get('auth_settings', {})
        providers = config_data.get('auth_providers', [])
        users = config_data.get('authorized_users', [])

        for p in providers:
            p.pop('client_secret', None)
            try:
                p['client_id'] = fernet.decrypt(p['client_id'].encode()).decode()
            except Exception:
                p['client_id'] = '(could not decrypt)'

        return jsonify({
            "settings": auth_settings,
            "providers": providers,
            "users": users
        })

    if request.method == 'PUT':
        data = request.get_json()

        if 'auth_settings' in data:
            config_data['auth_settings'] = data['auth_settings']
            if 'password_login_enabled' in data['auth_settings']:
                config_data['disable_password_login'] = not bool(data['auth_settings']['password_login_enabled'])

        if 'oauth_settings' in data:
            config_data['oauth_settings'] = data['oauth_settings']

        if not _save_encrypted_config(config_data, fernet):
            return jsonify({"error": "failed_to_save_config"}), 500

        from app.web import config_loader
        config_loader.apply_config_to_app(current_app, config_data)

        return jsonify({"status": "success", "message": "Settings saved. A restart may be required."})

@api_v2_bp.route('/auth/providers', methods=['GET', 'POST'])
@login_required
def manage_auth_providers():
    from app.web.config_loader import load_encrypted_config_with_cipher
    config_data, fernet = load_encrypted_config_with_cipher()
    if config_data is None:
        return jsonify({"error": "config_not_loaded"}), 500

    if request.method == 'GET':
        providers = config_data.get('auth_providers', [])
        for p in providers:
            p.pop('client_id', None)
            p.pop('client_secret', None)
        return jsonify({"providers": providers})

    if request.method == 'POST':
        data = request.get_json()
        required_fields = ['id', 'name', 'type', 'client_id', 'client_secret']

        if not all(field in data for field in required_fields):
            return jsonify({"error": "missing_required_fields"}), 400

        provider_type = data.get('type')
        if provider_type in ['oidc', 'google'] and not data.get('issuer_url'):
            return jsonify({"error": "issuer_url_required_for_oidc"}), 400

        if not config_data.get('auth_providers'):
            config_data['auth_providers'] = []

        existing_ids = [p['id'] for p in config_data['auth_providers']]
        if data['id'] in existing_ids:
            return jsonify({"error": "provider_id_exists"}), 400

        encrypted_client_id = fernet.encrypt(data['client_id'].encode()).decode()
        encrypted_client_secret = fernet.encrypt(data['client_secret'].encode()).decode()

        new_provider = {
            'id': data['id'],
            'name': data['name'],
            'type': data['type'],
            'issuer_url': data.get('issuer_url'),
            'client_id': encrypted_client_id,
            'client_secret': encrypted_client_secret,
            'enabled': data.get('enabled', True)
        }

        config_data['auth_providers'].append(new_provider)

        if not _save_encrypted_config(config_data, fernet):
            return jsonify({"error": "failed_to_save_config"}), 500

        from app.web import config_loader
        config_loader.apply_config_to_app(current_app, config_data)
        
        try:
            from app import oauth
            from app.core.oauth_manager import register_oauth_providers
            registered_count = register_oauth_providers(current_app, oauth, fernet)
            logging.info(f"OAuth providers re-registered: {registered_count} provider(s)")
        except Exception as e:
            logging.error(f"Failed to re-register OAuth providers: {e}", exc_info=True)

        return jsonify({"status": "success", "message": "Provider added successfully."})

@api_v2_bp.route('/auth/providers/<provider_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_auth_provider(provider_id):
    from app.web.config_loader import load_encrypted_config_with_cipher
    config_data, fernet = load_encrypted_config_with_cipher()
    if config_data is None:
        return jsonify({"error": "config_not_loaded"}), 500

    providers = config_data.get('auth_providers', [])
    provider_index = next((i for i, p in enumerate(providers) if p['id'] == provider_id), None)

    if provider_index is None:
        return jsonify({"error": "provider_not_found"}), 404

    if request.method == 'PUT':
        data = request.get_json()
        provider = providers[provider_index]

        if 'name' in data:
            provider['name'] = data['name']
        if 'enabled' in data:
            provider['enabled'] = data['enabled']
        if 'client_id' in data:
            provider['client_id'] = fernet.encrypt(data['client_id'].encode()).decode()
        if 'client_secret' in data:
            provider['client_secret'] = fernet.encrypt(data['client_secret'].encode()).decode()
        if 'issuer_url' in data:
            provider['issuer_url'] = data['issuer_url']

        if not _save_encrypted_config(config_data, fernet):
            return jsonify({"error": "failed_to_save_config"}), 500

        from app.web import config_loader
        config_loader.apply_config_to_app(current_app, config_data)
        
        try:
            from app import oauth
            from app.core.oauth_manager import register_oauth_providers
            registered_count = register_oauth_providers(current_app, oauth, fernet)
            logging.info(f"OAuth providers re-registered after update: {registered_count} provider(s)")
        except Exception as e:
            logging.error(f"Failed to re-register OAuth providers: {e}", exc_info=True)

        return jsonify({"status": "success", "message": "Provider updated successfully."})

    if request.method == 'DELETE':
        del providers[provider_index]

        if not _save_encrypted_config(config_data, fernet):
            return jsonify({"error": "failed_to_save_config"}), 500

        from app.web import config_loader
        config_loader.apply_config_to_app(current_app, config_data)
        
        try:
            from app import oauth
            from app.core.oauth_manager import register_oauth_providers
            registered_count = register_oauth_providers(current_app, oauth, fernet)
            logging.info(f"OAuth providers re-registered after deletion: {registered_count} provider(s)")
        except Exception as e:
            logging.error(f"Failed to re-register OAuth providers: {e}", exc_info=True)

        return jsonify({"status": "success", "message": "Provider deleted successfully."})

@api_v2_bp.route('/auth/users', methods=['GET', 'POST'])
@login_required
def manage_auth_users():
    from app.web.config_loader import load_encrypted_config_with_cipher
    from datetime import datetime
    config_data, fernet = load_encrypted_config_with_cipher()
    if config_data is None:
        return jsonify({"error": "config_not_loaded"}), 500

    if request.method == 'GET':
        users = config_data.get('authorized_users', [])
        return jsonify({"users": users})

    if request.method == 'POST':
        data = request.get_json()

        if 'email' not in data:
            return jsonify({"error": "email_required"}), 400

        if not config_data.get('authorized_users'):
            config_data['authorized_users'] = []

        existing_emails = [u['email'] for u in config_data['authorized_users']]
        if data['email'] in existing_emails:
            return jsonify({"error": "user_exists"}), 400

        new_user = {
            'email': data['email'],
            'name': data.get('name', ''),
            'added_date': datetime.utcnow().isoformat()
        }

        config_data['authorized_users'].append(new_user)

        if not _save_encrypted_config(config_data, fernet):
            return jsonify({"error": "failed_to_save_config"}), 500

        current_app.config['OAUTH_AUTHORIZED_USERS'] = [
            user['email'] for user in config_data.get('authorized_users', [])
        ]

        return jsonify({"status": "success", "message": "User added successfully."})

@api_v2_bp.route('/auth/users/<user_email>', methods=['DELETE'])
@login_required
def manage_auth_user(user_email):
    from app.web.config_loader import load_encrypted_config_with_cipher
    config_data, fernet = load_encrypted_config_with_cipher()
    if config_data is None:
        return jsonify({"error": "config_not_loaded"}), 500

    users = config_data.get('authorized_users', [])
    user_index = next((i for i, u in enumerate(users) if u['email'] == user_email), None)

    if user_index is None:
        return jsonify({"error": "user_not_found"}), 404

    del users[user_index]

    if not _save_encrypted_config(config_data, fernet):
        return jsonify({"error": "failed_to_save_config"}), 500

    current_app.config['OAUTH_AUTHORIZED_USERS'] = [
        user['email'] for user in config_data.get('authorized_users', [])
    ]

    return jsonify({"status": "success", "message": "User deleted successfully."})

@api_v2_bp.route('/idp/types', methods=['GET'])
@login_required
def api_get_idp_types():
    from app.core import idp_manager
    try:
        types = idp_manager.get_supported_idp_types()
        return jsonify({"success": True, "types": types})
    except Exception as e:
        logging.error(f"Error getting IdP types: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@api_v2_bp.route('/idp/list', methods=['GET'])
@login_required
def api_list_idps():
    try:
        local_idps = list_identity_providers()
        return jsonify({"success": True, "identity_providers": local_idps})
    except Exception as e:
        logging.error(f"Error listing IdPs: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@api_v2_bp.route('/idp/sync', methods=['POST'])
@login_required
def api_sync_idps():
    from app.core import idp_manager
    from datetime import datetime, timezone

    try:
        cloudflare_idps = idp_manager.list_identity_providers()
        synced_count = 0

        for cf_idp in cloudflare_idps:
            cf_id = cf_idp.get('id')
            idp_type = cf_idp.get('type')
            idp_name = cf_idp.get('name', '').strip()

            if not idp_name:
                idp_name = idp_type.title()

            friendly_name, existing_idp = get_idp_by_cloudflare_id(cf_id)

            if not friendly_name:
                friendly_name = idp_name.lower().replace(' ', '-')
                counter = 1
                base_name = friendly_name
                while get_identity_provider(friendly_name):
                    friendly_name = f"{base_name}-{counter}"
                    counter += 1

            idp_data = {
                "cloudflare_id": cf_id,
                "name": idp_name,
                "type": idp_type,
                "last_synced": datetime.now(timezone.utc).isoformat(),
                "system_managed": idp_manager.is_system_managed_idp(idp_type)
            }

            config = cf_idp.get('config', {})
            if 'client_id' in config:
                idp_data['client_id_preview'] = config['client_id'][:20] + '...' if len(config['client_id']) > 20 else config['client_id']

            save_identity_provider(friendly_name, idp_data)
            synced_count += 1

        logging.info(f"Synced {synced_count} Identity Providers from Cloudflare")
        return jsonify({"success": True, "synced": synced_count})
    except Exception as e:
        logging.error(f"Error syncing IdPs: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@api_v2_bp.route('/idp/create', methods=['POST'])
@login_required
def api_create_idp():
    from app.core import idp_manager
    from datetime import datetime, timezone

    try:
        data = request.get_json()
        friendly_name = data.get('friendly_name', '').strip()
        name = data.get('name', '').strip()
        idp_type = data.get('type', '').strip()
        config = data.get('config', {})

        if not friendly_name or not name or not idp_type:
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        if get_identity_provider(friendly_name):
            return jsonify({"success": False, "error": "Friendly name already exists"}), 400

        cf_idp = idp_manager.create_identity_provider(name, idp_type, config)

        if not cf_idp or not cf_idp.get('id'):
            return jsonify({"success": False, "error": "Failed to create IdP in Cloudflare"}), 500

        idp_data = {
            "cloudflare_id": cf_idp['id'],
            "name": name,
            "type": idp_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_synced": datetime.now(timezone.utc).isoformat(),
            "system_managed": False
        }

        if 'client_id' in config:
            idp_data['client_id_preview'] = config['client_id'][:20] + '...' if len(config['client_id']) > 20 else config['client_id']

        save_identity_provider(friendly_name, idp_data)

        test_url = idp_manager.build_test_idp_url(cf_idp['id'])

        return jsonify({
            "success": True,
            "identity_provider": idp_data,
            "friendly_name": friendly_name,
            "test_url": test_url
        })
    except Exception as e:
        logging.error(f"Error creating IdP: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@api_v2_bp.route('/idp/<friendly_name>', methods=['GET'])
@login_required
def api_get_idp(friendly_name):
    from app.core import idp_manager

    try:
        local_idp = get_identity_provider(friendly_name)
        if not local_idp:
            return jsonify({"success": False, "error": "IdP not found"}), 404

        cf_id = local_idp.get('cloudflare_id')
        test_url = idp_manager.build_test_idp_url(cf_id) if cf_id else None

        return jsonify({
            "success": True,
            "identity_provider": local_idp,
            "friendly_name": friendly_name,
            "test_url": test_url
        })
    except Exception as e:
        logging.error(f"Error getting IdP: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@api_v2_bp.route('/idp/<friendly_name>', methods=['PUT'])
@login_required
def api_update_idp(friendly_name):
    from app.core import idp_manager
    from datetime import datetime, timezone

    try:
        local_idp = get_identity_provider(friendly_name)
        if not local_idp:
            return jsonify({"success": False, "error": "IdP not found"}), 404

        if local_idp.get('system_managed'):
            return jsonify({"success": False, "error": "Cannot update system-managed IdP"}), 403

        data = request.get_json()
        cf_id = local_idp.get('cloudflare_id')
        name = data.get('name')
        config = data.get('config')

        if not name and not config:
            return jsonify({"success": False, "error": "Nothing to update"}), 400

        cf_idp = idp_manager.update_identity_provider(cf_id, name=name, config=config)

        if not cf_idp:
            return jsonify({"success": False, "error": "Failed to update IdP in Cloudflare"}), 500

        if name:
            local_idp['name'] = name
        if config and 'client_id' in config:
            local_idp['client_id_preview'] = config['client_id'][:20] + '...' if len(config['client_id']) > 20 else config['client_id']

        local_idp['last_synced'] = datetime.now(timezone.utc).isoformat()
        save_identity_provider(friendly_name, local_idp)

        return jsonify({"success": True, "identity_provider": local_idp})
    except Exception as e:
        logging.error(f"Error updating IdP: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@api_v2_bp.route('/idp/<friendly_name>', methods=['DELETE'])
@login_required
def api_delete_idp(friendly_name):
    from app.core import idp_manager

    try:
        local_idp = get_identity_provider(friendly_name)
        if not local_idp:
            return jsonify({"success": False, "error": "IdP not found"}), 404

        if local_idp.get('system_managed'):
            return jsonify({"success": False, "error": "Cannot delete system-managed IdP"}), 403

        cf_id = local_idp.get('cloudflare_id')

        try:
            idp_manager.delete_identity_provider(cf_id)
        except Exception as e:
            logging.warning(f"Failed to delete IdP from Cloudflare (may already be deleted): {e}")

        delete_identity_provider(friendly_name)

        return jsonify({"success": True})
    except Exception as e:
        logging.error(f"Error deleting IdP: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
