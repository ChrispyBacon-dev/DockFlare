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
# app/core/tunnel_manager.py
import copy
import logging
import json 
import time 
from app import config, docker_client 
from app import tunnel_state, cloudflared_agent_state 
from app.core import cloudflare_api
from app.core.state_manager import managed_rules, state_lock 

from docker.errors import NotFound, APIError 
import requests 

def initialize_tunnel():
    logging.info("Initializing tunnel...")
    logging.info(f"Using Cloudflare Account ID: {config.CF_ACCOUNT_ID}")
    logging.info(f"API Token available: {'Yes' if config.CF_API_TOKEN else 'No'}")
    logging.info(f"Zone ID available: {'Yes: ' + config.CF_ZONE_ID if config.CF_ZONE_ID else 'No'}")
    logging.info(f"External mode: {config.USE_EXTERNAL_CLOUDFLARED}")
    logging.info(f"External tunnel ID: {config.EXTERNAL_TUNNEL_ID}")
    
    tunnel_state["status_message"] = "Checking tunnel configuration..."
    tunnel_state["error"] = None
    
    if config.USE_EXTERNAL_CLOUDFLARED:
        logging.info("External cloudflared configuration detected.")
        if config.EXTERNAL_TUNNEL_ID:
            tunnel_id = config.EXTERNAL_TUNNEL_ID
            logging.info(f"Using external tunnel ID: {tunnel_id}")
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = None
            tunnel_state["status_message"] = "Using external tunnel to manage DNS and inbound routes."
            logging.info(f"External tunnel (ID: {tunnel_id}) initialized for DNS and routes.")
            return
        else:
            logging.warning("USE_EXTERNAL_CLOUDFLARED is true but EXTERNAL_TUNNEL_ID is not provided.")
            tunnel_state["status_message"] = "Error: External tunnel config missing tunnel ID."
            tunnel_state["error"] = "External cloudflared enabled but missing tunnel ID."
            return
    
    if not config.TUNNEL_NAME:
        logging.error("TUNNEL_NAME not provided. Required when not using external cloudflared.")
        tunnel_state["status_message"] = "Error: Missing required TUNNEL_NAME."
        tunnel_state["error"] = "TUNNEL_NAME not provided."
        return

    try:
        tunnel_id, token = cloudflare_api.find_tunnel_via_api(config.TUNNEL_NAME)

        if not tunnel_id and not tunnel_state.get("error"):
            tunnel_state["status_message"] = f"Tunnel '{config.TUNNEL_NAME}' not found. Creating..."
            tunnel_id, token = cloudflare_api.create_tunnel_via_api(config.TUNNEL_NAME)

        if tunnel_id and token:
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = token
            tunnel_state["status_message"] = "Tunnel setup complete (using API)."
            tunnel_state["error"] = None
            logging.info(f"Tunnel '{config.TUNNEL_NAME}' initialized. ID: {tunnel_id}")
        elif not tunnel_state.get("error"):
            tunnel_state["status_message"] = "Tunnel initialization failed."
            tunnel_state["error"] = "Failed to find/create tunnel or get token."
            logging.error(f"Tunnel init failed for '{config.TUNNEL_NAME}'.")
        else:
            tunnel_state["status_message"] = "Tunnel initialization failed (see error details)."
            
    except requests.exceptions.RequestException as e:
        logging.error(f"API exception during tunnel initialization for '{config.TUNNEL_NAME}': {e}")
        if not tunnel_state.get("error"): 
            tunnel_state["error"] = f"API error: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (API error)."
    except Exception as e:
        logging.error(f"Unhandled exception during tunnel initialization for '{config.TUNNEL_NAME}': {e}", exc_info=True)
        if not tunnel_state.get("error"):
            tunnel_state["error"] = f"Unexpected init error: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (unexpected error)."

