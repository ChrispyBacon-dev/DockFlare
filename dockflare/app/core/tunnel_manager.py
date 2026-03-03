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
# dockflare/app/core/tunnel_manager.py
import copy
import logging
import json 
import time 
from flask import current_app
from app import config, docker_client
from app import tunnel_state, cloudflared_agent_state 
from app.core import cloudflare_api
from app.core.state_manager import managed_rules, state_lock, list_agents, get_agent_rules 

from docker.errors import NotFound, APIError 
import requests 

def initialize_tunnel():
    from app import app
    with app.app_context():
        logging.info("Initializing tunnel...")
        cf_account_id = current_app.config.get('CF_ACCOUNT_ID')
        cf_api_token = current_app.config.get('CF_API_TOKEN')
        cf_zone_id = current_app.config.get('CF_ZONE_ID')
        tunnel_name = current_app.config.get('TUNNEL_NAME')

        logging.info(f"Using Cloudflare Account ID: {cf_account_id}")
        logging.info(f"API Token available: {'Yes' if cf_api_token else 'No'}")
        logging.info(f"Zone ID available: {'Yes: ' + cf_zone_id if cf_zone_id else 'No'}")
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
                tunnel_state["name"] = tunnel_name or "External Tunnel"
                tunnel_state["token"] = None
                tunnel_state["status_message"] = "Using external tunnel to manage DNS and inbound routes."
                logging.info(f"External tunnel (ID: {tunnel_id}) initialized for DNS and routes.")

                # Update tunnel names for existing rules after tunnel initialization
                try:
                    from app.core.state_manager import update_tunnel_names_after_initialization
                    update_tunnel_names_after_initialization()
                except Exception as e:
                    logging.warning(f"Failed to update tunnel names after initialization: {e}")
                return
            else:
                logging.warning("USE_EXTERNAL_CLOUDFLARED is true but EXTERNAL_TUNNEL_ID is not provided.")
                tunnel_state["status_message"] = "Error: External tunnel config missing tunnel ID."
                tunnel_state["error"] = "External cloudflared enabled but missing tunnel ID."
                return
        
        if not tunnel_name:
            logging.error("TUNNEL_NAME not provided. Required when not using external cloudflared.")
            tunnel_state["status_message"] = "Error: Missing required TUNNEL_NAME."
            tunnel_state["error"] = "TUNNEL_NAME not provided."
            return

        try:
            tunnel_id, token = cloudflare_api.find_tunnel_via_api(tunnel_name)

            if not tunnel_id and not tunnel_state.get("error"):
                tunnel_state["status_message"] = f"Tunnel '{tunnel_name}' not found. Creating..."
                tunnel_id, token = cloudflare_api.create_tunnel_via_api(tunnel_name)

            if tunnel_id and token:
                tunnel_state["id"] = tunnel_id
                tunnel_state["name"] = tunnel_name
                tunnel_state["token"] = token
                tunnel_state["status_message"] = "Tunnel setup complete (using API)."
                tunnel_state["error"] = None
                logging.info(f"Tunnel '{tunnel_name}' initialized. ID: {tunnel_id}")

                # Update tunnel names for existing rules after tunnel initialization
                try:
                    from app.core.state_manager import update_tunnel_names_after_initialization
                    update_tunnel_names_after_initialization()
                except Exception as e:
                    logging.warning(f"Failed to update tunnel names after initialization: {e}")
            elif not tunnel_state.get("error"):
                tunnel_state["status_message"] = "Tunnel initialization failed."
                tunnel_state["error"] = "Failed to find/create tunnel or get token."
                logging.error(f"Tunnel init failed for '{tunnel_name}'.")
            else:
                tunnel_state["status_message"] = "Tunnel initialization failed (see error details)."
                
        except requests.exceptions.RequestException as e:
            logging.error(f"API exception during tunnel initialization for '{tunnel_name}': {e}")
            if not tunnel_state.get("error"):
                tunnel_state["error"] = f"API error: {e}"
            tunnel_state["status_message"] = "Tunnel initialization failed (API error)."
        except Exception as e:
            logging.error(f"Unhandled exception during tunnel initialization for '{tunnel_name}': {e}", exc_info=True)
            if not tunnel_state.get("error"):
                tunnel_state["error"] = f"Unexpected init error: {e}"
            tunnel_state["status_message"] = "Tunnel initialization failed (unexpected error)."


