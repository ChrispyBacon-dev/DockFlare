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
# app/core/docker_handler.py

import logging
import time
import requests
import copy 
from docker.errors import NotFound, APIError

from app import config, docker_client, cloudflared_agent_state, tunnel_state 

from app.core.state_manager import managed_rules, state_lock, save_state
from app.core.tunnel_manager import update_cloudflare_config
from app.core.cloudflare_api import create_cloudflare_dns_record, get_zone_id_from_name
from app.core.access_manager import handle_access_policy_from_labels 

def is_valid_hostname(hostname): 
    if not hostname: return False
    if hostname.startswith('*.'):
        domain_part = hostname[2:]
        if not domain_part or len(domain_part) > 253: return False
        for label in domain_part.split('.'):
            if not label or len(label) > 63: return False
            if not all(c.isalnum() or c == '-' for c in label): return False
            if label.startswith('-') or label.endswith('-'): return False
        return True
    if len(hostname) > 253: return False
    labels = hostname.split('.')
    for label in labels:
        if not label or len(label) > 63: return False
        if not all(c.isalnum() or c == '-' for c in label): return False
        if label.startswith('-') or label.endswith('-'): return False
    return True

def is_valid_service(service): 
    import re 
    if not service: return False
    return (re.match(r"^(https?|tcp|unix)://", service) or 
            re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)) is not None

