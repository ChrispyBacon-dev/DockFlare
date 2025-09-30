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
    managed_rules, state_lock, save_state,
    add_agent, get_agent, update_agent, list_agents, remove_agent, add_agent_key, revoke_agent_key, find_agent_id_by_key, list_agent_keys, get_agent_key_info,
    get_services_snapshot, cleanup_expired_revoked_keys, get_revoked_keys_summary
)
from app.core import agent_key_store
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
    get_zone_details_by_id,
    delete_tunnel_via_api,
    cf_api_request,
    list_account_zones
)
from app.core.access_manager import (
    check_for_tld_access_policy,
    get_cloudflare_account_email,
    delete_cloudflare_access_application,
    create_cloudflare_access_application,
    update_cloudflare_access_application,
    generate_access_app_config_hash,
    find_cloudflare_access_application_by_hostname,
    handle_access_policy_from_labels
)
from app.core.reconciler import reconcile_state_threaded
from app.core.docker_handler import is_valid_hostname, is_valid_service
from app.core.utils import get_rule_key, get_label

api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

_AGENT_ENDPOINT_ALLOWLIST = {
    'api_v2.agents_register',
    'api_v2.agents_get_commands',
    'api_v2.agents_post_events',
}

_UI_ENDPOINT_ALLOWLIST = {
    'api_v2.manage_auth_settings',
    'api_v2.manage_auth_providers',
    'api_v2.manage_auth_provider',
    'api_v2.manage_auth_users',
    'api_v2.manage_auth_user',
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

    # For UI endpoints, rely on Flask-Login's session auth
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

def _ensure_agent_api_key(agent_id, agent_record, token):
    key_info = get_agent_key_info(token)
    if not key_info:
        logging.warning("AGENT_AUTH: Token missing from key registry during agent verification.")
        return False

    status = key_info.get("status", "active")
    if status != "active":
        logging.warning(f"AGENT_AUTH: Token for agent {agent_id} is not active (status={status}).")
        return False

    stored_token = agent_record.get("api_key")
    if stored_token is None:
        updated = update_agent(agent_id, {"api_key": token})
        if not updated:
            logging.error(f"AGENT_AUTH: Failed to persist API key binding for agent {agent_id}.")
            return False
    elif stored_token != token:
        logging.warning(f"AGENT_AUTH: Token mismatch for agent {agent_id}.")
        return False

    meta_update = dict(key_info)
    now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    meta_update["last_used_at"] = now_iso
    if meta_update.get("bound_agent_id") != agent_id:
        meta_update["bound_agent_id"] = agent_id
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
    rules_for_api = {}
    api_tunnel_state = {}
    api_agent_state = {}
    initialization_status_api = {}
    tld_policy_exists_val_api = False
    account_email_for_tld_api = None
    relevant_zone_name_for_tld_policy_api = None

    all_account_tunnels_list_api = get_all_account_cloudflare_tunnels()
    tunnel_names_map = {}
    tunnel_status_map = {}
    try:
        for t in all_account_tunnels_list_api or []:
            tid = t.get("id")
            if tid:
                tunnel_status_map[tid] = {
                    "status": t.get("status") or "unknown",
                    "name": t.get("name")
                }
                if t.get("name"):
                    tunnel_names_map[tid] = t.get("name")
    except Exception as _e:
        logging.error(f"Error while building tunnel_status_map: {_e}", exc_info=True)

    zone_lookup_map = {}
    try:
        for zone in list_account_zones() or []:
            zid = zone.get("id")
            zname = zone.get("name")
            if zid and zname:
                zone_lookup_map[zid] = zname
    except Exception as zone_list_error:
        logging.debug(f"Could not build zone lookup map: {zone_list_error}")

    with state_lock:
        state_changed_during_serialization = False
        for hostname_key, rule_value in managed_rules.items():
            serialized_rule = serialize_rule(rule_value)
            tunnel_id_value = serialized_rule.get("tunnel_id")
            if not tunnel_id_value and rule_value.get("source") == "manual":
                fallback_tunnel_id = get_effective_tunnel_id()
                if fallback_tunnel_id:
                    tunnel_id_value = fallback_tunnel_id
                    serialized_rule["tunnel_id"] = fallback_tunnel_id
                    rule_value["tunnel_id"] = fallback_tunnel_id
                    state_changed_during_serialization = True
            if tunnel_id_value and (not serialized_rule.get("tunnel_name") or serialized_rule.get("tunnel_name") in (None, "", "N/A")):
                tunnel_name_lookup = tunnel_names_map.get(tunnel_id_value)
                if tunnel_name_lookup:
                    serialized_rule["tunnel_name"] = tunnel_name_lookup
                elif tunnel_id_value == (tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID):
                    fallback_name = tunnel_state.get("name")
                    if fallback_name:
                        serialized_rule["tunnel_name"] = fallback_name
                if serialized_rule.get("tunnel_name") and rule_value.get("tunnel_name") != serialized_rule.get("tunnel_name"):
                    rule_value["tunnel_name"] = serialized_rule["tunnel_name"]
                    state_changed_during_serialization = True
            zone_id_value = serialized_rule.get("zone_id")
            if zone_id_value and not serialized_rule.get("zone_name"):
                zone_name_lookup = zone_lookup_map.get(zone_id_value)
                if zone_name_lookup:
                    serialized_rule["zone_name"] = zone_name_lookup
                    if rule_value.get("zone_name") != zone_name_lookup:
                        rule_value["zone_name"] = zone_name_lookup
                        state_changed_during_serialization = True
            rules_for_api[hostname_key] = serialized_rule
        
        api_tunnel_state = tunnel_state.copy()
        api_agent_state = cloudflared_agent_state.copy()

        initialization_status_api = {
            "complete": api_tunnel_state.get("id") is not None or config.EXTERNAL_TUNNEL_ID,
            "in_progress": not (api_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID) and \
                            api_tunnel_state.get("status_message", "").lower().startswith("init")
        }

        cf_zone_id = current_app.config.get('CF_ZONE_ID')
        if cf_zone_id and docker_client:
            zone_details = get_zone_details_by_id(cf_zone_id)
            if zone_details and zone_details.get("name"):
                relevant_zone_name_for_tld_policy_api = zone_details.get("name")
            
            if relevant_zone_name_for_tld_policy_api:
                tld_policy_exists_val_api = check_for_tld_access_policy(relevant_zone_name_for_tld_policy_api)
                if not tld_policy_exists_val_api:
                    account_email_for_tld_api = get_cloudflare_account_email()
        if state_changed_during_serialization:
            save_state()

    agents_list_api = list_agents()
    agent_keys_list_api = list_agent_keys()

    try:
        now_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
        heartbeat_timeout = getattr(config, "AGENT_HEARTBEAT_TIMEOUT", 60)
        processed_agents = {}
        for a_id, a in agents_list_api.items():
            processed = dict(a) if isinstance(a, dict) else {"id": a_id}
            last_seen_str = processed.get("last_seen")
            online = False
            try:
                if last_seen_str:
                    
                    if last_seen_str.endswith('Z'):
                        last_seen_dt = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                    else:
                        last_seen_dt = datetime.fromisoformat(last_seen_str)
                    last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc) if last_seen_dt.tzinfo is None else last_seen_dt.astimezone(timezone.utc)
                    delta_secs = (now_dt - last_seen_dt).total_seconds()
                    online = delta_secs <= heartbeat_timeout
                else:
                    online = False
            except Exception:
                online = False

            processed["online"] = online
            processed["health"] = "connected" if online else "disconnected"
            
            try:
                assigned_tid = processed.get("assigned_tunnel_id")
                if assigned_tid:
                    ts = tunnel_status_map.get(assigned_tid)
                    if not ts:
                        try:
                            account_id = current_app.config.get('CF_ACCOUNT_ID')
                            if account_id:
                                detail = cf_api_request("GET", f"/accounts/{account_id}/cfd_tunnel/{assigned_tid}")
                                if detail and detail.get("result"):
                                    res = detail["result"]
                                    ts = {
                                        "status": res.get("status") or "unknown",
                                        "name": res.get("name")
                                    }
                                    tunnel_status_map[assigned_tid] = ts
                        except Exception as _fetch_e:
                            logging.debug(f"Could not fetch tunnel detail for {assigned_tid}: {_fetch_e}")
                    if ts:
                        existing_ts = processed.get("tunnel_status") or {}
                        if existing_ts.get("version") and "version" not in ts:
                            ts = dict(ts)
                            ts["version"] = existing_ts.get("version")
                        processed["tunnel_status"] = ts
            except Exception as _te:
                logging.debug(f"Unable to enrich agent {a_id} with tunnel_status: {_te}")
            processed_agents[a_id] = processed
        agents_list_api = processed_agents
    except Exception as e:
        logging.error(f"Error while computing agent health fields: {e}", exc_info=True)

    log_stream_url = "/stream-logs"
    try:
        log_stream_url = url_for('web.stream_logs_route', _external=False)
    except RuntimeError as e:
        logging.error(f"RuntimeError generating url_for for 'web.stream_logs_route': {e}. Falling back to static path.")

    cf_account_id = current_app.config.get('CF_ACCOUNT_ID')
    return jsonify({
        "tunnel_state": api_tunnel_state,
        "agent_state": api_agent_state,
        "initialization": initialization_status_api,
        "display_token": tunnel_state.get("token"), 
        "cloudflared_container_name": current_app.config.get('CLOUDFLARED_CONTAINER_NAME'),
        "docker_available": docker_client is not None,
        "external_cloudflared": config.USE_EXTERNAL_CLOUDFLARED,
        "external_tunnel_id": config.EXTERNAL_TUNNEL_ID,
        "rules": rules_for_api,
        "all_account_tunnels": all_account_tunnels_list_api,
        "config_status": {
            "cf_account_id_configured": bool(cf_account_id),
            "account_id_for_display": cf_account_id if cf_account_id else "Not Configured",
            "cf_zone_id_configured": bool(cf_zone_id),
            "relevant_zone_name_for_tld_policy": relevant_zone_name_for_tld_policy_api,
            "tld_policy_exists": tld_policy_exists_val_api,
            "account_email_for_tld": account_email_for_tld_api,
        },
        "reconciliation_info": getattr(current_app, 'reconciliation_info', {
            "in_progress": False, "progress": 0, "total_items": 0,
            "processed_items": 0, "status": "Not started"
        }),
        "agents": agents_list_api,
        "agent_keys": agent_keys_list_api,
        "log_stream_path": log_stream_url
    })

