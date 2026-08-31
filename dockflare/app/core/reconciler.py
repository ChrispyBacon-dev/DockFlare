# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute it and/or modify
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
# dockflare/app/core/reconciler.py
import logging
import time
import threading
import copy
from datetime import datetime, timedelta, timezone
from app import config, docker_client, tunnel_state, publish_state_event
from flask import current_app 

from app.core.state_manager import (
    find_container_rule,
    managed_rules,
    mark_rule_tunnel_sync_pending,
    restore_container_rule_key,
    restore_rule_lifecycle,
    state_lock,
    save_state,
    get_agent,
    update_agent,
)
from app.core.cloudflare_api import (
    get_account_zone_inventory,
    resolve_account_zone,
    create_cloudflare_dns_record,
    delete_cloudflare_dns_record
)
from app.core.zone_resolver import ZoneResolutionError
from app.core.access_manager import (
    handle_access_policy_from_labels, 
    delete_cloudflare_access_application 
)
from app.core.tunnel_manager import get_tunnel_operation_lock, update_cloudflare_config
from app.core.utils import get_rule_key, get_source_rule_key, get_label
from app.core import notification_manager

def _get_hostname_configs_from_container(container_obj):
    labels = container_obj.labels
    container_id_val = container_obj.id
    container_name_val = container_obj.name
    
    hostnames_configs = []

    default_path_label = get_label(labels, "path")
    default_originsrvname_label = get_label(labels, "originsrvname")
    default_http_host_header_label = get_label(labels, "httpHostHeader")

    default_access_groups = get_label(labels, "access.groups")
    default_access_group = get_label(labels, "access.group") if not default_access_groups else None
    default_access_policy_type = get_label(labels, "access.policy")

    if default_access_policy_type == "bypass" and not default_access_group and not default_access_groups:
        logging.info(f"RECONCILER: Legacy label 'dockflare.access.policy=bypass' detected for {container_name_val}. Migrating to 'dockflare.access.group=public-default-bypass'.")
        default_access_group = ["public-default-bypass"]
        default_access_policy_type = None
    elif default_access_group and not default_access_groups:
        if isinstance(default_access_group, str) and default_access_group == "bypass":
            logging.info(f"RECONCILER: Legacy group 'bypass' detected for {container_name_val}. Migrating to 'public-default-bypass'.")
            default_access_group = "public-default-bypass"
        elif isinstance(default_access_group, list) and "bypass" in default_access_group:
            logging.info(f"RECONCILER: Legacy group 'bypass' detected in list for {container_name_val}. Migrating to 'public-default-bypass'.")
            default_access_group = ["public-default-bypass" if g == "bypass" else g for g in default_access_group]
    elif default_access_policy_type == "authenticate" and not default_access_group and not default_access_groups:
        from app.core.cloudflare_api import get_cloudflare_account_email
        account_email = get_cloudflare_account_email()
        if account_email:
            logging.info(f"RECONCILER: Legacy label 'dockflare.access.policy=authenticate' detected for {container_name_val}. Migrating to 'dockflare.access.group=authenticated-default' (restricted to {account_email}).")
            default_access_group = ["authenticated-default"]
            default_access_policy_type = None
        else:
            logging.warning(f"RECONCILER: Cannot migrate 'dockflare.access.policy=authenticate' for {container_name_val}. Cloudflare account email not available. Skipping access policy creation. Use 'dockflare.access.group=<group>' instead.")
            default_access_policy_type = None

    if default_access_groups:
        default_access_group = [gid.strip() for gid in default_access_groups.split(',')]
    elif default_access_group:
        default_access_group = [default_access_group.strip()] if isinstance(default_access_group, str) else default_access_group
    default_access_app_name = get_label(labels, "access.name")
    default_session_duration = get_label(labels, "access.session_duration", "24h")
    default_app_launcher_visible = get_label(labels, "access.app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
    default_allowed_idps_str = get_label(labels, "access.allowed_idps")
    default_auto_redirect = get_label(labels, "access.auto_redirect_to_identity", "false").lower() in ["true", "1", "t", "yes"]
    default_custom_rules_str = get_label(labels, "access.custom_rules")

    h_main = get_label(labels, "hostname")
    s_main = get_label(labels, "service")
    zn_main = get_label(labels, "zonename")
    ntv_main_str = get_label(labels, "no_tls_verify", "false")
    ntv_main = ntv_main_str.lower() in ["true", "1", "t", "yes"]

    if h_main and s_main: 
        hostnames_configs.append({
            "hostname": h_main, "service": s_main, "zone_name": zn_main, 
            "path": default_path_label, 
            "no_tls_verify": ntv_main,
            "origin_server_name": default_originsrvname_label.strip() if default_originsrvname_label else None,
            "http_host_header": default_http_host_header_label.strip() if default_http_host_header_label else None,
            "container_id": container_id_val, "container_name": container_name_val,
            "access_group": default_access_group,
            "access_policy_type": default_access_policy_type,
            "access_app_name": default_access_app_name,
            "access_session_duration": default_session_duration,
            "access_app_launcher_visible": default_app_launcher_visible,
            "access_allowed_idps_str": default_allowed_idps_str,
            "access_auto_redirect": default_auto_redirect,
            "access_custom_rules_str": default_custom_rules_str
        })

    idx = 0
    while True:
        h_idx = get_label(labels, f"{idx}.hostname")
        if not h_idx:
            break
        
        s_idx = get_label(labels, f"{idx}.service", s_main)
        if not s_idx:
            idx += 1
            continue
            
        path_idx = get_label(labels, f"{idx}.path", default_path_label) 
        zn_idx = get_label(labels, f"{idx}.zonename", zn_main)
        ntv_idx_str = get_label(labels, f"{idx}.no_tls_verify", ntv_main_str) 
        ntv_idx = ntv_idx_str.lower() in ["true", "1", "t", "yes"]
        osn_idx_val = get_label(labels, f"{idx}.originsrvname", default_originsrvname_label)
        h_h_h_idx_val = get_label(labels, f"{idx}.httpHostHeader", default_http_host_header_label)

        acc_groups_idx = get_label(labels, f"{idx}.access.groups")
        acc_group_idx = get_label(labels, f"{idx}.access.group") if not acc_groups_idx else None
        if acc_groups_idx:
            acc_group_idx = [gid.strip() for gid in acc_groups_idx.split(',')]
        elif acc_group_idx:
            acc_group_idx = [acc_group_idx.strip()]
        else:
            acc_group_idx = default_access_group

        acc_pol_idx = get_label(labels, f"{idx}.access.policy", default_access_policy_type)
        acc_name_idx = get_label(labels, f"{idx}.access.name", default_access_app_name)
        acc_sess_idx = get_label(labels, f"{idx}.access.session_duration", default_session_duration)
        acc_vis_idx_str = get_label(labels, f"{idx}.access.app_launcher_visible", str(default_app_launcher_visible).lower())
        acc_vis_idx = acc_vis_idx_str.lower() in ["true", "1", "t", "yes"]
        acc_idps_idx = get_label(labels, f"{idx}.access.allowed_idps", default_allowed_idps_str)
        acc_redir_idx_str = get_label(labels, f"{idx}.access.auto_redirect_to_identity", str(default_auto_redirect).lower())
        acc_redir_idx = acc_redir_idx_str.lower() in ["true", "1", "t", "yes"]
        acc_custom_idx = get_label(labels, f"{idx}.access.custom_rules", default_custom_rules_str)
        
        hostnames_configs.append({
            "hostname": h_idx, "service": s_idx, "zone_name": zn_idx, 
            "path": path_idx, 
            "no_tls_verify": ntv_idx,
            "origin_server_name": osn_idx_val.strip() if osn_idx_val else None,
            "http_host_header": h_h_h_idx_val.strip() if h_h_h_idx_val else None,
            "container_id": container_id_val, "container_name": container_name_val,
            "access_group": acc_group_idx,
            "access_policy_type": acc_pol_idx, "access_app_name": acc_name_idx,
            "access_session_duration": acc_sess_idx, "access_app_launcher_visible": acc_vis_idx,
            "access_allowed_idps_str": acc_idps_idx, "access_auto_redirect": acc_redir_idx,
            "access_custom_rules_str": acc_custom_idx
        })
        idx += 1
    return hostnames_configs


def reconcile_agent_report(agent_id, reported_containers):
    """
    Self-heal: reconcile an individual agent's reported containers against master state.
    - reported_containers: list of dicts with keys: id, name, labels
    Returns True if any state was changed (rules restored), False otherwise.
    """
    from app import app as main_app
    try:
        with main_app.app_context():
            if not getattr(config, "AUTO_RESTORE_AGENT_RULES", True):
                logging.debug(f"[Reconcile-Agent] Auto-restore disabled by config. Skipping for agent {agent_id}.")
                return False

            now_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
            cooldown = getattr(config, "AUTO_RESTORE_COOLDOWN_SECONDS", 60)

            agent_record = get_agent(agent_id)
            if not agent_record:
                logging.debug(f"[Reconcile-Agent] No agent record found for {agent_id}. Skipping auto-restore.")
                return False
            
            last_auto_at = agent_record.get("last_auto_restore_at")
            if last_auto_at:
                try:
                    if last_auto_at.endswith('Z'):
                        last_auto_dt = datetime.fromisoformat(last_auto_at.replace('Z', '+00:00'))
                    else:
                        last_auto_dt = datetime.fromisoformat(last_auto_at)
                    last_auto_dt = last_auto_dt.replace(tzinfo=timezone.utc) if last_auto_dt.tzinfo is None else last_auto_dt.astimezone(timezone.utc)
                    elapsed = (now_dt - last_auto_dt).total_seconds()
                    if elapsed < cooldown:
                        logging.debug(f"[Reconcile-Agent] Cooldown active for agent {agent_id}; current observations will still be evaluated.")
                except Exception:
                    logging.debug(f"[Reconcile-Agent] Could not parse last_auto_restore_at for agent {agent_id}; continuing.")
            
            if not reported_containers:
                logging.debug(f"[Reconcile-Agent] No containers reported by agent {agent_id}; nothing to reconcile.")
                return False

            restored_any = False
            sync_needed = False
            desired_configs = {}
            dns_rekeys = []

            for c in reported_containers:
                labels = c.get("labels", {}) or {}
                c_id = c.get("id")
                c_name = c.get("name")
                container_like = type("CObj", (), {})()
                container_like.labels = labels
                container_like.id = c_id
                container_like.name = c_name
                try:
                    configs = _get_hostname_configs_from_container(container_like)
                except Exception as e:
                    logging.error(f"[Reconcile-Agent] Error parsing reported container {c_id} for agent {agent_id}: {e}", exc_info=True)
                    configs = []
                for conf in configs:
                    rk = get_rule_key(conf["hostname"], conf.get("path"))
                    desired_configs[rk] = conf

            if not desired_configs:
                logging.debug(f"[Reconcile-Agent] No hostname configs derived from agent {agent_id} reported containers.")
                return False

            overridden_keys = set()
            with state_lock:
                for observed_key, desired in desired_configs.items():
                    source_key = get_source_rule_key(desired["hostname"], desired.get("path"))
                    matched_key, existing = find_container_rule(source_key, "agent", agent_id)
                    if not existing or not existing.get("rule_ui_override"):
                        continue
                    changed, reactivated = restore_rule_lifecycle(existing, desired.get("container_id"))
                    if existing.get("source_rule_key") is None and matched_key == observed_key:
                        existing["source_rule_key"] = source_key
                        existing["lifecycle_generation"] = int(existing.get("lifecycle_generation") or 0) + 1
                        changed = True
                    if reactivated:
                        mark_rule_tunnel_sync_pending(existing)
                        sync_needed = True
                    restored_any |= changed
                    overridden_keys.add(observed_key)

            unresolved_desired = {key: value for key, value in desired_configs.items() if key not in overridden_keys}
            zone_inventory = get_account_zone_inventory() if unresolved_desired else None
            resolved_desired = {}
            for rule_key, desired in unresolved_desired.items():
                try:
                    resolved_desired[rule_key] = resolve_account_zone(
                        desired["hostname"],
                        explicit_zone_name=desired.get("zone_name") or None,
                        zones=zone_inventory["zones"],
                        inventory_status=zone_inventory["status"],
                        allow_unverified_default=True,
                    )
                except ZoneResolutionError as exc:
                    logging.warning(f"[Reconcile-Agent] Zone resolution failed for {rule_key} ({exc.code}). Skipping.")

            with state_lock:
                for rule_key, selected_zone in resolved_desired.items():
                    desired = desired_configs[rule_key]
                    source_key = get_source_rule_key(desired["hostname"], desired.get("path"))
                    existing, previous_source_render = restore_container_rule_key(
                        source_key,
                        desired["hostname"],
                        desired.get("path"),
                        "agent",
                        agent_id,
                    )
                    if previous_source_render:
                        restored_any = True
                        sync_needed = True
                        mark_rule_tunnel_sync_pending(existing)
                        old_tuple = (
                            previous_source_render.get("hostname"),
                            previous_source_render.get("zone_id"),
                            previous_source_render.get("tunnel_id"),
                        )
                        new_tuple = (
                            existing.get("hostname"),
                            existing.get("zone_id"),
                            existing.get("tunnel_id"),
                        )
                        if all(old_tuple) and all(new_tuple) and old_tuple != new_tuple:
                            dns_rekeys.append((old_tuple, new_tuple))
                    if existing is None:
                        existing = managed_rules.get(rule_key)
                    target_zone_id = selected_zone["id"]

                    if existing:
                        original_existing = copy.deepcopy(existing)
                        if existing.get("source") == "manual":
                            continue
                        if existing.get("source") != "agent" or existing.get("agent_id") != agent_id:
                            logging.warning("[Reconcile-Agent] Ownership mismatch for %s; observation ignored.", rule_key)
                            continue
                        if existing.get("source_rule_key") is None:
                            existing["source_rule_key"] = get_source_rule_key(desired["hostname"], desired.get("path"))
                            existing["lifecycle_generation"] = int(existing.get("lifecycle_generation") or 0) + 1
                            restored_any = True
                        if existing.get("rule_ui_override"):
                            if existing.get("status") == "pending_deletion":
                                existing["status"] = "active"
                                existing["delete_at"] = None
                                mark_rule_tunnel_sync_pending(existing)
                                sync_needed = True
                                restored_any = True
                            continue

                        if existing.get("status") == "pending_deletion":
                            existing["status"] = "active"
                            existing["delete_at"] = None
                            restored_any = True
                            logging.info(f"[Reconcile-Agent] Restored rule {rule_key} (was pending_deletion) for agent {agent_id}.")
                        changed = False
                        if existing.get("service") != desired.get("service"):
                            existing["service"] = desired.get("service")
                            changed = True
                        if existing.get("container_id") != desired.get("container_id"):
                            existing["container_id"] = desired.get("container_id")
                            changed = True
                        if existing.get("path") != desired.get("path"):
                            existing["path"] = desired.get("path")
                            changed = True
                        if existing.get("zone_id") != target_zone_id:
                            existing["zone_id"] = target_zone_id
                            changed = True
                        if existing.get("zone_name") != selected_zone.get("name"):
                            existing["zone_name"] = selected_zone.get("name")
                            changed = True
                        if existing.get("zone_resolution_source") != selected_zone.get("source"):
                            existing["zone_resolution_source"] = selected_zone.get("source")
                            changed = True
                        if existing.get("no_tls_verify") != desired.get("no_tls_verify"):
                            existing["no_tls_verify"] = desired.get("no_tls_verify")
                            changed = True
                        if existing.get("source") != "agent" or existing.get("agent_id") != agent_id:
                            existing["source"] = "agent"
                            existing["agent_id"] = agent_id
                            changed = True
                        if existing.get("tunnel_id") != agent_record.get("assigned_tunnel_id"):
                            existing["tunnel_id"] = agent_record.get("assigned_tunnel_id")
                            changed = True
                        if existing.get("tunnel_name") != agent_record.get("assigned_tunnel_name"):
                            existing["tunnel_name"] = agent_record.get("assigned_tunnel_name")
                            changed = True
                        if changed:
                            restored_any = True
                            logging.info(f"[Reconcile-Agent] Updated rule {rule_key} from agent {agent_id} report.")
                        tunnel_fields = (
                            "hostname", "path", "service", "zone_id", "no_tls_verify",
                            "origin_server_name", "http_host_header", "http2_origin",
                            "disable_chunked_encoding", "match_sni_to_host", "tunnel_id",
                        )
                        if (
                            original_existing.get("status") != existing.get("status")
                            or any(original_existing.get(field) != existing.get(field) for field in tunnel_fields)
                        ):
                            mark_rule_tunnel_sync_pending(existing)
                            sync_needed = True
                    else:
                        managed_rules[rule_key] = {
                            "hostname": desired["hostname"],
                            "path": desired.get("path"),
                            "service": desired["service"],
                            "container_id": desired.get("container_id"),
                            "status": "active",
                            "delete_at": None,
                            "zone_id": target_zone_id,
                            "zone_name": selected_zone.get("name"),
                            "zone_resolution_source": selected_zone.get("source"),
                            "no_tls_verify": desired.get("no_tls_verify"),
                            "origin_server_name": desired.get("origin_server_name"),
                            "http_host_header": desired.get("http_host_header"),
                            "access_app_id": None,
                            "access_policy_type": None,
                            "access_app_config_hash": None,
                            "access_policy_ui_override": False,
                            "rule_ui_override": False,
                            "source": "agent",
                            "agent_id": agent_id,
                            "access_group_id": None,
                            "tunnel_name": agent_record.get("assigned_tunnel_name"),
                            "tunnel_id": agent_record.get("assigned_tunnel_id"),
                            "source_rule_key": get_source_rule_key(desired["hostname"], desired.get("path")),
                            "tunnel_sync_pending": True,
                            "tunnel_sync_last_attempt_at": None,
                            "tunnel_sync_attempts": 0,
                            "lifecycle_generation": 0,
                        }
                        restored_any = True
                        sync_needed = True
                        logging.info(f"[Reconcile-Agent] Created missing rule {rule_key} for agent {agent_id} based on agent report.")

                if restored_any:
                    try:
                        update_agent(agent_id, {"last_auto_restore_at": now_dt.isoformat().replace('+00:00', 'Z')})
                    except Exception:
                        logging.exception(f"[Reconcile-Agent] Could not update agent record for last_auto_restore_at: {agent_id}")
                    save_state()
                    publish_state_event('snapshot_refresh')

            if sync_needed:
                try:
                    logging.info(f"[Reconcile-Agent] Triggering pending tunnel synchronization for agent {agent_id}.")
                    def sync_agent_changes():
                        retry_pending_tunnel_sync(force=True)
                        for old_tuple, new_tuple in dns_rekeys:
                            with state_lock:
                                new_rule_ready = any(
                                    rule.get("status") == "active"
                                    and not rule.get("tunnel_sync_pending")
                                    and (
                                        rule.get("hostname"), rule.get("zone_id"),
                                        _effective_rule_tunnel_id(rule),
                                    ) == new_tuple
                                    for rule in managed_rules.values()
                                )
                            if not new_rule_ready:
                                continue
                            dns_result = create_cloudflare_dns_record(new_tuple[1], new_tuple[0], new_tuple[2])
                            if not dns_result or dns_result in {"semaphore_timeout", "existing_record_unconfirmed"}:
                                continue
                            with state_lock:
                                old_tuple_owned = any(
                                    rule.get("status") == "active"
                                    and (
                                        rule.get("hostname"), rule.get("zone_id"),
                                        _effective_rule_tunnel_id(rule),
                                    ) == old_tuple
                                    for rule in managed_rules.values()
                                )
                            if not old_tuple_owned:
                                delete_cloudflare_dns_record(old_tuple[1], old_tuple[0], old_tuple[2])

                    t = threading.Thread(target=sync_agent_changes, name=f"agent-reconcile-{agent_id}", daemon=True)
                    t.start()
                except Exception as e:
                    logging.error(f"[Reconcile-Agent] Failed to trigger Cloudflare update: {e}", exc_info=True)

            return restored_any
    except Exception as e:
        logging.error(f"[Reconcile-Agent] Unexpected error reconciling agent {agent_id}: {e}", exc_info=True)
        return False

def _run_reconciliation_logic(): 
    from app import app as main_app_instance_for_context
    from app.core.state_manager import get_agent

    with main_app_instance_for_context.app_context(): 
        logging.info("[Reconcile Thread] Starting state reconciliation logic (with app context).")
        needs_tunnel_config_update = False 
        state_changed_locally = False
        max_total_time = 480 
        reconciliation_start_time = time.time()

        current_app.reconciliation_info = { 
            "in_progress": True, "progress": 0, "total_items": 0,
            "processed_items": 0, "start_time": reconciliation_start_time,
            "status": "Initializing reconciliation..."
        }
        
        running_labeled_rules_details = {}
        container_scan_complete = True
        try:
            current_app.reconciliation_info["status"] = "Scanning containers for services and access policies..."
            containers = docker_client.containers.list(sparse=False, all=config.SCAN_ALL_NETWORKS)
            container_count = len(containers)
            current_app.reconciliation_info["total_items"] = container_count
            processed_container_count = 0
            batch_size = 3 if not config.USE_EXTERNAL_CLOUDFLARED else 2

            for i in range(0, container_count, batch_size):
                if time.time() - reconciliation_start_time > 60:
                    logging.warning("[Reconcile] Timeout during container scanning phase.")
                    current_app.reconciliation_info["status"] = "Container scan timeout (partial data)"
                    container_scan_complete = False
                    break
                
                batch = containers[i:i+batch_size]
                processed_container_count += len(batch)
                current_app.reconciliation_info["progress"] = min(100, int((processed_container_count / container_count) * 100)) if container_count > 0 else 0
                current_app.reconciliation_info["status"] = f"Scanning containers: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                
                for c_obj in batch:
                    try:
                        c_obj.reload() 
                        if get_label(c_obj.labels, "enable", "false").lower() in ["true", "1", "t", "yes"]:
                            configs = _get_hostname_configs_from_container(c_obj)
                            for conf_item in configs:
                                rule_key = get_rule_key(conf_item["hostname"], conf_item.get("path"))
                                if rule_key in running_labeled_rules_details:
                                    logging.warning(f"[Reconcile] Duplicate rule '{rule_key}' found. Using from: {conf_item['container_name']}.")
                                running_labeled_rules_details[rule_key] = conf_item
                    except Exception as e_cont_scan:
                        logging.error(f"[Reconcile] Error processing container {c_obj.id[:12] if c_obj and c_obj.id else 'N/A'}: {e_cont_scan}")
            logging.info(f"[Reconcile] Found {len(running_labeled_rules_details)} running rules with DockFlare labels.")
        except Exception as e_phase1:
            container_scan_complete = False
            logging.error(f"[Reconcile] Error in container scanning phase: {e_phase1}", exc_info=True)
            current_app.reconciliation_info["status"] = f"Container scan error: {str(e_phase1)}"
            
        current_app.reconciliation_info["status"] = "Comparing state and reconciling cloud resources..."
        current_app.reconciliation_info["total_items"] = len(running_labeled_rules_details) + len(managed_rules) 
        current_app.reconciliation_info["processed_items"] = 0 
        processed_reconcile_items = 0
        hostnames_requiring_dns_setup = set()
        dns_cleanup_after_sync = set()
        policy_jobs_map = {}
        overridden_observed_keys = set()
        effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
        with state_lock:
            for observed_key, desired_details in running_labeled_rules_details.items():
                source_key = get_source_rule_key(desired_details["hostname"], desired_details.get("path"))
                matched_key, existing_rule = find_container_rule(source_key, "docker")
                if not existing_rule or not existing_rule.get("rule_ui_override"):
                    continue
                changed, reactivated = restore_rule_lifecycle(existing_rule, desired_details["container_id"])
                if existing_rule.get("source_rule_key") is None and matched_key == observed_key:
                    existing_rule["source_rule_key"] = source_key
                    existing_rule["lifecycle_generation"] = int(existing_rule.get("lifecycle_generation") or 0) + 1
                    changed = True
                if reactivated:
                    mark_rule_tunnel_sync_pending(existing_rule)
                    needs_tunnel_config_update = True
                state_changed_locally |= changed
                overridden_observed_keys.add(observed_key)
                if existing_rule.get("hostname") and existing_rule.get("zone_id"):
                    hostnames_requiring_dns_setup.add((existing_rule["hostname"], existing_rule["zone_id"], existing_rule.get("tunnel_id") or effective_tunnel_id))
        resolved_running_rules = {}
        rules_requiring_resolution = {
            key: details for key, details in running_labeled_rules_details.items()
            if key not in overridden_observed_keys
        }
        zone_inventory = get_account_zone_inventory() if rules_requiring_resolution else None
        for rule_key, desired_details in rules_requiring_resolution.items():
            try:
                resolved_running_rules[rule_key] = resolve_account_zone(
                    desired_details["hostname"],
                    explicit_zone_name=desired_details.get("zone_name") or None,
                    zones=zone_inventory["zones"],
                    inventory_status=zone_inventory["status"],
                    allow_unverified_default=True,
                )
            except ZoneResolutionError as exc:
                logging.error(f"[Reconcile] Zone resolution failed for {rule_key} ({exc.code}). Skipping.")

        with state_lock:
            now_utc = datetime.now(timezone.utc)
            current_managed_rule_keys_in_state = set(managed_rules.keys())
            master_tunnel_name = tunnel_state.get("name")
                            
            for rule_key, selected_zone in resolved_running_rules.items():
                desired_details = running_labeled_rules_details[rule_key]
                processed_reconcile_items +=1
                current_app.reconciliation_info["processed_items"] = processed_reconcile_items
                current_app.reconciliation_info["progress"] = min(100, int((processed_reconcile_items / current_app.reconciliation_info["total_items"]) * 100)) if current_app.reconciliation_info["total_items"] > 0 else 0
                current_app.reconciliation_info["status"] = f"Reconciling (active): {rule_key}"

                if time.time() - reconciliation_start_time > max_total_time - 30:
                    break

                source_key = get_source_rule_key(
                    desired_details["hostname"],
                    desired_details.get("path"),
                )
                existing_rule, previous_source_render = restore_container_rule_key(
                    source_key,
                    desired_details["hostname"],
                    desired_details.get("path"),
                    "docker",
                )
                if previous_source_render:
                    state_changed_locally = True
                    needs_tunnel_config_update = True
                    mark_rule_tunnel_sync_pending(existing_rule)
                    if (
                        previous_source_render.get("hostname")
                        and previous_source_render.get("zone_id")
                        and previous_source_render.get("tunnel_id")
                    ):
                        dns_cleanup_after_sync.add((
                            previous_source_render["hostname"],
                            previous_source_render["zone_id"],
                            previous_source_render["tunnel_id"],
                        ))
                if existing_rule is None:
                    existing_rule = managed_rules.get(rule_key)
                if existing_rule and existing_rule.get("source") == "manual":
                    continue
                if existing_rule and existing_rule.get("source", "docker") != "docker":
                    logging.warning("[Reconcile] Rule %s belongs to another source; observation ignored.", rule_key)
                    continue
                if existing_rule and existing_rule.get("source_rule_key") is None:
                    existing_rule["source_rule_key"] = get_source_rule_key(desired_details["hostname"], desired_details.get("path"))
                    existing_rule["lifecycle_generation"] = int(existing_rule.get("lifecycle_generation") or 0) + 1
                    state_changed_locally = True
                if existing_rule and existing_rule.get("rule_ui_override"):
                    if existing_rule.get("status") == "pending_deletion":
                        existing_rule["status"] = "active"
                        existing_rule["delete_at"] = None
                        mark_rule_tunnel_sync_pending(existing_rule)
                        needs_tunnel_config_update = True
                        state_changed_locally = True
                    if existing_rule.get("hostname") and existing_rule.get("zone_id"):
                        hostnames_requiring_dns_setup.add((existing_rule.get("hostname"), existing_rule.get("zone_id"), existing_rule.get("tunnel_id") or effective_tunnel_id))
                    continue

                target_zone_id = selected_zone["id"]
                
                if not existing_rule:
                    managed_rules[rule_key] = {
                        "hostname": desired_details["hostname"],
                        "path": desired_details.get("path"),
                        "service": desired_details["service"], 
                        "container_id": desired_details["container_id"],
                        "status": "active", "delete_at": None, "zone_id": target_zone_id,
                        "zone_name": selected_zone.get("name"),
                        "zone_resolution_source": selected_zone.get("source"),
                        "no_tls_verify": desired_details["no_tls_verify"],
                        "origin_server_name": desired_details.get("origin_server_name"),
                        "http_host_header": desired_details.get("http_host_header"),
                        "access_app_id": None, "access_policy_type": None, "access_app_config_hash": None,
                        "access_policy_ui_override": False, "rule_ui_override": False, "source": "docker",
                        "access_group_id": None,
                        "tunnel_name": master_tunnel_name,
                        "tunnel_id": effective_tunnel_id,
                        "source_rule_key": get_source_rule_key(desired_details["hostname"], desired_details.get("path")),
                        "tunnel_sync_pending": True,
                        "tunnel_sync_last_attempt_at": None,
                        "tunnel_sync_attempts": 0,
                        "lifecycle_generation": 0,
                    }
                    existing_rule = managed_rules[rule_key]
                    state_changed_locally = True
                    needs_tunnel_config_update = True
                else:
                    original_existing_rule = copy.deepcopy(existing_rule)
                    changed_in_reconcile = False
                    if existing_rule.get("status") == "pending_deletion":
                        existing_rule["status"] = "active"
                        existing_rule["delete_at"] = None
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True
                    
                    if existing_rule.get("service") != desired_details["service"]:
                        existing_rule["service"] = desired_details["service"]
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True
                    if existing_rule.get("no_tls_verify") != desired_details["no_tls_verify"]:
                        existing_rule["no_tls_verify"] = desired_details["no_tls_verify"]
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True
                    if existing_rule.get("zone_id") != target_zone_id:
                        existing_rule["zone_id"] = target_zone_id
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True 
                    if existing_rule.get("zone_name") != selected_zone.get("name"):
                        existing_rule["zone_name"] = selected_zone.get("name")
                        changed_in_reconcile = True
                    if existing_rule.get("zone_resolution_source") != selected_zone.get("source"):
                        existing_rule["zone_resolution_source"] = selected_zone.get("source")
                        changed_in_reconcile = True
                    if existing_rule.get("container_id") != desired_details["container_id"]:
                        existing_rule["container_id"] = desired_details["container_id"]
                        changed_in_reconcile = True
                    if existing_rule.get("path") != desired_details.get("path"):
                        existing_rule["path"] = desired_details.get("path")
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True
                    if existing_rule.get("origin_server_name") != desired_details.get("origin_server_name"):
                        existing_rule["origin_server_name"] = desired_details.get("origin_server_name")
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True
                    if existing_rule.get("http_host_header") != desired_details.get("http_host_header"):
                        existing_rule["http_host_header"] = desired_details.get("http_host_header")
                        changed_in_reconcile = True
                        needs_tunnel_config_update = True
                    
                    if existing_rule.get("tunnel_name") != master_tunnel_name:
                        existing_rule["tunnel_name"] = master_tunnel_name
                        changed_in_reconcile = True
                    if existing_rule.get("tunnel_id") != effective_tunnel_id:
                        existing_rule["tunnel_id"] = effective_tunnel_id
                        changed_in_reconcile = True

                    existing_rule["source"] = "docker" 
                    if changed_in_reconcile:
                        state_changed_locally = True
                    tunnel_fields = (
                        "hostname", "path", "service", "zone_id", "no_tls_verify",
                        "origin_server_name", "http_host_header", "http2_origin",
                        "disable_chunked_encoding", "match_sni_to_host", "tunnel_id",
                    )
                    if (
                        original_existing_rule.get("status") != existing_rule.get("status")
                        or any(original_existing_rule.get(field) != existing_rule.get(field) for field in tunnel_fields)
                    ):
                        mark_rule_tunnel_sync_pending(existing_rule)
                
                hostnames_requiring_dns_setup.add((desired_details["hostname"], target_zone_id, effective_tunnel_id))
                
                if not existing_rule.get("access_policy_ui_override", False):
                    policy_jobs_map[rule_key] = copy.deepcopy(desired_details)
            
            observed_source_keys = {
                get_source_rule_key(details["hostname"], details.get("path"))
                for details in running_labeled_rules_details.values()
            }
            rule_keys_in_state_but_not_running = [
                key for key in current_managed_rule_keys_in_state
                if key not in running_labeled_rules_details
                and not (
                    managed_rules.get(key, {}).get("source_rule_key")
                    and managed_rules[key]["source_rule_key"] in observed_source_keys
                )
            ]
            for rule_key_to_check in rule_keys_in_state_but_not_running:
                processed_reconcile_items +=1 
                current_app.reconciliation_info["processed_items"] = processed_reconcile_items
                            
                if time.time() - reconciliation_start_time > max_total_time - 20:
                    break
                
                rule = managed_rules.get(rule_key_to_check)
                if rule and rule.get("status") == "active":
                    if rule.get("source", "docker") == "docker" and container_scan_complete:
                        logging.info(f"[Reconcile] Docker-managed rule {rule_key_to_check} active but container/labels gone. Marking for deletion.")
                        rule["status"] = "pending_deletion"
                        grace_period = current_app.config.get('GRACE_PERIOD_SECONDS', 28800)
                        rule["delete_at"] = now_utc + timedelta(seconds=grace_period)
                        state_changed_locally = True
                    elif rule.get("source") == "manual" and rule.get("zone_id") and rule.get("hostname"):
                        manual_rule_tunnel_id = rule.get("tunnel_id") or effective_tunnel_id
                        hostnames_requiring_dns_setup.add((rule.get("hostname"), rule.get("zone_id"), manual_rule_tunnel_id))
                    elif rule.get("source") == "agent" and rule.get("zone_id") and rule.get("hostname"):
                        agent_id = rule.get("agent_id")
                        if agent_id:
                            agent_record = get_agent(agent_id)
                            if agent_record:
                                agent_tunnel_id = agent_record.get("assigned_tunnel_id")
                                if agent_tunnel_id:
                                    hostnames_requiring_dns_setup.add((rule.get("hostname"), rule.get("zone_id"), agent_tunnel_id))

        policy_state_changed = False
        for rule_key, details in policy_jobs_map.items():
            if handle_access_policy_from_labels(rule_key, copy.deepcopy(details)):
                policy_state_changed = True

        if policy_state_changed:
            state_changed_locally = True

        if state_changed_locally:
            current_app.reconciliation_info["status"] = "Saving reconciled state..."
            save_state()
            publish_state_event('snapshot_refresh')

        if time.time() - reconciliation_start_time > max_total_time - 15:
            logging.warning("[Reconcile] Timeout before Tunnel/DNS operations.")
            needs_tunnel_config_update = False 

        if needs_tunnel_config_update:
            current_app.reconciliation_info["status"] = "Updating Cloudflare tunnel configuration..."
            if not update_cloudflare_config(effective_tunnel_id):
                logging.error("[Reconcile] Failed to update Cloudflare tunnel configuration.")
                current_app.reconciliation_info["status"] = "Error: Failed tunnel config update."
                notification_manager.emit(
                    "cloudflare.tunnel_failure",
                    str(effective_tunnel_id or "master"),
                    {"tunnel_id": str(effective_tunnel_id or "")[:12], "operation": "reconciliation update"},
                )
            else:
                logging.info("[Reconcile] Cloudflare tunnel configuration updated successfully.")
                current_app.reconciliation_info["status"] = "Tunnel configuration updated."
                sync_state_changed = False
                with state_lock:
                    for rule in managed_rules.values():
                        if rule.get("source", "docker") == "docker" and _effective_rule_tunnel_id(rule) == effective_tunnel_id and rule.get("tunnel_sync_pending"):
                            rule["tunnel_sync_pending"] = False
                            rule["tunnel_sync_last_attempt_at"] = None
                            rule["tunnel_sync_attempts"] = 0
                            rule["lifecycle_generation"] = int(rule.get("lifecycle_generation") or 0) + 1
                            sync_state_changed = True
                if sync_state_changed:
                    save_state()
        
        if hostnames_requiring_dns_setup:
            unique_dns_setups = list(hostnames_requiring_dns_setup)
            dns_total = len(unique_dns_setups)
            current_app.reconciliation_info["status"] = f"Setting up DNS for {dns_total} hostnames..."
            dns_processed_count = 0
            
            logging.info(f"[Reconcile] Unique hostnames for DNS setup/check: {len(unique_dns_setups)}")
            for hostname_dns, zone_id_dns, tunnel_id_dns in unique_dns_setups:
                dns_processed_count +=1 
                current_app.reconciliation_info["status"] = f"DNS for {hostname_dns} ({dns_processed_count}/{dns_total})"
                if time.time() - reconciliation_start_time > max_total_time - 5:
                    break
                
                if tunnel_id_dns and not hostname_dns.startswith('*.'):
                    try:
                        dns_result = create_cloudflare_dns_record(zone_id_dns, hostname_dns, tunnel_id_dns)
                    except Exception:
                        logging.exception("[Reconcile] DNS creation raised for %s.", hostname_dns)
                        dns_result = None
                    if not dns_result or dns_result in {"semaphore_timeout", "existing_record_unconfirmed"}:
                        notification_manager.emit(
                            "cloudflare.dns_failure",
                            f"{zone_id_dns}:{hostname_dns}",
                            {"hostname": hostname_dns, "operation": "reconciliation create"},
                        )
                    if config.USE_EXTERNAL_CLOUDFLARED:
                        time.sleep(0.1)
                elif not tunnel_id_dns:
                    logging.error(f"[Reconcile] Cannot setup DNS for {hostname_dns}: Tunnel ID is missing.")
                    notification_manager.emit(
                        "cloudflare.tunnel_failure",
                        hostname_dns,
                        {"hostname": hostname_dns, "operation": "reconciliation resolve tunnel"},
                    )

        for old_hostname, old_zone_id, old_tunnel_id in dns_cleanup_after_sync:
            with state_lock:
                sync_pending = any(
                    rule.get("tunnel_sync_pending")
                    and _effective_rule_tunnel_id(rule) == old_tunnel_id
                    for rule in managed_rules.values()
                )
                still_owned = any(
                    rule.get("status") == "active"
                    and rule.get("hostname") == old_hostname
                    and rule.get("zone_id") == old_zone_id
                    and _effective_rule_tunnel_id(rule) == old_tunnel_id
                    for rule in managed_rules.values()
                )
            if not sync_pending and not still_owned and not old_hostname.startswith("*."):
                if not delete_cloudflare_dns_record(old_zone_id, old_hostname, old_tunnel_id):
                    notification_manager.emit(
                        "cloudflare.dns_failure",
                        f"{old_zone_id}:{old_hostname}",
                        {"hostname": old_hostname, "operation": "reconciliation delete"},
                    )
                
        current_app.reconciliation_info["in_progress"] = False
        current_app.reconciliation_info["progress"] = 100 
        final_status = current_app.reconciliation_info.get("status", "Reconciliation finished.")
        if not final_status.endswith("(Final)"):
            final_status += " (Final)"
        current_app.reconciliation_info["status"] = final_status
        current_app.reconciliation_info["completed_at"] = time.time()
        duration = current_app.reconciliation_info["completed_at"] - current_app.reconciliation_info["start_time"]
        logging.info(f"[Reconcile Thread] Reconciliation complete. Duration: {duration:.2f}s. Status: {current_app.reconciliation_info['status']}")

def reconcile_state_threaded(): 
    if not docker_client:
        logging.warning("Docker client unavailable, skipping reconciliation.")
        return
    if not tunnel_state.get("id") and not config.EXTERNAL_TUNNEL_ID: 
        logging.warning("Tunnel not initialized (no ID), skipping reconciliation.")
        return
    
    from app import app as main_app_instance_for_thread_check

    if not hasattr(main_app_instance_for_thread_check, 'reconciliation_info'):
        logging.error("main_app_instance_for_thread_check.reconciliation_info not initialized. Cannot start reconciliation.")
        main_app_instance_for_thread_check.reconciliation_info = {"in_progress": False} 
        
    if main_app_instance_for_thread_check.reconciliation_info.get("in_progress", False):
        logging.info("Reconciliation is already in progress. Skipping new request.")
        return

    reconcile_thread = threading.Thread(
        target=_run_reconciliation_logic, 
        name="ReconciliationThread",
        daemon=True
    )
    reconcile_thread.start()
    logging.info(f"Started reconciliation in background thread {reconcile_thread.name}")

def _effective_rule_tunnel_id(rule):
    explicit_tunnel_id = rule.get("tunnel_id")
    if explicit_tunnel_id:
        return explicit_tunnel_id
    return config.EXTERNAL_TUNNEL_ID if config.USE_EXTERNAL_CLOUDFLARED else tunnel_state.get("id")


def _candidate_still_matches(candidate):
    rule = managed_rules.get(candidate["key"])
    if not rule:
        return False
    return (
        rule.get("status") == candidate["status"]
        and rule.get("delete_at") == candidate["delete_at"]
        and rule.get("container_id") == candidate["container_id"]
        and rule.get("source", "docker") == candidate["source"]
        and rule.get("agent_id") == candidate["agent_id"]
        and rule.get("lifecycle_generation", 0) == candidate["lifecycle_generation"]
        and rule.get("tunnel_id") == candidate["tunnel_id"]
    )


def cleanup_expired_rules_once(now=None):
    current_time = now or datetime.now(timezone.utc)
    candidates = []
    with state_lock:
        for key, rule in managed_rules.items():
            if rule.get("source", "docker") not in {"docker", "agent"} or rule.get("status") != "pending_deletion":
                continue
            deadline = rule.get("delete_at")
            if isinstance(deadline, datetime):
                deadline = deadline.astimezone(timezone.utc) if deadline.tzinfo else deadline.replace(tzinfo=timezone.utc)
                if deadline > current_time:
                    continue
            candidates.append({
                "key": key,
                "status": rule.get("status"),
                "delete_at": rule.get("delete_at"),
                "container_id": rule.get("container_id"),
                "source": rule.get("source", "docker"),
                "agent_id": rule.get("agent_id"),
                "lifecycle_generation": rule.get("lifecycle_generation", 0),
                "tunnel_id": rule.get("tunnel_id"),
                "effective_tunnel_id": _effective_rule_tunnel_id(rule),
                "hostname": rule.get("hostname"),
                "zone_id": rule.get("zone_id"),
                "access_app_id": rule.get("access_app_id"),
            })

    groups = {}
    for candidate in candidates:
        groups.setdefault(candidate["effective_tunnel_id"], []).append(candidate)
    committed = 0
    committed_candidates = []
    tunnel_failures = []
    dns_failures = []
    access_failures = []
    for tunnel_id in sorted(groups, key=lambda value: str(value or "")):
        if not tunnel_id:
            logging.error("Cleanup retained %s rules because their effective tunnel is missing.", len(groups[tunnel_id]))
            continue
        with get_tunnel_operation_lock(tunnel_id):
            with state_lock:
                valid = [candidate for candidate in groups[tunnel_id] if _candidate_still_matches(candidate)]
            if not valid:
                continue
            if not update_cloudflare_config(tunnel_id):
                tunnel_failures.append(tunnel_id)
                continue
            successful = []
            for candidate in valid:
                with state_lock:
                    if not _candidate_still_matches(candidate):
                        continue
                    dns_shared = any(
                        key != candidate["key"]
                        and rule.get("hostname") == candidate["hostname"]
                        and rule.get("zone_id") == candidate["zone_id"]
                        and _effective_rule_tunnel_id(rule) == tunnel_id
                        for key, rule in managed_rules.items()
                    )
                    app_shared = candidate["access_app_id"] and any(
                        key != candidate["key"] and rule.get("access_app_id") == candidate["access_app_id"]
                        for key, rule in managed_rules.items()
                    )
                if candidate["hostname"] and not dns_shared and not delete_cloudflare_dns_record(candidate["zone_id"], candidate["hostname"], tunnel_id):
                    dns_failures.append(candidate)
                    continue
                if candidate["access_app_id"] and not app_shared and not delete_cloudflare_access_application(candidate["access_app_id"]):
                    access_failures.append(candidate)
                    continue
                successful.append(candidate)
            with state_lock:
                for candidate in successful:
                    if _candidate_still_matches(candidate):
                        del managed_rules[candidate["key"]]
                        committed += 1
                        committed_candidates.append(candidate)
                if successful:
                    save_state()
    if committed:
        publish_state_event("snapshot_refresh")
        notification_manager.emit(
            "rule.deleted",
            f"cleanup:{int(current_time.timestamp())}",
            {
                "source": "cleanup",
                "resources": [
                    {
                        "key": candidate["key"],
                        "hostname": candidate.get("hostname"),
                        "source": candidate.get("source"),
                    }
                    for candidate in committed_candidates
                ],
                "public_url": config.DOCKFLARE_PUBLIC_URL,
            },
        )
    for tunnel_id in tunnel_failures:
        notification_manager.emit(
            "cloudflare.tunnel_failure",
            tunnel_id,
            {"tunnel_id": str(tunnel_id)[:12], "operation": "cleanup update"},
        )
    for candidate in dns_failures:
        notification_manager.emit(
            "cloudflare.dns_failure",
            f"{candidate.get('zone_id')}:{candidate.get('hostname')}",
            {"hostname": candidate.get("hostname"), "operation": "delete", "source": candidate.get("source")},
        )
    for candidate in access_failures:
        notification_manager.emit(
            "cloudflare.access_failure",
            candidate["key"],
            {"hostname": candidate.get("hostname"), "operation": "delete", "source": candidate.get("source")},
        )
    return committed


def retry_pending_tunnel_sync(now=None, force=False):
    current_time = now or datetime.now(timezone.utc)
    pending_tunnels = set()
    with state_lock:
        for rule in managed_rules.values():
            if rule.get("tunnel_sync_pending"):
                tunnel_id = _effective_rule_tunnel_id(rule)
                if tunnel_id:
                    pending_tunnels.add(tunnel_id)
    changed = False
    for tunnel_id in sorted(pending_tunnels):
        with state_lock:
            rules = [rule for rule in managed_rules.values() if rule.get("tunnel_sync_pending") and _effective_rule_tunnel_id(rule) == tunnel_id]
            eligible = force
            if not eligible:
                for rule in rules:
                    last_attempt = rule.get("tunnel_sync_last_attempt_at")
                    if not isinstance(last_attempt, datetime) or (current_time - last_attempt).total_seconds() >= config.TUNNEL_SYNC_RETRY_SECONDS:
                        eligible = True
                        break
            if not eligible:
                continue
            for rule in rules:
                rule["tunnel_sync_last_attempt_at"] = current_time
                rule["tunnel_sync_attempts"] = int(rule.get("tunnel_sync_attempts") or 0) + 1
                changed = True
        success = update_cloudflare_config(tunnel_id)
        if not success:
            notification_manager.emit(
                "cloudflare.tunnel_failure",
                tunnel_id,
                {
                    "tunnel_id": str(tunnel_id)[:12],
                    "operation": "retry pending synchronization",
                    "retry_count": max((int(rule.get("tunnel_sync_attempts") or 0) for rule in rules), default=0),
                },
            )
        if success:
            with state_lock:
                for rule in managed_rules.values():
                    if rule.get("tunnel_sync_pending") and _effective_rule_tunnel_id(rule) == tunnel_id:
                        rule["tunnel_sync_pending"] = False
                        rule["tunnel_sync_last_attempt_at"] = None
                        rule["tunnel_sync_attempts"] = 0
                        rule["lifecycle_generation"] = int(rule.get("lifecycle_generation") or 0) + 1
                        changed = True
    if changed:
        save_state()
        publish_state_event("snapshot_refresh")
    return changed


def cleanup_expired_rules(stop_event_param):
    from app import app as main_app
    if stop_event_param is None:
        return
    while not stop_event_param.is_set():
        with main_app.app_context():
            try:
                cleanup_expired_rules_once()
                retry_pending_tunnel_sync()
            except Exception:
                logging.exception("Expired-rule cleanup pass failed.")
        stop_event_param.wait(config.CLEANUP_INTERVAL_SECONDS)