def process_container_start(container_obj):
    if not container_obj:
        return

    container_id_val = None
    container_name_val = "UnknownContainer"
    logging.info(f"DOCKER_HANDLER_PROCESS_START: Initial managed_rules ID: {id(managed_rules)}, len: {len(managed_rules)} for container {getattr(container_obj, 'name', 'N/A')}")
    try:
        container_id_val = container_obj.id
        container_obj.reload() 
        container_name_val = container_obj.name
        labels = container_obj.labels
        
        enabled_label_key = f"{config.LABEL_PREFIX}.enable"
        is_enabled = labels.get(enabled_label_key, "false").lower() in ["true", "1", "t", "yes"]
        if not is_enabled:
            logging.debug(f"DOCKER_HANDLER: Ignoring start: {container_name_val} ({container_id_val[:12]}): '{enabled_label_key}' not true.")
            return

        hostnames_to_process = []
        default_access_policy_type_label = labels.get(f"{config.LABEL_PREFIX}.access.policy")
        default_access_app_name_label = labels.get(f"{config.LABEL_PREFIX}.access.name")
        default_access_session_duration_label = labels.get(f"{config.LABEL_PREFIX}.access.session_duration", "24h")
        default_access_app_launcher_visible_label = labels.get(f"{config.LABEL_PREFIX}.access.app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
        default_access_allowed_idps_label_str = labels.get(f"{config.LABEL_PREFIX}.access.allowed_idps")
        default_access_auto_redirect_label = labels.get(f"{config.LABEL_PREFIX}.access.auto_redirect_to_identity", "false").lower() in ["true", "1", "t", "yes"]
        default_access_custom_rules_label_str = labels.get(f"{config.LABEL_PREFIX}.access.custom_rules")
        hostname_label = labels.get(f"{config.LABEL_PREFIX}.hostname")
        service_label = labels.get(f"{config.LABEL_PREFIX}.service")
        zone_name_label = labels.get(f"{config.LABEL_PREFIX}.zonename")
        no_tls_verify_label = labels.get(f"{config.LABEL_PREFIX}.no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]
        if hostname_label and service_label:
            if is_valid_hostname(hostname_label) and is_valid_service(service_label):
                hostnames_to_process.append({
                    "hostname": hostname_label, "service": service_label, "zone_name": zone_name_label,
                    "no_tls_verify": no_tls_verify_label,
                    "access_policy_type": default_access_policy_type_label, "access_app_name": default_access_app_name_label,
                    "access_session_duration": default_access_session_duration_label, "access_app_launcher_visible": default_access_app_launcher_visible_label,
                    "access_allowed_idps_str": default_access_allowed_idps_label_str, "access_auto_redirect": default_access_auto_redirect_label,
                    "access_custom_rules_str": default_access_custom_rules_label_str
                })
        index = 0
        while True:
            prefix = f"{config.LABEL_PREFIX}.{index}"
            hostname_indexed = labels.get(f"{prefix}.hostname")
            if not hostname_indexed: break
            service_indexed = labels.get(f"{prefix}.service", service_label) 
            if not service_indexed: index += 1; continue
            zone_name_indexed = labels.get(f"{prefix}.zonename", zone_name_label)
            no_tls_verify_indexed_val = labels.get(f"{prefix}.no_tls_verify", str(no_tls_verify_label).lower())
            no_tls_verify_indexed = no_tls_verify_indexed_val.lower() in ["true", "1", "t", "yes"]
            access_policy_type_indexed = labels.get(f"{prefix}.access.policy", default_access_policy_type_label)
            access_app_name_indexed = labels.get(f"{prefix}.access.name", default_access_app_name_label)
            access_session_duration_indexed = labels.get(f"{prefix}.access.session_duration", default_access_session_duration_label)
            acc_launcher_val_idx = labels.get(f"{prefix}.access.app_launcher_visible", str(default_access_app_launcher_visible_label).lower())
            access_app_launcher_visible_indexed = acc_launcher_val_idx.lower() in ["true", "1", "t", "yes"]
            access_allowed_idps_indexed_str = labels.get(f"{prefix}.access.allowed_idps", default_access_allowed_idps_label_str)
            acc_redirect_val_idx = labels.get(f"{prefix}.access.auto_redirect_to_identity", str(default_access_auto_redirect_label).lower())
            access_auto_redirect_indexed = acc_redirect_val_idx.lower() in ["true", "1", "t", "yes"]
            access_custom_rules_indexed_str = labels.get(f"{prefix}.access.custom_rules", default_access_custom_rules_label_str)
            if is_valid_hostname(hostname_indexed) and is_valid_service(service_indexed):
                hostnames_to_process.append({
                    "hostname": hostname_indexed, "service": service_indexed, "zone_name": zone_name_indexed, "no_tls_verify": no_tls_verify_indexed,
                    "access_policy_type": access_policy_type_indexed, "access_app_name": access_app_name_indexed,
                    "access_session_duration": access_session_duration_indexed, "access_app_launcher_visible": access_app_launcher_visible_indexed,
                    "access_allowed_idps_str": access_allowed_idps_indexed_str, "access_auto_redirect": access_auto_redirect_indexed,
                    "access_custom_rules_str": access_custom_rules_indexed_str
                })
            index += 1
        
        if not hostnames_to_process:
            logging.warning(f"DOCKER_HANDLER: No valid hostname configs for {container_name_val} ({container_id_val[:12]}).")
            return
            
        logging.info(f"DOCKER_HANDLER: Found {len(hostnames_to_process)} hostname configurations for container {container_name_val}")
        
        state_changed_locally_for_this_container = False
        needs_tunnel_config_update_for_this_container = False

        for config_item in hostnames_to_process:
            hostname = config_item["hostname"]
            service = config_item["service"]
            zone_name_from_item = config_item["zone_name"] 
            no_tls_verify_from_item = config_item["no_tls_verify"] 
            
            target_zone_id = None
            if zone_name_from_item:
                target_zone_id = get_zone_id_from_name(zone_name_from_item) 
                if not target_zone_id:
                    logging.error(f"DOCKER_HANDLER: Failed Zone ID lookup for '{zone_name_from_item}' (hostname {hostname}). Skipping.")
                    continue
            elif config.CF_ZONE_ID:
                target_zone_id = config.CF_ZONE_ID
            else: 
                logging.error(f"DOCKER_HANDLER: No Zone ID for {hostname}. Skipping.")
                continue
            
            logging.info(f"DOCKER_HANDLER_LOOP_ITEM: For {hostname}. Before lock, managed_rules ID {id(managed_rules)}, len {len(managed_rules)}")
            with state_lock: 
                existing_rule = managed_rules.get(hostname) 
                
                if existing_rule and existing_rule.get("source") == "manual":
                    logging.info(f"DOCKER_HANDLER: Hostname {hostname} is manual, skipping for {container_name_val}.")
                    continue

                original_existing_rule_for_comparison = copy.deepcopy(existing_rule) if existing_rule else None
                
                if existing_rule:
                    logging.info(f"DOCKER_HANDLER_UPD_RULE_PRE: Updating rule for {hostname}. Current: {existing_rule}")
                    
                    rule_data_changed = False
                    if existing_rule.get("service") != service: existing_rule["service"] = service; rule_data_changed = True
                    if existing_rule.get("container_id") != container_id_val: existing_rule["container_id"] = container_id_val 
                    if existing_rule.get("zone_id") != target_zone_id: existing_rule["zone_id"] = target_zone_id; rule_data_changed = True
                    if existing_rule.get("no_tls_verify") != no_tls_verify_from_item: existing_rule["no_tls_verify"] = no_tls_verify_from_item; rule_data_changed = True
                    
                    existing_rule["source"] = "docker" # Ensure source is set

                    if existing_rule.get("status") == "pending_deletion":
                        existing_rule["status"] = "active"
                        existing_rule["delete_at"] = None
                        rule_data_changed = True 
                    
                    if rule_data_changed:
                        needs_tunnel_config_update_for_this_container = True
                    
                    if original_existing_rule_for_comparison != existing_rule:
                         state_changed_locally_for_this_container = True
                    logging.info(f"DOCKER_HANDLER_UPD_RULE_POST: For {hostname}. Rule: {existing_rule}. state_changed: {state_changed_locally_for_this_container}, tunnel_update: {needs_tunnel_config_update_for_this_container}")

                else: 
                    logging.info(f"DOCKER_HANDLER_NEW_RULE_PRE: Adding NEW rule for {hostname}. managed_rules ID before add: {id(managed_rules)}")
                    managed_rules[hostname] = {
                        "service": service, "container_id": container_id_val,
                        "status": "active", "delete_at": None, "zone_id": target_zone_id,
                        "no_tls_verify": no_tls_verify_from_item,
                        "access_app_id": None, "access_policy_type": None, 
                        "access_app_config_hash": None, "access_policy_ui_override": False,
                        "source": "docker"
                    }
                    existing_rule = managed_rules[hostname] 
                    state_changed_locally_for_this_container = True
                    needs_tunnel_config_update_for_this_container = True
                    logging.info(f"DOCKER_HANDLER_NEW_RULE_POST: Added {hostname}. managed_rules ID after add: {id(managed_rules)}, len: {len(managed_rules)}. Rule: {existing_rule}")
                
                if existing_rule: 
                    if existing_rule.get("access_policy_ui_override", False):
                        logging.info(f"DOCKER_HANDLER: Access policy for {hostname} is UI-managed. Skipping.")
                    else:
                        if handle_access_policy_from_labels(config_item, existing_rule, None): 
                            state_changed_locally_for_this_container = True 
                            logging.info(f"DOCKER_HANDLER_ACCESS_MOD: Access policy for {hostname} changed. state_changed: {state_changed_locally_for_this_container}. managed_rules ID {id(managed_rules)}, len {len(managed_rules)}")
            
        logging.info(f"DOCKER_HANDLER_END_CONTAINER_LOOP: For {container_name_val}. state_changed={state_changed_locally_for_this_container}, tunnel_update={needs_tunnel_config_update_for_this_container}. managed_rules ID {id(managed_rules)}, len {len(managed_rules)}")
            
        if state_changed_locally_for_this_container:
            logging.info(f"DOCKER_HANDLER_PRE_SAVE: For container {container_name_val}. managed_rules ID {id(managed_rules)}, len {len(managed_rules)}")
            save_state() 
        else:
            logging.info(f"DOCKER_HANDLER: No local state changes for {container_name_val}. Skipping save_state().")

        if needs_tunnel_config_update_for_this_container:
            logging.info(f"DOCKER_HANDLER: Triggering tunnel config update for {container_name_val}.")
            if update_cloudflare_config(): 
                logging.info(f"DOCKER_HANDLER: Tunnel config update successful for container {container_name_val}.")
                effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
                if effective_tunnel_id:
                    for config_item_dns in hostnames_to_process: 
                        hostname_dns = config_item_dns["hostname"]
                        zone_name_dns_item = config_item_dns["zone_name"]
                        target_zone_id_for_dns_item = get_zone_id_from_name(zone_name_dns_item) if zone_name_dns_item else config.CF_ZONE_ID
                        if managed_rules.get(hostname_dns, {}).get("source") == "manual": continue 
                        if target_zone_id_for_dns_item:
                            dns_record_id_status = create_cloudflare_dns_record(target_zone_id_for_dns_item, hostname_dns, effective_tunnel_id)
                            if dns_record_id_status and dns_record_id_status not in ["semaphore_timeout", "existing_record_unconfirmed"]:
                                logging.info(f"DOCKER_HANDLER: DNS for {hostname_dns} in zone {target_zone_id_for_dns_item} OK (ID/Status: {dns_record_id_status}).")
                            elif not dns_record_id_status: 
                                logging.error(f"DOCKER_HANDLER: CRITICAL - Failed DNS for {hostname_dns} in zone {target_zone_id_for_dns_item}!")
                                if cloudflared_agent_state: cloudflared_agent_state["last_action_status"] = f"Error: Failed DNS for {hostname_dns}."
                        else:
                            logging.error(f"DOCKER_HANDLER: Missing Zone ID for DNS for {hostname_dns} - cannot manage record.")
                else:
                    logging.error(f"DOCKER_HANDLER: Missing effective Tunnel ID - cannot manage DNS records for {container_name_val}.")
            else:
                logging.error(f"DOCKER_HANDLER: Failed to update Cloudflare tunnel config for {container_name_val}. DNS records not managed.")

    except NotFound:
        logging.warning(f"DOCKER_HANDLER: Container {container_name_val} ({container_id_val[:12] if container_id_val else 'UnknownID'}) not found.")
    except APIError as e:
        logging.error(f"DOCKER_HANDLER: Docker API error for {container_name_val}: {e}", exc_info=True)
    except requests.exceptions.ConnectionError as e: 
        logging.error(f"DOCKER_HANDLER: Docker connection error for {container_name_val}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"DOCKER_HANDLER: Unexpected error for {container_name_val}: {e}", exc_info=True)

def schedule_container_stop(container_id_val):
    from datetime import datetime, timedelta, timezone 
    if not container_id_val: return
    logging.info(f"Processing stop event for container {container_id_val[:12]}.")
    
    state_changed_after_stop_processing = False 
    with state_lock: 
        hostnames_affected_by_stop = []
        for hn, details in managed_rules.items(): 
            if details.get("container_id") == container_id_val and \
               details.get("status") == "active" and \
               details.get("source", "docker") == "docker":
                hostnames_affected_by_stop.append(hn)
        
        if hostnames_affected_by_stop:
            for hostname_to_schedule in hostnames_affected_by_stop:
                rule = managed_rules[hostname_to_schedule]
                if rule.get("status") != "pending_deletion": 
                    rule["status"] = "pending_deletion"
                    grace_delta = timedelta(seconds=config.GRACE_PERIOD_SECONDS)
                    rule["delete_at"] = datetime.now(timezone.utc) + grace_delta
                    logging.info(f"Rule for {hostname_to_schedule} (from stopped container {container_id_val[:12]}) scheduled for deletion at {rule['delete_at'].isoformat()}")
                    state_changed_after_stop_processing = True
                else:
                    logging.info(f"Rule for {hostname_to_schedule} from stopped container {container_id_val[:12]} was already pending deletion.")
        else:
            logging.info(f"Stop event for {container_id_val[:12]}, but it didn't manage any active Docker-sourced rules currently in 'active' state.")

        if state_changed_after_stop_processing:
            save_state() 

def docker_event_listener(stop_event_param): 
    if not docker_client:
        logging.error("Docker client unavailable, event listener cannot start.")
        return

    logging.info("Starting Docker event listener...")
    error_count = 0
    max_errors = 5
        
    if stop_event_param is None:
        logging.error("docker_event_listener called with None stop_event_param. Listener will not run correctly.")
        return 

    while not stop_event_param.is_set() and error_count < max_errors:
        try:
            logging.info("Connecting to Docker event stream...")
            events = docker_client.events(decode=True, since=int(time.time()))
            logging.info("Successfully connected to Docker event stream.")
            error_count = 0 

            for event in events:
                if stop_event_param.is_set():
                    logging.info("Stop event received in listener, exiting loop.")
                    break

                ev_type = event.get("Type")
                action = event.get("Action")
                actor = event.get("Actor", {})
                cont_id = actor.get("ID")
                
                logging.debug(f"Docker Event: Type={ev_type}, Action={action}, ID={cont_id[:12] if cont_id else 'N/A'}")

                if ev_type == "container" and cont_id:
                    if action == "start":
                        container_instance = None
                        for attempt in range(3): 
                            try:
                                container_instance = docker_client.containers.get(cont_id)
                                if attempt == 0 and not container_instance.labels.get(f"{config.LABEL_PREFIX}.enable"):
                                     time.sleep(0.2) 
                                     container_instance.reload()
                                if container_instance.labels.get(f"{config.LABEL_PREFIX}.hostname") or container_instance.labels.get(f"{config.LABEL_PREFIX}.0.hostname"): 
                                    logging.debug(f"Container {cont_id[:12]} details retrieved on attempt {attempt+1}.")
                                    break 
                                else:
                                    logging.debug(f"Container {cont_id[:12]} found but key labels missing, retrying ({attempt+1}/3)...")
                            except NotFound:
                                logging.debug(f"Container {cont_id[:12]} not found on attempt {attempt+1}, retrying...")
                            except APIError as e_get_cont:
                                logging.error(f"Docker API error getting container {cont_id[:12]} on attempt {attempt+1}: {e_get_cont}")
                                break 
                            except requests.exceptions.ConnectionError as e_conn_cont:
                                logging.error(f"Docker connection error getting container {cont_id[:12]}: {e_conn_cont}")
                                raise 
                            except Exception as e_unexp_cont:
                                logging.error(f"Unexpected error getting container {cont_id[:12]} details: {e_unexp_cont}", exc_info=True)
                                break 
                            
                            if attempt < 2: time.sleep(0.2 * (attempt + 1)) 
                            else: logging.warning(f"Failed to get container {cont_id[:12]} details or key labels after multiple attempts.")
                        
                        if container_instance:
                            try:
                                process_container_start(container_instance)
                            except Exception as e_proc_start: 
                                logging.error(f"Error processing start event for {cont_id[:12]}: {e_proc_start}", exc_info=True)
                        
                    elif action in ["stop", "die", "destroy", "kill"]: 
                        try:
                            schedule_container_stop(cont_id)
                        except Exception as e_proc_stop: 
                            logging.error(f"Error processing stop/die/destroy/kill event for {cont_id[:12]}: {e_proc_stop}", exc_info=True)
        
        except requests.exceptions.ConnectionError as e_conn_stream: 
            error_count += 1
            logging.error(f"Docker listener connection error: {e_conn_stream}. Reconnecting ({error_count}/{max_errors})...")
            if not stop_event_param.is_set(): stop_event_param.wait(min(30, 2 * error_count)) 
        except APIError as e_api_stream:
            error_count += 1
            logging.error(f"Docker listener API error: {e_api_stream}. Reconnecting ({error_count}/{max_errors})...")
            if not stop_event_param.is_set(): stop_event_param.wait(min(30, 2 * error_count))
        except Exception as e_unexp_stream:
            error_count += 1
            logging.error(f"Unexpected error in Docker event listener: {e_unexp_stream}. Reconnecting ({error_count}/{max_errors})...", exc_info=True)
            if not stop_event_param.is_set(): stop_event_param.wait(min(30, 2 * error_count))

        if stop_event_param.is_set():
            break 

    if error_count >= max_errors:
        logging.error("Docker event listener stopping after multiple consecutive errors.")
    logging.info("Docker event listener stopped.")