@api_v2_bp.route('/zones', methods=['GET'])
def list_zones_api():
    force_refresh = request.args.get('refresh') == '1'
    zones = list_account_zones(force_refresh=force_refresh)
    return jsonify(zones)

def _auto_detect_zone_match(hostname, zones):
    if not hostname or not zones:
        return None, []
    normalized = hostname.lower()
    if normalized.startswith('*.'):
        normalized = normalized[2:]
    matches = []
    for zone in zones:
        name = (zone.get("name") or "").lower()
        if not name:
            continue
        if normalized == name or normalized.endswith('.' + name):
            matches.append(zone)
    if not matches:
        return None, []
    longest = max(len(zone.get("name") or "") for zone in matches)
    top_matches = [zone for zone in matches if len(zone.get("name") or "") == longest]
    if len(top_matches) == 1:
        return top_matches[0], []
    return None, top_matches

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
    zones = list_account_zones()
    selected_zone = None
    ambiguous_zones = []
    if zone_id_override:
        zone_candidate = next((z for z in zones if z.get('id') == zone_id_override), None)
        if not zone_candidate:
            return jsonify({"error": "zone_not_found", "candidates": zones}), 409
        selected_zone = zone_candidate
    else:
        selected_zone, ambiguous_zones = _auto_detect_zone_match(hostname, zones)
        if not selected_zone:
            if ambiguous_zones:
                return jsonify({"error": "zone_ambiguous", "candidates": ambiguous_zones}), 409
            return jsonify({"error": "zone_not_found", "candidates": zones}), 409
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
        access_groups = [access_groups_input.strip()] if access_groups_input.strip() else []
    elif isinstance(access_groups_input, list):
        access_groups = [str(item).strip() for item in access_groups_input if str(item).strip()]
    else:
        access_groups = []
    state_changed = False
    previous_tunnel_id = None
    master_tunnel_id = get_effective_tunnel_id()
    with state_lock:
        existing = managed_rules.get(rule_key)
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
                "tunnel_id": tunnel_id,
                "tunnel_name": tunnel_name,
                "access_group_id": access_groups or None
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
                "no_tls_verify": False,
                "origin_server_name": None,
                "http_host_header": None,
                "access_app_id": None,
                "access_policy_type": None,
                "access_app_config_hash": None,
                "access_policy_ui_override": False,
                "rule_ui_override": False,
                "source": "manual",
                "access_group_id": access_groups or None,
                "tunnel_id": tunnel_id,
                "tunnel_name": tunnel_name
            }
            save_state()
            state_changed = True
    if state_changed:
        publish_state_event('snapshot_refresh')
    try:
        create_cloudflare_dns_record(zone_id, hostname, tunnel_id)
    except Exception as dns_error:
        logging.error(f"Failed to ensure DNS for manual rule {rule_key}: {dns_error}")

    update_needed = state_changed or (previous_tunnel_id and previous_tunnel_id != tunnel_id)
    if update_needed:
        update_cloudflare_config(tunnel_id)
    if previous_tunnel_id and previous_tunnel_id != tunnel_id:
        update_cloudflare_config(previous_tunnel_id)
    if state_changed and previous_tunnel_id is None and master_tunnel_id and master_tunnel_id != tunnel_id:
        update_cloudflare_config(master_tunnel_id)
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

