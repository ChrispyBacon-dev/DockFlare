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
from app.core.utils import get_rule_key, get_label

def _get_hostname_configs_from_container(container_obj):
    labels = container_obj.labels
    container_id_val = container_obj.id
    container_name_val = container_obj.name
    
    hostnames_configs = []

    default_path_label = get_label(labels, "path")
    default_originsrvname_label = get_label(labels, "originsrvname")
    default_http_host_header_label = get_label(labels, "httpHostHeader")

    default_access_group = get_label(labels, "access.group")
    default_access_policy_type = get_label(labels, "access.policy")
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
        if not h_idx: break
        
        s_idx = get_label(labels, f"{idx}.service", s_main)
        if not s_idx: 
            idx += 1; continue
            
        path_idx = get_label(labels, f"{idx}.path", default_path_label) 
        zn_idx = get_label(labels, f"{idx}.zonename", zn_main)
        ntv_idx_str = get_label(labels, f"{idx}.no_tls_verify", ntv_main_str) 
        ntv_idx = ntv_idx_str.lower() in ["true", "1", "t", "yes"]
        osn_idx_val = get_label(labels, f"{idx}.originsrvname", default_originsrvname_label)
        h_h_h_idx_val = get_label(labels, f"{idx}.httpHostHeader", default_http_host_header_label)

        acc_group_idx = get_label(labels, f"{idx}.access.group", default_access_group)
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
        
        running_labeled_rules_details = {}
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
            logging.error(f"[Reconcile] Error in container scanning phase: {e_phase1}", exc_info=True)
            current_app.reconciliation_info["status"] = f"Container scan error: {str(e_phase1)}"
            
        current_app.reconciliation_info["status"] = "Comparing state and reconciling cloud resources..."
        current_app.reconciliation_info["total_items"] = len(running_labeled_rules_details) + len(managed_rules) 
        current_app.reconciliation_info["processed_items"] = 0 
        processed_reconcile_items = 0
        hostnames_requiring_dns_setup = set()

        with state_lock:
            now_utc = datetime.now(timezone.utc)
            current_managed_rule_keys_in_state = set(managed_rules.keys())
                            
            for rule_key, desired_details in running_labeled_rules_details.items():
                processed_reconcile_items +=1
                current_app.reconciliation_info["processed_items"] = processed_reconcile_items
                current_app.reconciliation_info["progress"] = min(100, int((processed_reconcile_items / current_app.reconciliation_info["total_items"]) * 100)) if current_app.reconciliation_info["total_items"] > 0 else 0
                current_app.reconciliation_info["status"] = f"Reconciling (active): {rule_key}"

                if time.time() - reconciliation_start_time > max_total_time - 30: break

                existing_rule = managed_rules.get(rule_key)
                if existing_rule and existing_rule.get("source") == "manual":
                    continue

                target_zone_id = get_zone_id_from_name(desired_details["zone_name"]) if desired_details["zone_name"] else config.CF_ZONE_ID
                if not target_zone_id:
                    logging.error(f"[Reconcile] No zone ID for {rule_key}, skipping its reconciliation.")
                    continue
                
                if not existing_rule:
                    managed_rules[rule_key] = {
                        "hostname": desired_details["hostname"],
                        "path": desired_details.get("path"),
                        "service": desired_details["service"], 
                        "container_id": desired_details["container_id"],
                        "status": "active", "delete_at": None, "zone_id": target_zone_id,
                        "no_tls_verify": desired_details["no_tls_verify"],
                        "origin_server_name": desired_details.get("origin_server_name"),
                        "http_host_header": desired_details.get("http_host_header"),
                        "access_app_id": None, "access_policy_type": None, "access_app_config_hash": None,
                        "access_policy_ui_override": False, "source": "docker",
                        "access_group_id": None
                    }
                    existing_rule = managed_rules[rule_key]
                    state_changed_locally = True
                    needs_tunnel_config_update = True
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
                    if existing_rule.get("path") != desired_details.get("path"):
                        existing_rule["path"] = desired_details.get("path"); changed_in_reconcile = True; needs_tunnel_config_update = True
                    if existing_rule.get("origin_server_name") != desired_details.get("origin_server_name"):
                        existing_rule["origin_server_name"] = desired_details.get("origin_server_name"); changed_in_reconcile = True; needs_tunnel_config_update = True
                    if existing_rule.get("http_host_header") != desired_details.get("http_host_header"):
                        existing_rule["http_host_header"] = desired_details.get("http_host_header"); changed_in_reconcile = True; needs_tunnel_config_update = True

                    existing_rule["source"] = "docker" 
                    if changed_in_reconcile: state_changed_locally = True
                
                hostnames_requiring_dns_setup.add((desired_details["hostname"], target_zone_id))
                
                if existing_rule.get("access_policy_ui_override", False):
                    pass 
                else:
                    if handle_access_policy_from_labels(desired_details, existing_rule, desired_details["hostname"]):
                        state_changed_locally = True
            
            rule_keys_in_state_but_not_running = list(current_managed_rule_keys_in_state - set(running_labeled_rules_details.keys()))
            for rule_key_to_check in rule_keys_in_state_but_not_running:
                processed_reconcile_items +=1 
                current_app.reconciliation_info["processed_items"] = processed_reconcile_items
                            
                if time.time() - reconciliation_start_time > max_total_time - 20: break
                
                rule = managed_rules.get(rule_key_to_check)
                if rule and rule.get("status") == "active" and rule.get("source", "docker") == "docker":
                    logging.info(f"[Reconcile] Docker-managed rule {rule_key_to_check} active but container/labels gone. Marking for deletion.")
                    rule["status"] = "pending_deletion"
                    rule["delete_at"] = now_utc + timedelta(seconds=config.GRACE_PERIOD_SECONDS)
                    state_changed_locally = True
                elif rule and rule.get("source") == "manual" and rule.get("zone_id") and rule.get("hostname"):
                     hostnames_requiring_dns_setup.add((rule.get("hostname"), rule.get("zone_id")))

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
            unique_dns_setups = list(hostnames_requiring_dns_setup)
            dns_total = len(unique_dns_setups)
            current_app.reconciliation_info["status"] = f"Setting up DNS for {dns_total} hostnames..."
            dns_processed_count = 0
            effective_tunnel_id_for_dns = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
            
            if effective_tunnel_id_for_dns:
                logging.info(f"[Reconcile] Unique hostnames for DNS setup/check: {len(unique_dns_setups)}")
                for hostname_dns, zone_id_dns in unique_dns_setups:
                    dns_processed_count +=1 
                    current_app.reconciliation_info["status"] = f"DNS for {hostname_dns} ({dns_processed_count}/{dns_total})"
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
            rules_to_delete_keys = []
            now_utc = datetime.now(timezone.utc)
            state_changed_in_cleanup = False

            with state_lock:
                for rule_key, details in managed_rules.items():
                    if details.get("status") == "pending_deletion" and details.get("source", "docker") == "docker":
                        delete_at = details.get("delete_at")
                        if isinstance(delete_at, datetime):
                            delete_at_utc = delete_at.astimezone(timezone.utc) if delete_at.tzinfo else delete_at.replace(tzinfo=timezone.utc)
                            if delete_at_utc <= now_utc:
                                rules_to_delete_keys.append(rule_key)
                        else:
                            logging.warning(f"Rule {rule_key} pending delete but has invalid/missing delete_at. Marking for immediate deletion.")
                            rules_to_delete_keys.append(rule_key)
                
                for rule_key, details in managed_rules.items():
                    if details.get("source") == "manual" and details.get("status") == "pending_deletion":
                        logging.warning(f"Manual rule {rule_key} found 'pending_deletion'. Resetting to 'active'.")
                        details["status"] = "active"
                        details["delete_at"] = None
                        state_changed_in_cleanup = True
            
            if state_changed_in_cleanup and not rules_to_delete_keys:
                save_state()

            if rules_to_delete_keys:
                logging.info(f"Found {len(rules_to_delete_keys)} expired rules to process: {rules_to_delete_keys}")
                effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID

                rules_being_deleted = {}
                with state_lock:
                    for key in rules_to_delete_keys:
                        if key in managed_rules:
                            rules_being_deleted[key] = managed_rules[key]

                for rule_key, delete_info in rules_being_deleted.items():
                    hostname_del = delete_info.get("hostname")
                    access_app_id_del = delete_info.get("access_app_id")

                    is_hostname_still_used = any(
                        k not in rules_to_delete_keys and r.get("hostname") == hostname_del
                        for k, r in managed_rules.items()
                    )
                    
                    if hostname_del and not is_hostname_still_used:
                        logging.info(f"Hostname '{hostname_del}' is no longer used. Deleting its DNS record.")
                        delete_cloudflare_dns_record(delete_info.get("zone_id"), hostname_del, effective_tunnel_id)
                    elif hostname_del:
                        logging.info(f"Skipping DNS delete for '{hostname_del}' as it is still used by other rules.")
                    
                    is_app_id_still_used = any(
                        k not in rules_to_delete_keys and r.get("access_app_id") == access_app_id_del
                        for k, r in managed_rules.items()
                    )
                    
                    if access_app_id_del and not is_app_id_still_used:
                        logging.info(f"Access App ID '{access_app_id_del}' is no longer used. Deleting it.")
                        delete_cloudflare_access_application(access_app_id_del)
                    elif access_app_id_del:
                        logging.info(f"Skipping Access App delete for '{access_app_id_del}' as it is still used by other rules.")

                config_updated = False
                if not config.USE_EXTERNAL_CLOUDFLARED:
                    logging.info("Updating Cloudflare config to remove expired ingress rules...")
                    if update_cloudflare_config():
                        config_updated = True
                    else:
                        logging.error("Failed to update Cloudflare tunnel config during rule cleanup. Rules will remain in local state temporarily.")
                else:
                    config_updated = True

                if config_updated:
                    with state_lock:
                        deleted_count = 0
                        for key in rules_to_delete_keys:
                            if key in managed_rules:
                                del managed_rules[key]
                                deleted_count += 1
                        if deleted_count > 0:
                            logging.info(f"Removed {deleted_count} expired rules from local state.")
                            save_state()
                            
        except Exception as e_cleanup:
            logging.error(f"Error in cleanup task loop: {e_cleanup}", exc_info=True)

        wait_duration = max(0, next_check_time - time.time())
        if not stop_event_param.is_set():
            stop_event_param.wait(wait_duration)

    logging.info("Cleanup task for expired rules stopped.")