def update_cloudflare_config(target_tunnel_id=None):
    from app import app
    with app.app_context():
        master_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
        if target_tunnel_id is None:
            target_tunnel_id = master_tunnel_id

        if not target_tunnel_id:
            logging.warning("Cannot update CF config, tunnel ID missing in state for target.")
            return False

        logging.info(f"Preparing Cloudflare config update for tunnel {target_tunnel_id}")

        desired_ingress = _build_ingress_entries_for_tunnel(target_tunnel_id, master_tunnel_id)

        try:
            current_api_config_ruleset = cloudflare_api.get_current_cf_config(target_tunnel_id)
        except Exception as exc:
            logging.error(f"Failed to fetch current CF config for tunnel {target_tunnel_id}: {exc}")
            if target_tunnel_id == master_tunnel_id:
                tunnel_state["error"] = f"Failed get tunnel config: {exc}"
            return False

        if current_api_config_ruleset is None:
            logging.error(f"Cloudflare returned no config for tunnel {target_tunnel_id}.")
            return False

        current_api_ingress_rules = current_api_config_ruleset.get("ingress", []) or []
        desired_comparable = {_ingress_to_comparable(rule) for rule in desired_ingress}
        preserved_rules = []

        for api_rule in current_api_ingress_rules:
            if _is_catch_all_rule(api_rule):
                preserved_rules.append(api_rule)
                continue
            hostname = api_rule.get("hostname") or ""
            if "*" in hostname:
                comp = _ingress_to_comparable(api_rule)
                if comp not in desired_comparable:
                    preserved_rules.append(api_rule)

        if config.PRESERVE_UNMANAGED_CF_INGRESS_FIELDS:
            final_ingress = [_merge_desired_with_current_fields(rule, current_api_ingress_rules) for rule in desired_ingress]
        else:
            final_ingress = list(desired_ingress)
        seen = set(desired_comparable)
        for preserved in preserved_rules:
            comp = _ingress_to_comparable(preserved)
            if comp not in seen:
                final_ingress.append(preserved)
                seen.add(comp)

        if not any(_is_catch_all_rule(rule) for rule in final_ingress):
            final_ingress.append({"service": "http_status:404"})

        final_comparable = {_ingress_to_comparable(rule) for rule in final_ingress}
        current_comparable = {_ingress_to_comparable(rule) for rule in current_api_ingress_rules}

        if current_comparable == final_comparable and len(current_api_ingress_rules) == len(final_ingress):
            logging.info(f"Tunnel {target_tunnel_id}: Cloudflare ingress already up to date.")
            return True

        logging.info(f"Tunnel {target_tunnel_id}: Updating Cloudflare ingress with {len(final_ingress)} entries (desired {len(desired_ingress)}, preserved {len(preserved_rules)})")

        try:
            account_id = current_app.config.get('CF_ACCOUNT_ID')
            endpoint = f"/accounts/{account_id}/cfd_tunnel/{target_tunnel_id}/configurations"
            cloudflare_api.cf_api_request("PUT", endpoint, json_data={"config": {"ingress": final_ingress}})
            return True
        except Exception as exc:
            logging.error(f"Failed to update Cloudflare config for tunnel {target_tunnel_id}: {exc}", exc_info=True)
            if target_tunnel_id == master_tunnel_id:
                tunnel_state["error"] = f"Failed to set tunnel config: {exc}"
            return False