def process_agent_container_start(payload, agent_id):
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
            logging.info(f"AGENT_PROCESS_START: Payload: {payload}")
            logging.info(f"AGENT_PROCESS_START: Labels: {labels}")

            is_enabled = get_label(labels, "enable", "false").lower() in ["true", "1", "t", "yes"]
            if not is_enabled:
                logging.debug(f"AGENT_PROCESS: Ignoring: {container_name} ({container_id[:12]}): 'enable' label not true.")
                return
            
            hostnames_to_process = []

            default_path_label = get_label(labels, "path")
            default_originsrvname_label = get_label(labels, "originsrvname")
            default_http_host_header_label = get_label(labels, "httpHostHeader")

            default_access_groups = get_label(labels, "access.groups")
            default_access_group = get_label(labels, "access.group") if not default_access_groups else None
            if default_access_groups:
                default_access_group = [gid.strip() for gid in default_access_groups.split(',')]
            elif default_access_group:
                default_access_group = [default_access_group.strip()]

            default_access_policy_type_label = get_label(labels, "access.policy")
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

                access_groups_indexed = get_label(labels, f"{index}.access.groups")
                access_group_indexed = get_label(labels, f"{index}.access.group") if not access_groups_indexed else None
                if access_groups_indexed:
                    access_group_indexed = [gid.strip() for gid in access_groups_indexed.split(',')]
                elif access_group_indexed:
                    access_group_indexed = [access_group_indexed.strip()]
                else:
                    access_group_indexed = default_access_group

                access_policy_type_indexed = get_label(labels, f"{index}.access.policy", default_access_policy_type_label)
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
                return

            logging.info(f"AGENT_PROCESS: Found {len(hostnames_to_process)} hostname configurations for container {container_name}")

            state_changed_locally = False
            needs_tunnel_config_update = False

            agent_record = get_agent(agent_id)
            assigned_tunnel_name = agent_record.get("assigned_tunnel_name") if agent_record else "Unknown"
            assigned_tunnel_id = agent_record.get("assigned_tunnel_id") if agent_record else None

            logging.info(f"AGENT_PROCESS: Processing {len(hostnames_to_process)} hostname configs for agent {agent_id}")

            for config_item in hostnames_to_process:
                hostname = config_item["hostname"]
                service = config_item["service"]
                path_from_item = config_item.get("path")
                rule_key = get_rule_key(hostname, path_from_item)

                zone_name_from_item = config_item["zone_name"]
                no_tls_verify_from_item = config_item["no_tls_verify"]
                origin_server_name_from_item = config_item.get("origin_server_name")

                target_zone_id = None
                if zone_name_from_item:
                    target_zone_id = get_zone_id_from_name(zone_name_from_item)
                    if not target_zone_id:
                        logging.error(f"AGENT_PROCESS: Failed Zone ID lookup for '{zone_name_from_item}' (rule {rule_key}). Skipping.")
                        continue
                elif current_app.config.get('CF_ZONE_ID'):
                    target_zone_id = current_app.config.get('CF_ZONE_ID')
                else:
                    logging.error(f"AGENT_PROCESS: No Zone ID for rule {rule_key}. Skipping.")
                    continue

                with state_lock:
                    existing_rule = managed_rules.get(rule_key)

                    if existing_rule and existing_rule.get("source") == "manual":
                        logging.info(f"AGENT_PROCESS: Rule {rule_key} is manual, skipping.")
                        continue

                    if existing_rule:
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
                        if existing_rule.get("tunnel_name") != assigned_tunnel_name:
                            existing_rule["tunnel_name"] = assigned_tunnel_name
                            rule_data_changed = True
                        if existing_rule.get("tunnel_id") != assigned_tunnel_id:
                            existing_rule["tunnel_id"] = assigned_tunnel_id
                            rule_data_changed = True
                        if existing_rule.get("zone_name") != zone_name_from_item:
                            existing_rule["zone_name"] = zone_name_from_item
                            rule_data_changed = True

                        existing_rule["source"] = "agent"
                        existing_rule["agent_id"] = agent_id

                        if existing_rule.get("status") == "pending_deletion":
                            existing_rule["status"] = "active"
                            existing_rule["delete_at"] = None
                            rule_data_changed = True

                        if rule_data_changed:
                            needs_tunnel_config_update = True
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
                            "no_tls_verify": no_tls_verify_from_item,
                            "origin_server_name": origin_server_name_from_item,
                            "http_host_header": config_item.get("http_host_header"),
                            "access_app_id": None,
                            "access_policy_type": None,
                            "access_app_config_hash": None,
                            "access_policy_ui_override": False,
                            "rule_ui_override": False,
                            "source": "agent",
                            "access_group_id": None,
                            "agent_id": agent_id,
                            "tunnel_name": assigned_tunnel_name,
                            "tunnel_id": assigned_tunnel_id
                        }
                        state_changed_locally = True
                        needs_tunnel_config_update = True

                    if existing_rule:
                        if existing_rule.get("access_policy_ui_override", False):
                            logging.info(f"AGENT_PROCESS: Access policy for {rule_key} is UI-managed. Skipping.")
                        else:
                            if handle_access_policy_from_labels(config_item, existing_rule, save_state):
                                state_changed_locally = True

            if state_changed_locally:
                save_state()
                publish_state_event('snapshot_refresh')
    
            if needs_tunnel_config_update:
                logging.info(f"AGENT_PROCESS: DNS and tunnel config update needed for agent {agent_id}.")
                
                agent_record = get_agent(agent_id)
                if agent_record and agent_record.get("assigned_tunnel_id"):
                    agent_tunnel_id = agent_record.get("assigned_tunnel_id")
                                        
                    for config_item in hostnames_to_process:
                        hostname = config_item["hostname"]
                        zone_name_dns_item = config_item.get("zone_name")
                        target_zone_id_for_dns = get_zone_id_from_name(zone_name_dns_item) if zone_name_dns_item else current_app.config.get('CF_ZONE_ID')
                        if target_zone_id_for_dns:
                            create_cloudflare_dns_record(target_zone_id_for_dns, hostname, agent_tunnel_id)
                        else:
                            logging.error(f"AGENT_PROCESS: Could not determine Zone ID for DNS record {hostname}")
    
                    from app.core.state_manager import get_agent_rules
                    agent_rules = get_agent_rules(agent_id)
                    
                    ingress_rules = []
                    for rule_key, rule in agent_rules.items():
                        if rule.get("status") == "active":
                            entry = {"hostname": rule["hostname"], "service": rule["service"]}
                            if rule.get("path"):
                                entry["path"] = rule["path"]
                            ingress_rules.append(entry)
                    ingress_rules.append({"service": "http_status:404"})
                    account_id = current_app.config.get('CF_ACCOUNT_ID')
                    endpoint = f"/accounts/{account_id}/cfd_tunnel/{agent_tunnel_id}/configurations"
                    config_payload = {"config": {"ingress": ingress_rules}}

                    try:
                        cf_api_request("PUT", endpoint, json_data=config_payload)
                        logging.info(f"AGENT_PROCESS: Successfully updated tunnel config for agent {agent_id}")
                    except Exception as e:
                        logging.error(f"AGENT_PROCESS: Failed to update tunnel config for agent {agent_id}: {e}")
                else:
                    logging.error(f"AGENT_PROCESS: Agent {agent_id} not found or has no tunnel ID. Cannot send update command.")
    except Exception as e:
        logging.error(f"AGENT_PROCESS_START: Exception in process_agent_container_start: {e}", exc_info=True)
        raise

