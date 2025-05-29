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
# app/core/reconciler.py
import copy
import logging
import time
import threading
from datetime import datetime, timedelta, timezone
import json 

from app import config, docker_client, tunnel_state, cloudflared_agent_state
from flask import current_app 

from app.core.state_manager import managed_rules, state_lock, save_state
from app.core.cloudflare_api import (
    get_zone_id_from_name, 
    create_cloudflare_dns_record,
    delete_cloudflare_dns_record
)
from app.core.access_manager import (
    handle_access_policy_from_labels, 
    delete_cloudflare_access_application 
)
from app.core.tunnel_manager import update_cloudflare_config

def _get_hostname_configs_from_container(container_obj):
    labels = container_obj.labels
    container_id_val = container_obj.id
    container_name_val = container_obj.name
    
    hostnames_configs = []

    default_path_label = labels.get(f"{config.LABEL_PREFIX}.path") 
    default_originsrvname_label = labels.get(f"{config.LABEL_PREFIX}.originsrvname")
    default_access_policy_type = labels.get(f"{config.LABEL_PREFIX}.access.policy")
    default_access_app_name = labels.get(f"{config.LABEL_PREFIX}.access.name")
    default_session_duration = labels.get(f"{config.LABEL_PREFIX}.access.session_duration", "24h")
    default_app_launcher_visible = labels.get(f"{config.LABEL_PREFIX}.access.app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
    default_allowed_idps_str = labels.get(f"{config.LABEL_PREFIX}.access.allowed_idps")
    default_auto_redirect = labels.get(f"{config.LABEL_PREFIX}.access.auto_redirect_to_identity", "false").lower() in ["true", "1", "t", "yes"]
    default_custom_rules_str = labels.get(f"{config.LABEL_PREFIX}.access.custom_rules")

    h_main = labels.get(f"{config.LABEL_PREFIX}.hostname")
    s_main = labels.get(f"{config.LABEL_PREFIX}.service")
    zn_main = labels.get(f"{config.LABEL_PREFIX}.zonename")
    ntv_main_str = labels.get(f"{config.LABEL_PREFIX}.no_tls_verify", "false")
    ntv_main = ntv_main_str.lower() in ["true", "1", "t", "yes"]

    if h_main and s_main: 
        hostnames_configs.append({
            "hostname": h_main, "service": s_main, "zone_name": zn_main, 
            "path": default_path_label, 
            "no_tls_verify": ntv_main,
            "origin_server_name": default_originsrvname_label.strip() if default_originsrvname_label else None,
            "container_id": container_id_val, "container_name": container_name_val,
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
        pfx = f"{config.LABEL_PREFIX}.{idx}"
        h_idx = labels.get(f"{pfx}.hostname")
        if not h_idx: break
        
        s_idx = labels.get(f"{pfx}.service", s_main)
        if not s_idx: 
            idx += 1; continue
            
        path_idx = labels.get(f"{pfx}.path", default_path_label) 
        zn_idx = labels.get(f"{pfx}.zonename", zn_main)
        ntv_idx_str = labels.get(f"{pfx}.no_tls_verify", ntv_main_str) 
        ntv_idx = ntv_idx_str.lower() in ["true", "1", "t", "yes"]
        osn_idx_val = labels.get(f"{pfx}.originsrvname", default_originsrvname_label)

        acc_pol_idx = labels.get(f"{pfx}.access.policy", default_access_policy_type)
        acc_name_idx = labels.get(f"{pfx}.access.name", default_access_app_name)
        acc_sess_idx = labels.get(f"{pfx}.access.session_duration", default_session_duration)
        acc_vis_idx_str = labels.get(f"{pfx}.access.app_launcher_visible", str(default_app_launcher_visible).lower())
        acc_vis_idx = acc_vis_idx_str.lower() in ["true", "1", "t", "yes"]
        acc_idps_idx = labels.get(f"{pfx}.access.allowed_idps", default_allowed_idps_str)
        acc_redir_idx_str = labels.get(f"{pfx}.access.auto_redirect_to_identity", str(default_auto_redirect).lower())
        acc_redir_idx = acc_redir_idx_str.lower() in ["true", "1", "t", "yes"]
        acc_custom_idx = labels.get(f"{pfx}.access.custom_rules", default_custom_rules_str)
        
        hostnames_configs.append({
            "hostname": h_idx, "service": s_idx, "zone_name": zn_idx, 
            "path": path_idx, 
            "no_tls_verify": ntv_idx,
            "origin_server_name": osn_idx_val.strip() if osn_idx_val else None,
            "container_id": container_id_val, "container_name": container_name_val,
            "access_policy_type": acc_pol_idx, "access_app_name": acc_name_idx,
            "access_session_duration": acc_sess_idx, "access_app_launcher_visible": acc_vis_idx,
            "access_allowed_idps_str": acc_idps_idx, "access_auto_redirect": acc_redir_idx,
            "access_custom_rules_str": acc_custom_idx
        })
        idx += 1
    return hostnames_configs

def _run_reconciliation_logic(): 
    from app import app as main_app_instance_for_context 

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
        
        running_labeled_hostnames_details = {}
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
                    break
                
                batch = containers[i:i+batch_size]
                processed_container_count += len(batch)
                current_app.reconciliation_info["progress"] = min(100, int((processed_container_count / container_count) * 100)) if container_count > 0 else 0
                current_app.reconciliation_info["processed_items"] = processed_container_count
                current_app.reconciliation_info["status"] = f"Scanning containers: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                
                for c_obj in batch:
                    try:
                        c_obj.reload() 
                        if c_obj.labels.get(f"{config.LABEL_PREFIX}.enable", "false").lower() in ["true", "1", "t", "yes"]:
                            configs = _get_hostname_configs_from_container(c_obj)
                            for conf_item in configs: 
                                if conf_item["hostname"] in running_labeled_hostnames_details:
                                    logging.warning(f"[Reconcile] Duplicate hostname '{conf_item['hostname']}' found. Using from: {conf_item['container_name']}.")
                                running_labeled_hostnames_details[conf_item["hostname"]] = conf_item
                    except Exception as e_cont_scan:
                        logging.error(f"[Reconcile] Error processing container {c_obj.id[:12] if c_obj and c_obj.id else 'N/A'}: {e_cont_scan}")
            logging.info(f"[Reconcile] Found {len(running_labeled_hostnames_details)} running hostnames with DockFlare labels.")
        except Exception as e_phase1:
            logging.error(f"[Reconcile] Error in container scanning phase: {e_phase1}", exc_info=True)
            current_app.reconciliation_info["status"] = f"Container scan error: {str(e_phase1)}"
            
        current_app.reconciliation_info["status"] = "Comparing state and reconciling cloud resources..."
        current_app.reconciliation_info["total_items"] = len(running_labeled_hostnames_details) + len(managed_rules) 
        current_app.reconciliation_info["processed_items"] = 0 
        processed_reconcile_items = 0
        hostnames_requiring_dns_setup = []

        with state_lock:
            now_utc = datetime.now(timezone.utc)
            current_managed_hostnames_in_state = set(managed_rules.keys())
                            
            for hostname, desired_details in running_labeled_hostnames_details.items():
                processed_reconcile_items +=1
                current_app.reconciliation_info["processed_items"] = processed_reconcile_items
                current_app.reconciliation_info["progress"] = min(100, int((processed_reconcile_items / current_app.reconciliation_info["total_items"]) * 100)) if current_app.reconciliation_info["total_items"] > 0 else 0
                current_app.reconciliation_info["status"] = f"Reconciling (active): {hostname}"

                if time.time() - reconciliation_start_time > max_total_time - 30: break

                existing_rule = managed_rules.get(hostname)
                if existing_rule and existing_rule.get("source") == "manual":
                    continue

                target_zone_id = get_zone_id_from_name(desired_details["zone_name"]) if desired_details["zone_name"] else config.CF_ZONE_ID
                if not target_zone_id:
                    logging.error(f"[Reconcile] No zone ID for {hostname}, skipping its reconciliation.")
                    continue

                if not existing_rule:
                    managed_rules[hostname] = {
                        "service": desired_details["service"], "container_id": desired_details["container_id"],
                        "status": "active", "delete_at": None, "zone_id": target_zone_id,
                        "no_tls_verify": desired_details["no_tls_verify"],
                        "access_app_id": None, "access_policy_type": None, "access_app_config_hash": None,
                        "access_policy_ui_override": False, "source": "docker"
                    }
                    existing_rule = managed_rules[hostname]
                    state_changed_locally = True
                    needs_tunnel_config_update = True
                    hostnames_requiring_dns_setup.append((hostname, target_zone_id))
                else:
                    changed_in_reconcile = False
                    if existing_rule.get("status") == "pending_deletion":
                        existing_rule["status"] = "active"; existing_rule["delete_at"] = None
                        changed_in_reconcile = True; needs_tunnel_config_update = True
                    
                    if existing_rule.get("service") != desired_details["service"]:
                        existing_rule["service"] = desired_details["service"]; changed_in_reconcile = True; needs_tunnel_config_update = True
                    if existing_rule.get("no_tls_verify") != desired_details["no_tls_verify"]:
                        existing_rule["no_tls_verify"] = desired_details["no_tls_verify"]; changed_in_reconcile = True; needs_tunnel_config_update = True
                    if existing_rule.get("zone_id") != target_zone_id:
                        existing_rule["zone_id"] = target_zone_id; changed_in_reconcile = True; needs_tunnel_config_update = True 
                    if existing_rule.get("container_id") != desired_details["container_id"]:
                        existing_rule["container_id"] = desired_details["container_id"]; changed_in_reconcile = True
                    
                    existing_rule["source"] = "docker" 
                    if changed_in_reconcile: state_changed_locally = True
                    hostnames_requiring_dns_setup.append((hostname, target_zone_id)) 
                
                if existing_rule.get("access_policy_ui_override", False):
                    pass 
                else:
                    if handle_access_policy_from_labels(desired_details, existing_rule, None):
                        state_changed_locally = True
            
            hostnames_in_state_but_not_running = list(current_managed_hostnames_in_state - set(running_labeled_hostnames_details.keys()))
            for hostname_to_check in hostnames_in_state_but_not_running:
                # ... (rest of this loop using current_app.reconciliation_info)
                processed_reconcile_items +=1 
                current_app.reconciliation_info["processed_items"] = processed_reconcile_items
                            
                if time.time() - reconciliation_start_time > max_total_time - 20: break
                
                rule = managed_rules.get(hostname_to_check)
                if rule and rule.get("status") == "active" and rule.get("source", "docker") == "docker":
                    logging.info(f"[Reconcile] Docker-managed rule {hostname_to_check} active but container/labels gone. Marking for deletion.")
                    rule["status"] = "pending_deletion"
                    rule["delete_at"] = now_utc + timedelta(seconds=config.GRACE_PERIOD_SECONDS)
                    state_changed_locally = True
                elif rule and rule.get("source") == "manual" and rule.get("zone_id"):
                     hostnames_requiring_dns_setup.append((hostname_to_check, rule.get("zone_id")))

            if state_changed_locally:
                current_app.reconciliation_info["status"] = "Saving reconciled state..."
                save_state()

        if time.time() - reconciliation_start_time > max_total_time - 15:
            logging.warning("[Reconcile] Timeout before Tunnel/DNS operations.")
            needs_tunnel_config_update = False 

        if needs_tunnel_config_update:
            current_app.reconciliation_info["status"] = "Updating Cloudflare tunnel configuration..."
            if not config.USE_EXTERNAL_CLOUDFLARED:
                if not update_cloudflare_config():
                    logging.error("[Reconcile] Failed to update Cloudflare tunnel configuration.")
                    current_app.reconciliation_info["status"] = "Error: Failed tunnel config update."
                else:
                    logging.info("[Reconcile] Cloudflare tunnel configuration updated successfully.")
                    current_app.reconciliation_info["status"] = "Tunnel configuration updated."
            else:
                logging.info("[Reconcile] External mode: Skipping DockFlare-managed tunnel config update.")
                current_app.reconciliation_info["status"] = "Tunnel config update skipped (external mode)."
        
        if hostnames_requiring_dns_setup:
            dns_total = len(hostnames_requiring_dns_setup)
            current_app.reconciliation_info["status"] = f"Setting up DNS for {dns_total} hostnames..."
            dns_processed_count = 0
            effective_tunnel_id_for_dns = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
            
            if effective_tunnel_id_for_dns:
                unique_dns_setups = list(set(hostnames_requiring_dns_setup)) 
                logging.info(f"[Reconcile] Unique hostnames for DNS setup/check: {len(unique_dns_setups)}")
                for hostname_dns, zone_id_dns in unique_dns_setups:
                    dns_processed_count +=1 
                    current_app.reconciliation_info["status"] = f"DNS for {hostname_dns} ({dns_processed_count}/{len(unique_dns_setups)})"
                    if time.time() - reconciliation_start_time > max_total_time - 5: break
                    create_cloudflare_dns_record(zone_id_dns, hostname_dns, effective_tunnel_id_for_dns)
                    if config.USE_EXTERNAL_CLOUDFLARED: time.sleep(0.1) 
            else:
                logging.error("[Reconcile] Cannot setup DNS: Effective tunnel ID is missing.")
                current_app.reconciliation_info["status"] = "Error: Missing tunnel ID for DNS setup."
                
        current_app.reconciliation_info["in_progress"] = False
        current_app.reconciliation_info["progress"] = 100 
        final_status = current_app.reconciliation_info.get("status", "Reconciliation finished.")
        if not final_status.endswith("(Final)"): final_status += " (Final)"
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

def cleanup_expired_rules(stop_event_param):
    logging.info("Starting cleanup task for expired rules...")
    if stop_event_param is None:
        logging.error("cleanup_expired_rules called with None stop_event_param. Task will not run correctly.")
        return

    while not stop_event_param.is_set():
        next_check_time = time.time() + config.CLEANUP_INTERVAL_SECONDS
        try:
            logging.debug("Running cleanup check for expired rules...")
            rules_to_process_for_deletion = {}
            now_utc = datetime.now(timezone.utc)
            state_changed_in_cleanup = False

            with state_lock:
                for hostname, details in list(managed_rules.items()): 
                    if details.get("status") == "pending_deletion" and details.get("source", "docker") == "docker":
                        delete_at = details.get("delete_at")
                        is_expired = False
                        if isinstance(delete_at, datetime):
                            delete_at_utc = delete_at.astimezone(timezone.utc) if delete_at.tzinfo else delete_at.replace(tzinfo=timezone.utc)
                            if delete_at_utc <= now_utc:
                                is_expired = True
                        else: 
                            logging.warning(f"Rule {hostname} pending delete but has invalid/missing delete_at: {delete_at}. Marking for immediate deletion.")
                            is_expired = True
                        
                        if is_expired:
                            rules_to_process_for_deletion[hostname] = {
                                "zone_id": details.get("zone_id", config.CF_ZONE_ID), 
                                "access_app_id": details.get("access_app_id")
                            }
                    elif details.get("source") == "manual" and details.get("status") == "pending_deletion":
                        logging.warning(f"Manual rule {hostname} found 'pending_deletion'. Resetting to 'active'.")
                        details["status"] = "active"; details["delete_at"] = None
                        state_changed_in_cleanup = True
            
            if state_changed_in_cleanup and not rules_to_process_for_deletion: 
                save_state()

            if rules_to_process_for_deletion:
                hostnames_fully_cleaned = []
                effective_tunnel_id_cleanup = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID

                for hostname, delete_info in rules_to_process_for_deletion.items():
                    zone_id_del = delete_info["zone_id"]
                    access_app_id_del = delete_info["access_app_id"]
                    
                    dns_deleted = False
                    if zone_id_del and effective_tunnel_id_cleanup:
                        if delete_cloudflare_dns_record(zone_id_del, hostname, effective_tunnel_id_cleanup):
                            dns_deleted = True
                        else: logging.error(f"Failed DNS delete for expired rule {hostname} in zone {zone_id_del}.")
                    elif not zone_id_del: logging.warning(f"Skipping DNS delete for {hostname}: Zone ID unavailable.")
                    elif not effective_tunnel_id_cleanup: logging.warning(f"Skipping DNS delete for {hostname}: Tunnel ID unavailable.")
                    
                    access_app_deleted = False
                    if access_app_id_del:
                        if delete_cloudflare_access_application(access_app_id_del):
                            access_app_deleted = True
                        else: logging.error(f"Failed Access App delete for {hostname}, App ID: {access_app_id_del}.")
                    else: access_app_deleted = True 

                    hostnames_fully_cleaned.append(hostname)

                if hostnames_fully_cleaned:
                    config_updated_after_delete = False
                    if not config.USE_EXTERNAL_CLOUDFLARED:
                        if update_cloudflare_config(): 
                            config_updated_after_delete = True
                        else:
                            logging.error("Failed to update Cloudflare tunnel config during rule cleanup. Rules may remain in local state temporarily.")
                    else: 
                        config_updated_after_delete = True 

                    if config_updated_after_delete:
                        with state_lock:
                            deleted_count = 0
                            for hostname_rem in hostnames_fully_cleaned:
                                if hostname_rem in managed_rules and managed_rules[hostname_rem].get("status") == "pending_deletion":
                                    del managed_rules[hostname_rem]
                                    deleted_count += 1
                            if deleted_count > 0:
                                logging.info(f"Removed {deleted_count} rules from local state after cleanup.")
                                save_state()
        except Exception as e_cleanup:
            logging.error(f"Error in cleanup task loop: {e_cleanup}", exc_info=True)

        wait_duration = max(0, next_check_time - time.time())
        if not stop_event_param.is_set(): stop_event_param.wait(wait_duration)

    logging.info("Cleanup task for expired rules stopped.")