def _build_ingress_entries_for_tunnel(target_tunnel_id, master_tunnel_id):
    entries = []
    with state_lock:
        for rule_key, rule_details in managed_rules.items():
            if rule_details.get("status") != "active":
                continue
            if not _rule_applies_to_tunnel(rule_details, target_tunnel_id, master_tunnel_id):
                continue
            entry = _build_ingress_entry_from_rule(rule_details)
            if entry:
                entries.append(entry)
    if target_tunnel_id:
        agents_map = list_agents()
        for agent_id, agent_details in agents_map.items():
            if agent_details.get("assigned_tunnel_id") != target_tunnel_id:
                continue
            agent_rules = get_agent_rules(agent_id)
            for rule_details in agent_rules.values():
                if rule_details.get("status") != "active":
                    continue
                entry = _build_ingress_entry_from_rule(rule_details)
                if entry:
                    entries.append(entry)
    entries.append({"service": "http_status:404"})
    unique_entries = []
    seen = set()
    for entry in entries:
        comp = _ingress_to_comparable(entry)
        if comp in seen:
            continue
        seen.add(comp)
        unique_entries.append(entry)
    return unique_entries


def _rule_applies_to_tunnel(rule_details, target_tunnel_id, master_tunnel_id):
    source = rule_details.get("source")
    rule_tunnel_id = rule_details.get("tunnel_id")
    if source == "manual":
        effective_tunnel = rule_tunnel_id or master_tunnel_id
        return effective_tunnel == target_tunnel_id
    if source == "docker":
        return target_tunnel_id == master_tunnel_id
    if source == "agent":
        if not rule_tunnel_id:
            return False
        return rule_tunnel_id == target_tunnel_id
    return target_tunnel_id == master_tunnel_id


def _build_ingress_entry_from_rule(rule_details):
    service_str = rule_details.get("service")
    if not service_str:
        return None
    entry = {"service": service_str}
    hostname = rule_details.get("hostname")
    if hostname:
        entry["hostname"] = hostname
    normalized_path = _normalize_path_for_ingress(rule_details.get("path"))
    if normalized_path:
        entry["path"] = normalized_path

    origin_request = {}
    if _service_supports_origin_request(service_str):
        if rule_details.get("no_tls_verify"):
            origin_request["noTLSVerify"] = True
        origin_server_name = rule_details.get("origin_server_name") or rule_details.get("originServerName")
        if origin_server_name:
            origin_request["originServerName"] = origin_server_name
        http_host_header = rule_details.get("http_host_header") or rule_details.get("httpHostHeader")
        if http_host_header:
            origin_request["httpHostHeader"] = http_host_header
        if rule_details.get("http2_origin"):
            origin_request["http2Origin"] = True
        if rule_details.get("disable_chunked_encoding"):
            origin_request["disableChunkedEncoding"] = True
        if rule_details.get("match_sni_to_host"):
            origin_request["matchSNIToHost"] = True
    if origin_request:
        entry["originRequest"] = origin_request
    return entry


def _normalize_path_for_ingress(path_value):
    if not path_value:
        return None
    path_str = str(path_value).strip()
    if not path_str:
        return None
    if not path_str.startswith('/'):
        path_str = '/' + path_str
    if len(path_str) > 1 and path_str.endswith('/'):
        path_str = path_str.rstrip('/')
    return path_str


def _service_supports_origin_request(service_str):
    if not isinstance(service_str, str):
        return False
    lower = service_str.lower()
    return lower.startswith("http://") or lower.startswith("https://")


def _ingress_to_comparable(rule):
    hostname = rule.get("hostname") or ""
    service = rule.get("service") or ""
    path = rule.get("path")
    if path is not None:
        path = _normalize_path_for_ingress(path)
    path = path or ""
    origin = rule.get("originRequest") or {}
    if not isinstance(origin, dict):
        origin = {}
    no_tls = bool(origin.get("noTLSVerify"))
    origin_name = origin.get("originServerName") or ""
    http_host = origin.get("httpHostHeader") or ""
    http2_origin = bool(origin.get("http2Origin"))
    disable_chunked = bool(origin.get("disableChunkedEncoding"))
    match_sni_to_host = bool(origin.get("matchSNIToHost"))
    return (hostname, service, path, no_tls, origin_name, http_host, http2_origin, disable_chunked, match_sni_to_host)


def _is_catch_all_rule(rule):
    service = rule.get("service")
    hostname = rule.get("hostname")
    path = rule.get("path")
    return service == "http_status:404" and not hostname and not path


def _ingress_identity_key(rule):
    hostname = rule.get("hostname") or ""
    service = rule.get("service") or ""
    path = _normalize_path_for_ingress(rule.get("path")) or ""
    return (hostname, service, path)