def process_agent_container_stop(payload, agent_id):
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
                        rule["delete_at"] = datetime.now(timezone.utc) + grace_delta
                        logging.info(f"AGENT_PROCESS_STOP: Rule for {rule_key} scheduled for deletion (grace period: {grace_period}s)")
                save_state()
                publish_state_event('snapshot_refresh')
                logging.info(f"AGENT_PROCESS_STOP: Scheduled {len(rule_keys_affected)} rules for deletion from agent {agent_id}")
            else:
                logging.info(f"AGENT_PROCESS_STOP: No active agent-managed rules found for container {container_id[:12]} from agent {agent_id}")

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
    key = data.get('key')
    if not key:
        return jsonify({"status": "error", "message": "Missing 'key' in payload."}), 400
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

    # Get key info to validate it exists and is revoked
    key_info = get_agent_key_info(key_id)
    if not key_info:
        return jsonify({"status": "error", "message": "Key not found"}), 404

    # Security: Only allow deletion of revoked keys
    if key_info.get("status") != "revoked":
        return jsonify({"status": "error", "message": "Can only permanently delete revoked keys"}), 400

    # Audit logging before deletion
    owner = key_info.get("owner", "unknown")
    revoked_at = key_info.get("revoked_at", "unknown")
    logging.info(f"ADMIN: Permanently deleting revoked key {key_id[:8]}... (owner: {owner}, revoked: {revoked_at})")

    # Perform the permanent deletion
    agent_key_store.remove_key(key_id)

    return jsonify({
        "status": "success",
        "message": "Key permanently deleted",
        "deleted_key": key_id[:8] + "...",
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

@api_v2_bp.route('/agents', methods=['GET'])
def agents_list_api():
    """
    Admin endpoint to list known agents and keys.
    """
    agents_map = list_agents()
    keys_map = list_agent_keys()

    try:
        now_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
        heartbeat_timeout = getattr(config, "AGENT_HEARTBEAT_TIMEOUT", 60)
        processed_agents = {}
        for a_id, a in agents_map.items():
            processed = dict(a) if isinstance(a, dict) else {"id": a_id}
            last_seen_str = processed.get("last_seen")
            online = False
            try:
                if last_seen_str:
                    
                    if last_seen_str.endswith('Z'):
                        last_seen_dt = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                    else:
                        last_seen_dt = datetime.fromisoformat(last_seen_str)
                    last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc) if last_seen_dt.tzinfo is None else last_seen_dt.astimezone(timezone.utc)
                    delta_secs = (now_dt - last_seen_dt).total_seconds()
                    online = delta_secs <= heartbeat_timeout
                else:
                    online = False
            except Exception:
                online = False

            processed["online"] = online
            processed["health"] = "connected" if online else "disconnected"
            processed.pop("api_key", None)
            processed_agents[a_id] = processed
        agents_map = processed_agents
    except Exception as e:
        logging.error(f"Error while computing agent health fields in agents_list_api: {e}", exc_info=True)

    return jsonify({"agents": agents_map, "agent_keys": keys_map}), 200

@api_v2_bp.route('/agents/register', methods=['POST'])
def agents_register():
    """
    Agent registration endpoint.
    Agent authenticates with Authorization: Bearer <API_KEY>
    Body may include optional 'agent_id', 'display_name', 'version'.
    Returns agent_id and enrollment status.
    """
    token, owner = _authenticate_agent_request()
    if not token:
        return jsonify({"status": "error", "message": "Missing or invalid Authorization header."}), 401

    data = request.get_json() or {}
    provided_agent_id = data.get('agent_id')
    agent_id = provided_agent_id or str(uuid.uuid4())
    display_name = data.get('display_name') or data.get('hostname') or f"agent-{agent_id[:8]}"
    version = data.get('version')
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    
    existing_agent_id = provided_agent_id or agent_id
    existing_agent = get_agent(existing_agent_id)

    if existing_agent:
        if not _ensure_agent_api_key(existing_agent_id, existing_agent, token):
            return jsonify({"status": "error", "message": "API key mismatch for agent."}), 403

        logging.info(f"Agent re-registration: Found existing agent '{existing_agent_id}'. Updating last_seen and version.")
        update_payload = {
            "last_seen": now,
            "version": version,
        }

        if not existing_agent.get("custom_name"):
            update_payload["display_name"] = display_name
        update_agent(existing_agent_id, update_payload)
        agent_record = get_agent(existing_agent_id)
        agent_id = existing_agent_id
        http_status_code = 200 # OK
    else:
        logging.info(f"New agent registration: Creating record for agent '{agent_id}'.")
        agent_record = {
            "id": agent_id,
            "display_name": display_name,
            "version": version,
            "last_seen": now,
            "status": "pending" if config.AGENT_ENROLLMENT_REQUIRED else "enrolled",
            "assigned_tunnel_name": None,
            "assigned_tunnel_id": None,
            "assigned_tunnel_token": None,
            "commands": [],
            "meta": {"registered_with_key_owner": owner},
            "api_key": token
        }
        add_agent(agent_id, agent_record)
        key_meta = get_agent_key_info(token) or {}
        meta_update = dict(key_meta)
        meta_update["bound_agent_id"] = agent_id
        if owner and not meta_update.get("owner"):
            meta_update["owner"] = owner
        if not meta_update.get("created_at"):
            meta_update["created_at"] = now
        meta_update["status"] = "active"
        meta_update["last_used_at"] = now
        add_agent_key(token, meta_update)
        http_status_code = 201 # Created

    return jsonify({"status": "success", "agent_id": agent_id, "agent": agent_record}), http_status_code

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

    commands = agent.get("commands", [])
    # clear commands after delivery
    update_agent(agent_id, {"commands": [] , "last_seen": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()})
    return jsonify({"status": "success", "commands": commands}), 200

@api_v2_bp.route('/agents/<agent_id>/events', methods=['POST'])
def agents_post_events(agent_id):
    """
    Agents POST events (container start/stop, tunnel status).
    Auth via API key.
    """
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

    # Process the event
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

    try:
        from app.core.cloudflare_api import find_tunnel_via_api, create_tunnel_via_api
        found_id, found_token = find_tunnel_via_api(tunnel_name)
        if not found_id:
            created_id, created_token = create_tunnel_via_api(tunnel_name)
            tunnel_id = created_id
            token = created_token
        else:
            tunnel_id = found_id
            token = found_token

        if not tunnel_id:
            return jsonify({"status": "error", "message": "Failed to create/find tunnel."}), 500

        cmd = {"action": "start_tunnel", "tunnel_name": tunnel_name, "tunnel_id": tunnel_id, "token": token}
        existing_cmds = agent.get("commands", [])
        existing_cmds.append(cmd)
        update_agent(agent_id, {
            "assigned_tunnel_name": tunnel_name,
            "assigned_tunnel_id": tunnel_id,
            "assigned_tunnel_token": token,
            "status": "enrolled",
            "commands": existing_cmds,
            "last_enrolled_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
        })

        with state_lock:
            rules_updated = False
            for rule in managed_rules.values():
                if rule.get("source") == "agent" and rule.get("agent_id") == agent_id:
                    if rule.get("tunnel_name") != tunnel_name:
                        rule["tunnel_name"] = tunnel_name
                        rules_updated = True
            if rules_updated:
                logging.info(f"Updated {len([r for r in managed_rules.values() if r.get('agent_id') == agent_id])} rules for agent {agent_id} with tunnel name '{tunnel_name}'.")
                save_state()

        return jsonify({"status": "success", "message": "Agent enrolled and command queued.", "command": cmd}), 200
    except Exception as e:
        logging.error(f"Error enrolling agent {agent_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Exception during enrollment: {e}"}), 500