def update_cloudflare_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot update CF config, tunnel ID missing in state.")
        return False

    with state_lock: 
        logging.info("Constructing desired Cloudflare tunnel configuration from managed rules...")
        desired_dockflare_rules = []
        for rule_key, rule_details in managed_rules.items():
            if rule_details.get("status") == "active":
                service_str = rule_details.get("service") 
                
                actual_hostname_for_cf = rule_details.get("hostname_for_dns")
                actual_path_for_cf = rule_details.get("path") 

                if not actual_hostname_for_cf: 
                    parts = rule_key.split('|', 1)
                    actual_hostname_for_cf = parts[0]
                    if not actual_path_for_cf and len(parts) > 1 and parts[1]: 
                         actual_path_for_cf = parts[1] 
                
                if service_str and actual_hostname_for_cf: 
                    no_tls_verify_flag = rule_details.get("no_tls_verify", False) 
                    origin_server_name_val = rule_details.get("origin_server_name")
                    rule_config = {"hostname": actual_hostname_for_cf, "service": service_str} 
                    
                    if actual_path_for_cf and actual_path_for_cf.strip(): 
                        processed_path = actual_path_for_cf.strip()
                        if not processed_path.startswith('/'):
                            processed_path = '/' + processed_path
                        if len(processed_path) > 1 and processed_path.endswith('/'):
                            processed_path = processed_path.rstrip('/')
                        rule_config["path"] = processed_path
                    
                    origin_request_settings = {}
                    if no_tls_verify_flag and isinstance(service_str, str) and \
                       (service_str.lower().startswith("http://") or service_str.lower().startswith("https://")):
                        origin_request_settings["noTLSVerify"] = True
                    elif no_tls_verify_flag:
                        logging.debug(f"Rule for {rule_key} has no_tls_verify=true, but service '{service_str}' is not HTTP/HTTPS. 'noTLSVerify' will be ignored by Cloudflare for this service type.")

                    if origin_server_name_val and isinstance(service_str, str) and \
                       (service_str.lower().startswith("http://") or service_str.lower().startswith("https://")):
                        origin_request_settings["originServerName"] = origin_server_name_val
                    elif origin_server_name_val:
                        logging.debug(f"Rule for {rule_key} has origin_server_name='{origin_server_name_val}', but service '{service_str}' is not HTTP/HTTPS. 'originServerName' might be ignored by Cloudflare for this service type or cause issues.")

                    if origin_request_settings:
                        rule_config["originRequest"] = origin_request_settings
                    
                    desired_dockflare_rules.append(rule_config)
                elif not service_str:
                    logging.warning(f"Rule {rule_key} is active but missing 'service'. Skipping.")
                elif not actual_hostname_for_cf:
                    logging.warning(f"Rule {rule_key} is active but could not determine a valid hostname for Cloudflare. Skipping.")
        
        try:
            current_api_config_ruleset = cloudflare_api.get_current_cf_config(tunnel_state["id"])
        except Exception as e:
            logging.error(f"Failed to fetch current CF config to compare: {e}")
            tunnel_state["error"] = f"Failed get tunnel config: {e}" 
            return False

        if current_api_config_ruleset is None: 
            logging.error("Failed to fetch current CF config ruleset; cannot reliably update.")
            return False
            
        current_api_ingress_rules = current_api_config_ruleset.get("ingress", [])
        preserved_api_rules = []
        catch_all_rule_template = {"service": "http_status:404"} 

        for api_rule in current_api_ingress_rules:
            api_hostname = api_rule.get("hostname")
            api_service = api_rule.get("service")
            api_path = api_rule.get("path") 

            is_catch_all = api_service == catch_all_rule_template["service"] and \
                           (api_hostname is None or api_hostname == "") and \
                           (api_path is None or api_path == "")

            is_actively_managed_by_dockflare = False
            if not is_catch_all : 
                for df_rule_key, df_rule_details in managed_rules.items():
                    df_hostname_for_cf = df_rule_details.get("hostname_for_dns")
                    df_path_for_cf = df_rule_details.get("path")
                    if not df_hostname_for_cf: 
                        parts = df_rule_key.split('|',1)
                        df_hostname_for_cf = parts[0]
                        if not df_path_for_cf and len(parts) > 1 and parts[1]:
                            df_path_for_cf = parts[1]

                    if df_rule_details.get("status") == "active" and \
                       df_hostname_for_cf == api_hostname and \
                       (df_path_for_cf or None) == (api_path or None): 
                        is_actively_managed_by_dockflare = True
                        break
            
            is_wildcard_not_actively_managed = api_hostname and '*' in api_hostname and not is_actively_managed_by_dockflare

            if is_catch_all or is_wildcard_not_actively_managed:
                if is_catch_all: logging.debug(f"Preserving API catch-all rule: {api_rule}")
                if is_wildcard_not_actively_managed: logging.debug(f"Preserving API wildcard rule (not actively managed by DockFlare): {api_rule}")
                preserved_api_rules.append(api_rule)
                continue
            
            if not is_actively_managed_by_dockflare:
                 logging.info(f"Non-DockFlare managed rule found in API (hostname: {api_hostname}, path: {api_path}, service: {api_service}). It will be removed by authoritative update.")

        final_ingress_rules_to_put = list(desired_dockflare_rules) 
        for p_rule in preserved_api_rules:
            is_duplicate = False
            p_hostname = p_rule.get("hostname")
            p_service = p_rule.get("service")
            p_path = p_rule.get("path") 
            for f_rule in final_ingress_rules_to_put:
                if f_rule.get("hostname") == p_hostname and \
                   f_rule.get("service") == p_service and \
                   (f_rule.get("path") or None) == (p_path or None):
                    is_duplicate = True
                    break
            if not is_duplicate:
                final_ingress_rules_to_put.append(p_rule)

        has_explicit_catch_all_in_final_list = any(
            r.get("service") == catch_all_rule_template["service"] and \
            (r.get("hostname") is None or r.get("hostname") == "") and \
            (r.get("path") is None or r.get("path") == "")
            for r in final_ingress_rules_to_put
        )
        if not has_explicit_catch_all_in_final_list:
            final_ingress_rules_to_put.append(catch_all_rule_template.copy()) 
            logging.info("Adding default catch-all rule as none was found/preserved from API or generated by DockFlare rules.")

        def rule_to_comparable_dict(rule):          
            comp_dict = {} 
            if rule.get("hostname") is not None: 
                 comp_dict["hostname"] = rule.get("hostname")
            comp_dict["service"] = rule.get("service") 
            path_val = rule.get("path")
            if path_val and path_val.strip():
                processed_path_comp = path_val.strip()
                if not processed_path_comp.startswith('/'):
                    processed_path_comp = '/' + processed_path_comp
                if len(processed_path_comp) > 1 and processed_path_comp.endswith('/'):
                    processed_path_comp = processed_path_comp.rstrip('/')
                comp_dict["path"] = processed_path_comp
            
            origin_request = rule.get("originRequest")
            if isinstance(origin_request, dict):
                if origin_request.get("noTLSVerify") is True:
                    comp_dict["noTLSVerify"] = True 
                if origin_request.get("originServerName"):
                    comp_dict["originServerName"] = origin_request.get("originServerName")
            return comp_dict

        current_api_comparable_set = {json.dumps(rule_to_comparable_dict(r), sort_keys=True) for r in current_api_ingress_rules}
        final_put_comparable_set = {json.dumps(rule_to_comparable_dict(r), sort_keys=True) for r in final_ingress_rules_to_put}

        needs_api_update = False
        if current_api_comparable_set != final_put_comparable_set:
            logging.info("Ingress rule configuration content differs from Cloudflare. Update required.")
            needs_api_update = True
        elif len(current_api_ingress_rules) != len(final_ingress_rules_to_put): 
            logging.info("Number of ingress rules differs from Cloudflare. Update required.")
            needs_api_update = True
        
        if not needs_api_update:
            logging.info("Cloudflare configuration content and rule count match desired state. No API update deemed necessary.")
            return True 

        logging.info(f"--- FINAL RULES TO PUT (PRE-SORT, {len(final_ingress_rules_to_put)} total) ---")
        for i, rule_to_log in enumerate(final_ingress_rules_to_put):
            logging.info(f"Pre-sort Rule {i}: {json.dumps(rule_to_log)}")
        
        actual_catch_all_rule = None
        rules_without_catch_all = []
        for r_to_sort in final_ingress_rules_to_put: 
            if r_to_sort.get("service") == catch_all_rule_template["service"] and \
               (r_to_sort.get("hostname") is None or r_to_sort.get("hostname") == "") and \
               (r_to_sort.get("path") is None or r_to_sort.get("path") == ""):
                if actual_catch_all_rule is None: 
                    actual_catch_all_rule = r_to_sort
                else:
                    logging.warning(f"Multiple catch-all like rules found: {r_to_sort} and {actual_catch_all_rule}. Using first.")
            else:
                rules_without_catch_all.append(r_to_sort)
        
        rules_without_catch_all.sort(key=lambda r_sort_key: (
            r_sort_key.get("hostname") or "\uffff", 
            0 if not r_sort_key.get("path") else 1, 
            -len(r_sort_key.get("path") or ""), 
            r_sort_key.get("path") or "" 
        ))

        final_sorted_rules_for_put = rules_without_catch_all
        if actual_catch_all_rule:
            final_sorted_rules_for_put.append(actual_catch_all_rule) 

        logging.info(f"--- FINAL RULES TO PUT (SORTED, {len(final_sorted_rules_for_put)} total) ---")
        for i, rule_to_log in enumerate(final_sorted_rules_for_put):
            logging.info(f"Sorted Rule {i}: {json.dumps(rule_to_log)}")
        
    if needs_api_update:
        endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        config_payload = {"config": {"ingress": final_sorted_rules_for_put}} 
        
        try:
            cloudflare_api.cf_api_request("PUT", endpoint, json_data=config_payload) 
            logging.info("Successfully updated Cloudflare tunnel configuration.")
            return True
        except Exception as e: 
            logging.error(f"Failed to update CF tunnel config: {e}", exc_info=True)
            tunnel_state["error"] = f"Failed update tunnel config: {e}" 
            return False
            
    return True