def _merge_desired_with_current_fields(desired_rule, current_rules):
    desired_identity = _ingress_identity_key(desired_rule)
    matching_current = None
    for current_rule in current_rules:
        if _ingress_identity_key(current_rule) == desired_identity:
            matching_current = current_rule
            break
    if not isinstance(matching_current, dict):
        return desired_rule

    merged = copy.deepcopy(matching_current)
    merged["service"] = desired_rule.get("service")
    if desired_rule.get("hostname"):
        merged["hostname"] = desired_rule.get("hostname")
    else:
        merged.pop("hostname", None)

    desired_path = desired_rule.get("path")
    if desired_path:
        merged["path"] = desired_path
    else:
        merged.pop("path", None)

    existing_origin = merged.get("originRequest")
    if not isinstance(existing_origin, dict):
        existing_origin = {}
    desired_origin = desired_rule.get("originRequest")
    if not isinstance(desired_origin, dict):
        desired_origin = {}

    managed_origin_keys = {
        "noTLSVerify",
        "originServerName",
        "httpHostHeader",
        "http2Origin",
        "disableChunkedEncoding",
        "matchSNIToHost"
    }
    merged_origin = {k: v for k, v in existing_origin.items() if k not in managed_origin_keys}
    merged_origin.update(desired_origin)

    if merged_origin:
        merged["originRequest"] = merged_origin
    else:
        merged.pop("originRequest", None)

    return merged

def get_cloudflared_container():
    from app import app
    with app.app_context():
        if not docker_client:
            logging.debug("Docker client unavailable in get_cloudflared_container.")
            return None
        if config.USE_EXTERNAL_CLOUDFLARED:
            return None
        
        container_name = current_app.config.get('CLOUDFLARED_CONTAINER_NAME')
        if not container_name:
            logging.debug("CLOUDFLARED_CONTAINER_NAME is not set in config.")
            return None
        try:
            container = docker_client.containers.get(container_name)
            container.reload()
            return container
        except NotFound:
            logging.debug(f"Agent container '{container_name}' not found.")
            return None
        except APIError as e:
            logging.error(f"Docker API error getting agent container '{container_name}': {e}")
            cloudflared_agent_state["last_action_status"] = f"Error get agent: {e}"
            return None
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Docker connection error getting agent container: {e}")
            cloudflared_agent_state["last_action_status"] = "Error: Docker connect check net."
            return None
        except Exception as e:
            logging.error(f"Unexpected error getting agent container '{container_name}': {e}", exc_info=True)
            cloudflared_agent_state["last_action_status"] = "Error: Unexpected get agent: {e}"
            return None