@api_v2_bp.route('/agents/<agent_id>/remove', methods=['POST'])
def agents_remove(agent_id):
    """
    Admin endpoint to remove an agent and clean up associated resources.
    This will:
    - Delete the Cloudflare tunnel
    - Remove DNS records associated with the tunnel
    - Remove rules created by this agent
    - Remove the agent from state
    """
    agent = get_agent(agent_id)
    if not agent:
        return jsonify({"status": "error", "message": "Agent not found."}), 404

    tunnel_id = agent.get("assigned_tunnel_id")
    tunnel_name = agent.get("assigned_tunnel_name")

    cleanup_results = {"tunnel_deleted": False, "dns_records_deleted": 0, "rules_removed": 0}

    if tunnel_id:
        try:

            try:
                all_tunnels = get_all_account_cloudflare_tunnels()
                tunnel_exists = any(t.get("id") == tunnel_id for t in all_tunnels)
            except Exception as check_err:
                logging.warning(f"Failed to check if tunnel {tunnel_id} exists on Cloudflare: {check_err}. Assuming it exists and trying to delete.")
                tunnel_exists = True

            if tunnel_exists:
                try:
                    success = delete_tunnel_via_api(tunnel_id)
                    cleanup_results["tunnel_deleted"] = success
                    if success:
                        logging.info(f"Successfully deleted tunnel {tunnel_id} for agent {agent_id}")
                    else:
                        logging.error(f"Failed to delete tunnel {tunnel_id} for agent {agent_id}")
                except Exception as delete_err:
                    logging.error(f"Exception while deleting tunnel {tunnel_id}: {delete_err}")
                    cleanup_results["tunnel_deleted"] = False
            else:
                logging.info(f"Tunnel {tunnel_id} for agent {agent_id} no longer exists on Cloudflare (already deleted)")
                cleanup_results["tunnel_deleted"] = True  # Consider it successful since it's already gone
        except Exception as e:
            logging.error(f"Exception while processing tunnel deletion for {tunnel_id}: {e}")
            cleanup_results["tunnel_deleted"] = False

    if tunnel_id:
        try:
            
            cf_zone_id = current_app.config.get('CF_ZONE_ID')
            scan_zone_names = current_app.config.get('TUNNEL_DNS_SCAN_ZONE_NAMES', [])
            zone_ids_to_scan = set()
            if cf_zone_id:
                zone_ids_to_scan.add(cf_zone_id)
            for zone_name in scan_zone_names:
                try:
                    zone_id = get_zone_id_from_name(zone_name)
                    if zone_id:
                        zone_ids_to_scan.add(zone_id)
                except Exception as zone_err:
                    logging.warning(f"Failed to get zone ID for {zone_name}: {zone_err}")

            for zone_id in zone_ids_to_scan:
                try:
                    dns_records = get_dns_records_for_tunnel(zone_id, tunnel_id)
                    for record in dns_records:
                        hostname = record.get("name")
                        if hostname:
                            success = delete_cloudflare_dns_record(zone_id, hostname, tunnel_id)
                            if success:
                                cleanup_results["dns_records_deleted"] += 1
                                logging.info(f"Deleted DNS record {hostname} for tunnel {tunnel_id}")
                except Exception as dns_err:
                    logging.error(f"Failed to cleanup DNS records in zone {zone_id} for tunnel {tunnel_id}: {dns_err}")
        except Exception as e:
            logging.error(f"Failed to cleanup DNS records for tunnel {tunnel_id}: {e}")

    with state_lock:
        rules_to_remove = []
        for rule_key, rule in managed_rules.items():
            if rule.get("source") == "agent" and rule.get("agent_id") == agent_id:
                rules_to_remove.append(rule_key)

        for rule_key in rules_to_remove:
            del managed_rules[rule_key]
            cleanup_results["rules_removed"] += 1
            logging.info(f"Removed rule {rule_key} for agent {agent_id}")

        save_state()

    success = remove_agent(agent_id)
    if success:
        logging.info(f"Successfully removed agent {agent_id}")
        return jsonify({
            "status": "success",
            "message": f"Agent {agent_id} removed successfully.",
            "cleanup": cleanup_results
        }), 200
    else:
        return jsonify({"status": "error", "message": "Failed to remove agent from state."}), 500