def get_cloudflared_container():
    if not docker_client:
        logging.debug("Docker client unavailable in get_cloudflared_container.")
        return None
    if config.USE_EXTERNAL_CLOUDFLARED:
        return None
    if not config.CLOUDFLARED_CONTAINER_NAME:
        logging.debug("CLOUDFLARED_CONTAINER_NAME is not set.")
        return None
    try:
        return docker_client.containers.get(config.CLOUDFLARED_CONTAINER_NAME)
    except NotFound:
        logging.debug(f"Agent container '{config.CLOUDFLARED_CONTAINER_NAME}' not found.")
        return None
    except APIError as e:
        logging.error(f"Docker API error getting agent container '{config.CLOUDFLARED_CONTAINER_NAME}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error get agent: {e}"
        return None
    except requests.exceptions.ConnectionError as e: 
        logging.error(f"Docker connection error getting agent container: {e}")
        cloudflared_agent_state["last_action_status"] = f"Error connect Docker: {e}"
        
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting agent container '{config.CLOUDFLARED_CONTAINER_NAME}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error unexpected get agent: {e}"
        return None

def update_cloudflared_container_status():
    global docker_client 
    current_status = cloudflared_agent_state.get("container_status")

    if not docker_client:
        if current_status != "docker_unavailable":
            logging.warning("Docker client unavailable in update_cloudflared_container_status, attempting reconnect...")
            try:
                
                import docker as docker_lib 
                docker_client = docker_lib.from_env(timeout=5)
                docker_client.ping()
                logging.info("Reconnected to Docker daemon during agent status update.")
                
            except Exception as e_reconnect:
                logging.error(f"Failed to reconnect to Docker daemon: {e_reconnect}")
                if current_status != "docker_unavailable": 
                    logging.info(f"Agent status changing to docker_unavailable.")
                    cloudflared_agent_state["container_status"] = "docker_unavailable"
                
                from app import docker_client as global_dc_ref
                if global_dc_ref is not None: 
                    logging.warning("Global docker_client was not None, but reconnect failed. This needs careful handling.")
                return 
        else: 
             return

    container = get_cloudflared_container() 
    new_status = "not_found"
    if container:
        try:
            container.reload()
            new_status = container.status
        except (NotFound, APIError) as e_reload:
            new_status = "not_found"
            logging.warning(f"Error reloading agent container status (now 'not_found'): {e_reload}")
            if cloudflared_agent_state.get("container_status") != "running": 
                 cloudflared_agent_state["last_action_status"] = "Agent container disappeared or API error."
        except requests.exceptions.ConnectionError as e_conn:
            new_status = "docker_unavailable"
            logging.error(f"Docker connection error during agent status reload: {e_conn}")
            
            from app import docker_client as global_dc_ref 

        except Exception as e_unexpected:
            logging.error(f"Unexpected error reloading agent status for {container.name}: {e_unexpected}", exc_info=True)
            
            return 
    
    if current_status != new_status:
        logging.info(f"Agent container '{config.CLOUDFLARED_CONTAINER_NAME}' status changed: {current_status} -> {new_status}")
        cloudflared_agent_state["container_status"] = new_status
        last_action = cloudflared_agent_state.get("last_action_status")
        if new_status == 'running' and last_action and last_action.startswith("Error"):
            cloudflared_agent_state["last_action_status"] = None

def ensure_docker_network_exists(network_name):
    if not docker_client:
        logging.error("Docker client unavailable, cannot check/create network.")
        return False
    if not network_name: 
        logging.error("Network name not provided to ensure_docker_network_exists.")
        return False
    try:
        docker_client.networks.get(network_name)
        logging.info(f"Docker network '{network_name}' already exists.")
        return True
    except NotFound:
        logging.info(f"Docker network '{network_name}' not found. Creating...")
        try:
            docker_client.networks.create(network_name, driver="bridge", check_duplicate=True)
            logging.info(f"Successfully created Docker network '{network_name}'.")
            return True
        except APIError as e_create:
            if "already exists" in str(e_create).lower(): # More robust check
                logging.warning(f"Network '{network_name}' creation reported conflict but NotFound was raised? Assuming it exists now.")
                return True # Race condition likely
            logging.error(f"Failed to create Docker network '{network_name}': {e_create}", exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error create net: {e_create}"
            return False
        except Exception as e_unexp_create:
            logging.error(f"Unexpected error creating Docker network '{network_name}': {e_unexp_create}", exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error: Unexpected create net: {e_unexp_create}"
            return False
    except APIError as e_get:
        logging.error(f"Docker API error checking network '{network_name}': {e_get}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error check net: {e_get}"
        return False
    except requests.exceptions.ConnectionError as e_conn:
        logging.error(f"Docker connection error checking network '{network_name}': {e_conn}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker connect check net."
        return False
    except Exception as e_unexp_get:
        logging.error(f"Unexpected error checking network '{network_name}': {e_unexp_get}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected check net: {e_unexp_get}"
        return False

def start_cloudflared_container():
    logging.info(f"Attempting to start agent container '{config.CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Starting..."
    success_flag = False
    
    if not docker_client:
        msg = "Docker client not available."
        logging.error(msg)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
        return False
    if not tunnel_state.get("token"):
        msg = "Tunnel token not available."
        logging.error(msg)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
        return False
    if not config.CLOUDFLARED_NETWORK_NAME or not ensure_docker_network_exists(config.CLOUDFLARED_NETWORK_NAME):
        logging.error(f"Failed network check/create for '{config.CLOUDFLARED_NETWORK_NAME}'. Cannot start agent.")
        
        return False

    token = tunnel_state["token"]
    container = get_cloudflared_container()
    needs_recreate = False

    if container:
        try:
            container.reload()
            logging.info(f"Found existing agent container '{container.name}' status: {container.status}")
            if container.status == 'running':
                msg = f"Agent container '{container.name}' is already running."
                logging.info(msg)
                cloudflared_agent_state["last_action_status"] = msg
                success_flag = True
                return True

            current_networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', 'default')
            
            
            is_on_correct_network = config.CLOUDFLARED_NETWORK_NAME in current_networks
            if network_mode != config.CLOUDFLARED_NETWORK_NAME and not is_on_correct_network :
                logging.warning(f"Existing agent container '{container.name}' is in network mode '{network_mode}' / not on '{config.CLOUDFLARED_NETWORK_NAME}'. Networks: {list(current_networks.keys())}. Needs recreation.")
                needs_recreate = True
            
            if needs_recreate:
                logging.info(f"Removing misconfigured/stopped agent container '{container.name}'...")
                try:
                    container.remove(force=True)
                    container = None 
                except (APIError, requests.exceptions.ConnectionError) as rm_err:
                    logging.error(f"Failed to remove misconfigured agent '{container.name}': {rm_err}. Cannot proceed.")
                    cloudflared_agent_state["last_action_status"] = f"Error: Failed remove old agent: {rm_err}"
                    return False
            else: 
                logging.info(f"Starting existing stopped agent container '{container.name}'...");
                container.start()
                msg = f"Started existing agent container '{container.name}'."
                cloudflared_agent_state["last_action_status"] = msg
                logging.info(msg)
                success_flag = True
        
        except (NotFound, APIError) as e_check:
            logging.warning(f"Error checking existing agent container '{config.CLOUDFLARED_CONTAINER_NAME}': {e_check}. Assuming creation is needed.")
            container = None 
        except requests.exceptions.ConnectionError as e_conn:
            logging.error(f"Docker connection error checking existing agent container: {e_conn}")
            cloudflared_agent_state["last_action_status"] = f"Error: Docker connect check agent."
            return False

    if not container and not success_flag: 
        logging.info(f"Agent container '{config.CLOUDFLARED_CONTAINER_NAME}' not found or needs recreation. Creating...")
        try:
            logging.info(f"Pulling image {config.CLOUDFLARED_IMAGE}...");
            docker_client.images.pull(config.CLOUDFLARED_IMAGE)
            logging.info("Image pull complete.")
        except APIError as img_err:
            logging.warning(f"Could not pull image {config.CLOUDFLARED_IMAGE}: {img_err}. Will attempt using local if available.")
        except requests.exceptions.ConnectionError as e_conn_pull:
            logging.error(f"Docker connection failed during image pull: {e_conn_pull}")
            cloudflared_agent_state["last_action_status"] = f"Error: Docker connect pull image."
            return False
        
        try:
            container_params = {
                "image": config.CLOUDFLARED_IMAGE,
                "command": f"tunnel --no-autoupdate run --token {token}",
                "name": config.CLOUDFLARED_CONTAINER_NAME,
                "network": config.CLOUDFLARED_NETWORK_NAME,
                "restart_policy": {"Name": "unless-stopped"},
                "detach": True,
                "remove": False, 
                "labels": {"managed-by": "dockflare"}
            }
            new_container = docker_client.containers.run(**container_params)
            msg = f"Successfully created and started agent container '{new_container.name}' ({new_container.id[:12]})."
            cloudflared_agent_state["last_action_status"] = msg
            logging.info(msg)
            success_flag = True
        except APIError as create_err:
            if "is already in use" in str(create_err):
                msg = f"Error: Agent container name '{config.CLOUDFLARED_CONTAINER_NAME}' conflict."
            else:
                msg = f"Docker API error creating agent container: {create_err}"
            logging.error(msg, exc_info=True)
            cloudflared_agent_state["last_action_status"] = msg
            success_flag = False
        except requests.exceptions.ConnectionError as e_conn_run:
            logging.error(f"Docker connection failed running agent container: {e_conn_run}")
            cloudflared_agent_state["last_action_status"] = f"Error: Docker connect run agent."
            success_flag = False
            
    if success_flag: 
        time.sleep(2) 
    
    update_cloudflared_container_status() 
    logging.info(f"Exiting start_cloudflared_container (Success: {success_flag}).")
    return success_flag

def stop_cloudflared_container():
    logging.info(f"Attempting to stop agent container '{config.CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Stopping..."
    success_flag = False
    
    if not docker_client:
        msg = "Docker client unavailable."
        logging.error(msg)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
        return False

    container = get_cloudflared_container()
    if not container:
        msg = f"Agent container '{config.CLOUDFLARED_CONTAINER_NAME}' not found (already stopped/removed?)."
        logging.warning(msg)
        cloudflared_agent_state["last_action_status"] = msg
        if cloudflared_agent_state["container_status"] != "not_found":
            cloudflared_agent_state["container_status"] = "not_found"
        success_flag = True
        return True

    try:
        container.reload()
        if container.status != 'running':
            msg = f"Agent container '{container.name}' is not running (status: {container.status})."
            logging.info(msg)
            cloudflared_agent_state["last_action_status"] = msg
            if cloudflared_agent_state["container_status"] != container.status:
                cloudflared_agent_state["container_status"] = container.status
            success_flag = True
            return True

        logging.info(f"Stopping running agent container '{container.name}'...");
        container.stop(timeout=30) 
        msg = f"Successfully stopped agent container '{container.name}'."
        cloudflared_agent_state["last_action_status"] = msg
        logging.info(msg)
        success_flag = True
    except (APIError, NotFound) as e_stop: 
        msg = f"Docker API error stopping agent container '{config.CLOUDFLARED_CONTAINER_NAME}': {e_stop}"
        logging.error(msg, exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
        success_flag = False
    except requests.exceptions.ConnectionError as e_conn:
        msg = f"Docker connection error stopping agent container: {e_conn}"
        logging.error(msg)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
        success_flag = False
    except Exception as e_unexp:
        msg = f"Unexpected error stopping agent container '{config.CLOUDFLARED_CONTAINER_NAME}': {e_unexp}"
        logging.error(msg, exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
        success_flag = False
    
    if success_flag: 
        time.sleep(2)

    update_cloudflared_container_status() 
    logging.info(f"Exiting stop_cloudflared_container (Success: {success_flag}).")
    return success_flag