def update_cloudflared_container_status():
    from app import app
    with app.app_context():
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
                        logging.info("Agent status changing to docker_unavailable.")
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
                cloudflared_agent_state["last_action_status"] = "Error: Docker connect check net."
            except Exception as e_unexpected:
                logging.error(f"Unexpected error reloading agent status for {container.name}: {e_unexpected}", exc_info=True)
                return 
        
        if current_status != new_status:
            container_name = current_app.config.get('CLOUDFLARED_CONTAINER_NAME', 'cloudflared-agent')
            logging.info(f"Agent container '{container_name}' status changed: {current_status} -> {new_status}")
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
            if "already exists" in str(e_create).lower(): 
                logging.warning(f"Network '{network_name}' creation reported conflict but NotFound was raised? Assuming it exists now.")
                return True 
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
        cloudflared_agent_state["last_action_status"] = "Error: Docker connect check net."
        return False
    except Exception as e_unexp_get:
        logging.error(f"Unexpected error checking network '{network_name}': {e_unexp_get}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = "Error: Unexpected check net: {e_unexp_get}"
        return False

def start_cloudflared_container():
    from app import app
    with app.app_context():
        container_name = current_app.config.get('CLOUDFLARED_CONTAINER_NAME')
        logging.info(f"Attempting to start and reconcile agent container '{container_name}'...")
        cloudflared_agent_state["last_action_status"] = "Starting/Reconciling..."
        
        if not docker_client:
            cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
            logging.error("Docker client unavailable, cannot start agent container.")
            return False
        if not tunnel_state.get("token"):
            cloudflared_agent_state["last_action_status"] = "Error: Tunnel token not available."
            logging.error("Tunnel token not available, cannot start agent container.")
            return False
        if not config.CLOUDFLARED_NETWORK_NAME or not ensure_docker_network_exists(config.CLOUDFLARED_NETWORK_NAME):
            cloudflared_agent_state["last_action_status"] = "Error: Docker network setup failed."
            logging.error("Docker network setup failed, cannot start agent container.")
            return False

        token = tunnel_state["token"]
        container = get_cloudflared_container()
        needs_recreate = False

        if container:
            logging.info(f"Found existing agent container '{container.name}' with status: {container.status}. Checking configuration...")
            
            network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', 'default')
            if network_mode != config.CLOUDFLARED_NETWORK_NAME:
                logging.warning(f"Network mismatch for managed agent. Desired: '{config.CLOUDFLARED_NETWORK_NAME}', Actual: '{network_mode}'. Recreation required.")
                needs_recreate = True
            try:
                current_image = container.image.tags[0] if container.image.tags else None
                if current_image != config.CLOUDFLARED_IMAGE:
                    logging.warning(f"Image mismatch for managed agent. Desired: '{config.CLOUDFLARED_IMAGE}', Actual: '{current_image}'. Recreation required.")
                    needs_recreate = True
            except Exception as img_err:
                 logging.warning(f"Could not reliably determine image for running agent container: {img_err}")
            
            desired_metrics_port = config.CLOUDFLARED_METRICS_PORT
            port_bindings = container.attrs.get('HostConfig', {}).get('PortBindings', {})
            
            actual_metrics_port = None
            if port_bindings:
                for port_key in port_bindings:
                    if port_key.endswith('/tcp'):
                        actual_metrics_port = port_key[:-4] 
                        break 
            
            if desired_metrics_port and actual_metrics_port != desired_metrics_port:
                logging.warning(f"Metrics port mismatch. Desired: '{desired_metrics_port}', Actual: '{actual_metrics_port}'. Recreation required.")
                needs_recreate = True
            elif not desired_metrics_port and actual_metrics_port:
                logging.warning(f"Metrics port should be disabled, but found port '{actual_metrics_port}' exposed. Recreation required.")
                needs_recreate = True

            if needs_recreate:
                logging.info(f"Removing misconfigured agent container '{container.name}' before recreation...")
                try:
                    container.remove(force=True)
                    container = None
                except (APIError, requests.exceptions.ConnectionError) as rm_err:
                    logging.error(f"Failed to remove misconfigured agent '{container.name}': {rm_err}. Cannot proceed.")
                    cloudflared_agent_state["last_action_status"] = f"Error: Failed to remove old agent: {rm_err}"
                    return False

        if container:
            if container.status == 'running':
                msg = f"Managed agent container '{container.name}' is already running and correctly configured."
                logging.info(msg)
                cloudflared_agent_state["last_action_status"] = msg
            else:
                logging.info(f"Starting correctly configured but stopped agent container '{container.name}'...")
                try:
                    container.start()
                    msg = f"Started existing agent container '{container.name}'."
                    cloudflared_agent_state["last_action_status"] = msg
                    logging.info(msg)
                except NotFound as e:
                    if 'network' in str(e).lower() and 'not found' in str(e).lower():
                        logging.warning(f"Agent container '{container.name}' is attached to a stale or missing network. Forcing recreation.")
                        cloudflared_agent_state["last_action_status"] = "Stale network detected, recreating agent..."
                        try:
                            container.remove(force=True)
                            container = None
                        except (APIError, requests.exceptions.ConnectionError) as rm_err:
                            logging.error(f"Failed to remove broken agent '{container.name}': {rm_err}. Cannot proceed.")
                            cloudflared_agent_state["last_action_status"] = f"Error: Failed to remove broken agent: {rm_err}"
                            return False
                    else:
                        logging.error(f"Failed to start container '{container.name}' due to an unexpected 'NotFound' error: {e}", exc_info=True)
                        cloudflared_agent_state["last_action_status"] = f"Error starting agent: {e}"
                        raise
                except (APIError, requests.exceptions.ConnectionError) as e:
                    logging.error(f"Failed to start container '{container.name}': {e}", exc_info=True)
                    cloudflared_agent_state["last_action_status"] = f"Error starting agent: {e}"
                    return False

        if not container:
            logging.info(f"Agent container '{container_name}' not found or was broken. Creating new container...")
            try:
                logging.info(f"Pulling image {config.CLOUDFLARED_IMAGE}...")
                docker_client.images.pull(config.CLOUDFLARED_IMAGE)
                logging.info("Image pull complete.")
            except Exception as img_err:
                logging.warning(f"Could not pull image {config.CLOUDFLARED_IMAGE}: {img_err}. Will attempt using local if available.")

            command_parts = ["tunnel"]
            ports_mapping = {}
            if config.CLOUDFLARED_METRICS_PORT:
                metrics_address = f"0.0.0.0:{config.CLOUDFLARED_METRICS_PORT}"
                command_parts.extend(["--metrics", metrics_address])
                ports_mapping[f"{config.CLOUDFLARED_METRICS_PORT}/tcp"] = int(config.CLOUDFLARED_METRICS_PORT)
                logging.info(f"Metrics endpoint will be enabled on {metrics_address}")

            command_parts.extend(["--no-autoupdate", "run", "--token", token])
            try:
                container_params = {
                    "image": config.CLOUDFLARED_IMAGE,
                    "command": command_parts, 
                    "name": container_name,
                    "network": config.CLOUDFLARED_NETWORK_NAME,
                    "restart_policy": {"Name": "unless-stopped"},
                    "detach": True,
                    "remove": False, 
                    "labels": {"managed-by": "dockflare"},
                    "ports": ports_mapping,
                    "extra_hosts": {"host.docker.internal": "host-gateway"}, 
                }
                new_container = docker_client.containers.run(**container_params)
                msg = f"Successfully created and started agent container '{new_container.name}' ({new_container.id[:12]})."
                cloudflared_agent_state["last_action_status"] = msg
                logging.info(msg)
            except APIError as create_err:
                logging.error(f"Failed to create new agent container: {create_err}")
                cloudflared_agent_state["last_action_status"] = f"Error creating agent: {create_err}"
                return False
            except requests.exceptions.ConnectionError as e_conn_run:
                logging.error(f"Docker connection error while creating agent: {e_conn_run}")
                cloudflared_agent_state["last_action_status"] = "Error: Docker connection lost."
                return False
                
        time.sleep(2) 
        update_cloudflared_container_status() 
        logging.info("Exiting start_cloudflared_container (Success: True).")
        return True

def stop_cloudflared_container():
    from app import app
    with app.app_context():
        container_name = current_app.config.get('CLOUDFLARED_CONTAINER_NAME')
        logging.info(f"Attempting to stop agent container '{container_name}'...")
        cloudflared_agent_state["last_action_status"] = "Stopping..."
        success_flag = False
        
        if not docker_client:
            msg = "Docker client unavailable."
            logging.error(msg)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
            return False

        container = get_cloudflared_container()
        if not container:
            msg = f"Agent container '{container_name}' not found (already stopped/removed?)."
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

            logging.info(f"Stopping running agent container '{container.name}'...")
            container.stop(timeout=30) 
            msg = f"Successfully stopped agent container '{container.name}'."
            cloudflared_agent_state["last_action_status"] = msg
            logging.info(msg)
            success_flag = True
        except (APIError, NotFound) as e_stop: 
            msg = f"Docker API error stopping agent container '{container_name}': {e_stop}"
            logging.error(msg, exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
            success_flag = False
        except requests.exceptions.ConnectionError as e_conn:
            msg = f"Docker connection error stopping agent container: {e_conn}"
            logging.error(msg)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
            success_flag = False
        except Exception as e_unexp:
            msg = f"Unexpected error stopping agent container '{container_name}': {e_unexp}"
            logging.error(msg, exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"
            success_flag = False
    
    if success_flag: 
        time.sleep(2)

    update_cloudflared_container_status() 
    logging.info(f"Exiting stop_cloudflared_container (Success: {success_flag}).")
    return success_flag