@api_v2_bp.route('/agents/<agent_id>/trigger-migration', methods=['POST'])
def trigger_agent_migration(agent_id):
    try:
        from app.core.migration_service import TunnelMigrationService
        from app.core.state_manager import get_agent

        agent_record = get_agent(agent_id)
        if not agent_record:
            return jsonify({"status": "error", "message": "Agent not found."}), 404

        assigned_tunnel_id = agent_record.get("assigned_tunnel_id")
        if not assigned_tunnel_id:
            return jsonify({"status": "error", "message": "Agent not assigned to a tunnel."}), 400

        # Use containers from last status report
        containers = agent_record.get("last_containers", [])
        if not containers:
            return jsonify({"status": "error", "message": "No container data available for agent."}), 400

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

        if agent_record.get("status") != "enrolled":
            return jsonify({"status": "error", "message": "Agent not enrolled."}), 400

        tunnel_name = agent_record.get("assigned_tunnel_name")
        tunnel_id = agent_record.get("assigned_tunnel_id")
        tunnel_token = agent_record.get("tunnel_token")

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

@api_v2_bp.route('/agents/<agent_id>/rename', methods=['POST'])
def rename_agent(agent_id):
    try:
        from app.core.state_manager import get_agent, update_agent

        agent_record = get_agent(agent_id)
        if not agent_record:
            return jsonify({"status": "error", "message": "Agent not found."}), 404

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

        current_access_app_id = current_rule.get("access_app_id")
        session_duration = data.get('session_duration', current_rule.get("access_session_duration", "24h"))
        app_launcher_visible = data.get('app_launcher_visible', current_rule.get("access_app_launcher_visible", False))
        allowed_idps_str = data.get('allowed_idps_str', current_rule.get("access_allowed_idps_str"))
        auto_redirect = data.get('auto_redirect', current_rule.get("access_auto_redirect", False))

        desired_app_name = f"DockFlare-{hostname_for_access_app}" 
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
                existing_cf_app = find_cloudflare_access_application_by_hostname(hostname_for_access_app)
                if existing_cf_app and existing_cf_app.get("id"):
                    effective_app_id_for_operation = existing_cf_app.get("id")
                    logging.info(f"Found existing Access App ID '{effective_app_id_for_operation}' on Cloudflare for {hostname_for_access_app}. Will update.")
                    current_rule["access_app_id"] = effective_app_id_for_operation 
                    state_changed_locally = True
            
            if effective_app_id_for_operation:
                if current_rule.get("access_policy_type") != final_policy_type_for_state or \
                   current_rule.get("access_app_config_hash") != new_config_hash or \
                   current_rule.get("access_app_id") != effective_app_id_for_operation: 
                    
                    updated_app = update_cloudflare_access_application(
                        effective_app_id_for_operation, hostname_for_access_app, desired_app_name,
                        session_duration, app_launcher_visible, [hostname_for_access_app],
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
                    hostname_for_access_app, desired_app_name,
                    session_duration, app_launcher_visible, [hostname_for_access_app],
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
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client unavailable."}),

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
        elif initial_rule_source == "docker":
            current_rule["access_policy_ui_override"] = False
            state_changed_for_revert = True
            logging.info(f"API: Reverting Docker rule '{rule_key}' access policy to be label-driven.")
        else: 
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' has unknown source '{initial_rule_source}'."}), 500

        if state_changed_for_revert:
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

    reconcile_state_threaded()
    return jsonify({"status": "success", "message": f"Access policy for '{rule_key}' reverted. Reconciliation triggered."}),

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

        return jsonify({"status": "success", "message": "Provider updated successfully."})

    if request.method == 'DELETE':
        del providers[provider_index]

        if not _save_encrypted_config(config_data, fernet):
            return jsonify({"error": "failed_to_save_config"}), 500

        from app.web import config_loader
        config_loader.apply_config_to_app(current_app, config_data)

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
