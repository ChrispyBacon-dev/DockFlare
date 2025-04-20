import os
import sys
import logging
import re
import json
import threading
import time
import queue
from datetime import datetime, timedelta, timezone
import random
import copy 

import docker
from docker.errors import NotFound, APIError
from flask import Flask, jsonify, render_template, redirect, url_for, request, Response, stream_with_context
from dotenv import load_dotenv
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')
load_dotenv()

MAX_CF_UPDATE_RETRIES = 3
CF_UPDATE_RETRY_DELAY = 2
CF_UPDATE_BACKOFF_FACTOR = 2

CF_API_TOKEN = os.getenv('CF_API_TOKEN')
TUNNEL_NAME = os.getenv('TUNNEL_NAME')
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_ZONE_ID = os.getenv('CF_ZONE_ID')
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}

LABEL_PREFIX = os.getenv('LABEL_PREFIX', 'cloudflare.tunnel')
GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 28800))
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 300))
AGENT_STATUS_UPDATE_INTERVAL_SECONDS = int(os.getenv('AGENT_STATUS_UPDATE_INTERVAL_SECONDS', 10))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')
MAX_LOG_QUEUE_SIZE = 200

CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"
CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net')

if not CF_API_TOKEN or not TUNNEL_NAME or not CF_ACCOUNT_ID:
    logging.error("FATAL: Missing required environment variables (CF_API_TOKEN, TUNNEL_NAME, CF_ACCOUNT_ID)")
    sys.exit(1)
if not CF_ZONE_ID:
    logging.warning("CF_ZONE_ID not set. DNS management requires 'cloudflare.tunnel.zonename' label on containers.")

log_queue = queue.Queue(maxsize=MAX_LOG_QUEUE_SIZE)
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class QueueLogHandler(logging.Handler):
    """Sends log records to the SSE queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        log_entry = self.format(record)
        try:
            self.log_queue.put_nowait(log_entry)
        except queue.Full:
            try:
                self.log_queue.get_nowait()
                self.log_queue.put_nowait(log_entry)
            except queue.Empty:
                pass
            except queue.Full:
                 print("Log queue full, dropping message.", file=sys.stderr)

queue_handler = QueueLogHandler(log_queue)
queue_handler.setFormatter(log_formatter)
queue_handler.setLevel(logging.INFO)
root_logger = logging.getLogger()
root_logger.addHandler(queue_handler)

try:
    docker_client = docker.from_env(timeout=10)
    docker_client.ping()
    logging.info("Successfully connected to Docker daemon.")
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    docker_client = None

tunnel_state = { "name": TUNNEL_NAME, "id": None, "token": None, "status_message": "Initializing...", "error": None }
cloudflared_agent_state = { "container_status": "unknown", "last_action_status": None }
managed_rules = {}
zone_id_cache = {}
state_lock = threading.Lock()
stop_event = threading.Event()

def load_state():
    global managed_rules
    state_dir = os.path.dirname(STATE_FILE_PATH)
    if not os.path.exists(state_dir):
        try:
             os.makedirs(state_dir, exist_ok=True)
             logging.info(f"Created directory for state file: {state_dir}")
        except OSError as e:
             logging.error(f"FATAL: Could not create directory for state file {state_dir}: {e}. State persistence will fail.")
             managed_rules = {}
             return

    if not os.path.exists(STATE_FILE_PATH):
        logging.info(f"State file '{STATE_FILE_PATH}' not found, starting fresh.")
        managed_rules = {}
        return
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            loaded_data = json.load(f)
        for hostname, rule in loaded_data.items():
             if rule.get("delete_at") and isinstance(rule.get("delete_at"), str):
                 try:
                     if rule["delete_at"].endswith('Z'):
                        dt = datetime.fromisoformat(rule["delete_at"].replace('Z', '+00:00'))
                     else:
                         dt = datetime.fromisoformat(rule["delete_at"])
                     rule["delete_at"] = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                 except ValueError as date_err:
                     logging.warning(f"Could not parse delete_at for {hostname}: {rule['delete_at']} Error: {date_err}. Setting to None.")
                     rule["delete_at"] = None
             elif not isinstance(rule.get("delete_at"), datetime):
                 rule["delete_at"] = None
             if "zone_id" not in rule:
                 logging.warning(f"Rule for {hostname} loaded from state is missing 'zone_id'. Will attempt to re-determine on reconcile.")
                 rule["zone_id"] = None
        managed_rules = loaded_data
        logging.info(f"Loaded state for {len(managed_rules)} rules from {STATE_FILE_PATH}")
    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Error loading state from {STATE_FILE_PATH}: {e}. Starting fresh.", exc_info=True)
        managed_rules = {}

def save_state():
    serializable_state = {}
    for hostname, rule in managed_rules.items():
        rule_copy = rule.copy()
        if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
            rule_copy["delete_at"] = rule_copy["delete_at"].astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if "zone_id" not in rule_copy:
            logging.warning(f"Attempting to save rule for {hostname} without zone_id!")
            rule_copy["zone_id"] = None
        serializable_state[hostname] = rule_copy
    try:
        state_dir = os.path.dirname(STATE_FILE_PATH)
        if not os.path.exists(state_dir):
            try: os.makedirs(state_dir, exist_ok=True); logging.info(f"Created directory {state_dir} before saving state.")
            except OSError as e: logging.error(f"Could not create directory {state_dir} for state file: {e}. Save failed."); return

        temp_file_path = STATE_FILE_PATH + ".tmp"
        with open(temp_file_path, 'w') as f:
            json.dump(serializable_state, f, indent=2)
        os.replace(temp_file_path, STATE_FILE_PATH)
        logging.debug(f"Saved state for {len(managed_rules)} rules to {STATE_FILE_PATH}")
    except (IOError, OSError) as e:
        logging.error(f"Error saving state to {STATE_FILE_PATH}: {e}", exc_info=True)

def cf_api_request(method, endpoint, json_data=None, params=None):
    url = f"{CF_API_BASE_URL}{endpoint}"
    error_msg = None
    try:
        logging.info(f"API Request: {method} {url} Params: {params}")
        if json_data:
             logging.debug(f"API Request Data: {json_data}")
        response = requests.request(method, url, headers=CF_HEADERS, json=json_data, params=params, timeout=30)
        response.raise_for_status()
        logging.info(f"API Response Status: {response.status_code}")
        if response.status_code == 204 or not response.content:
            return {"success": True, "result": None}
        try:
            response_data = response.json()
            logging.debug(f"API Response Body (first 500 chars): {str(response_data)[:500]}")
            if isinstance(response_data, dict) and 'success' in response_data:
                 if response_data['success']:
                      return response_data
                 else:
                      cf_errors = response_data.get('errors', [])
                      error_code = None
                      if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                           error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                           error_code = cf_errors[0].get('code')
                      else:
                           error_msg = f"API reported failure but no error details provided. Response: {response_data}"
                      logging.error(f"API Request Failed ({method} {url}): {error_msg} - Full Errors: {cf_errors}")
                      api_exception = requests.exceptions.RequestException(error_msg, response=response)
                      api_exception.cf_error_code = error_code
                      raise api_exception
            else:
                 logging.warning(f"API response for {method} {url} was valid JSON but missing 'success' field. Status: {response.status_code}. Body: {str(response_data)[:200]}")
                 raise requests.exceptions.RequestException(f"Unexpected JSON response format from API. Status: {response.status_code}", response=response)
        except json.JSONDecodeError:
            logging.error(f"API response for {method} {url} was not valid JSON. Status: {response.status_code}. Body: {response.text[:200]}")
            raise requests.exceptions.RequestException(f"Invalid JSON response from API. Status: {response.status_code}", response=response)
    except requests.exceptions.RequestException as e:
        if error_msg is None:
            logging.error(f"API Request Failed: {method} {url}")
            error_msg = f"Request Exception: {e}"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    cf_errors = error_data.get('errors', [])
                    if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                        error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                        e.cf_error_code = cf_errors[0].get('code') 
                    else:
                         error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
                    logging.error(f"API Error Response Body: {error_data}")
                except (ValueError, AttributeError, json.JSONDecodeError):
                     error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
            logging.error(f"Final error message: {error_msg}")

        if "cfd_tunnel" in endpoint and tunnel_state.get("id") is None and "token" not in endpoint:
             tunnel_state["error"] = error_msg
        raise e 

def get_zone_id_from_name(zone_name):
    """Retrieves the Zone ID for a given zone name, using cache."""
    global zone_id_cache
    if not zone_name:
        logging.warning("get_zone_id_from_name called with empty zone_name.")
        return None

    with state_lock:
        cached_id = zone_id_cache.get(zone_name)
    if cached_id:
        logging.debug(f"Zone ID for '{zone_name}' found in cache: {cached_id}")
        return cached_id

    logging.info(f"Zone ID for '{zone_name}' not in cache. Querying Cloudflare API...")
    endpoint = "/zones"
    params = {"name": zone_name, "status": "active"}

    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        results = response_data.get("result", [])

        if results and isinstance(results, list) and len(results) == 1:
            zone_id = results[0].get("id")
            zone_actual_name = results[0].get("name")
            if zone_id and zone_actual_name == zone_name:
                logging.info(f"Found Zone ID for '{zone_name}': {zone_id}")
                with state_lock:
                    zone_id_cache[zone_name] = zone_id
                return zone_id
            else:
                logging.error(f"API returned unexpected result or name mismatch for zone '{zone_name}': {results[0]}")
                return None
        elif results and len(results) > 1:
            logging.error(f"API returned multiple ({len(results)}) active zones matching name '{zone_name}'. Cannot determine correct zone.")
            return None
        else:
            logging.warning(f"No active zone found matching name '{zone_name}' via API.")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error looking up zone '{zone_name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error looking up zone '{zone_name}': {e}", exc_info=True)
        return None

def find_tunnel_via_api(name):
    """Finds an existing tunnel and its token via the API."""
    logging.info(f"Finding tunnel '{name}' via API")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"name": name, "is_deleted": "false"}
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])
        if tunnels and isinstance(tunnels, list):
            tunnel = tunnels[0]
            tunnel_id = tunnel.get("id")
            if tunnel_id:
                logging.info(f"Found existing tunnel '{name}' ID: {tunnel_id}. Getting token...")
                token = get_tunnel_token_via_api(tunnel_id)
                return tunnel_id, token
            else:
                 logging.warning(f"Found tunnel entry for '{name}' but it has no ID: {tunnel}")
                 return None, None
        else:
            logging.info(f"Tunnel '{name}' not found via API.")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding tunnel '{name}': {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error finding tunnel '{name}': {e}", exc_info=True)
        tunnel_state["error"] = f"Unexpected error finding tunnel: {e}"
        return None, None

def get_tunnel_token_via_api(tunnel_id):
    """Gets the token for a specific tunnel ID."""
    logging.info(f"Getting token for tunnel ID '{tunnel_id}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    url = f"{CF_API_BASE_URL}{endpoint}"
    try:
        logging.info(f"API Request: GET {url} (for token)")
        response = requests.request("GET", url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"}, timeout=30)
        response.raise_for_status()
        token = response.text.strip()
        if not token or len(token) < 50:
            logging.error(f"Retrieved token for tunnel {tunnel_id} appears invalid.")
            raise ValueError("Invalid token format received from API")
        logging.info(f"Successfully retrieved token for tunnel {tunnel_id}")
        return token
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error getting token for tunnel {tunnel_id}: {e}"
        if e.response is not None:
             error_msg += f" Status: {e.response.status_code} Body: {e.response.text[:100]}"
        logging.error(error_msg)
        tunnel_state["error"] = error_msg
        raise
    except Exception as e:
         logging.error(f"Unexpected error getting tunnel token for {tunnel_id}: {e}", exc_info=True)
         tunnel_state["error"] = f"Unexpected error getting token: {e}"
         raise

def create_tunnel_via_api(name):
    """Creates a new tunnel and returns its ID and token."""
    logging.info(f"Creating tunnel '{name}' via API")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    payload = {"name": name, "config_src": "cloudflare"}
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        token = result.get("token")
        if not tunnel_id or not token:
            logging.error(f"API response for tunnel creation missing ID or Token: {result}")
            raise ValueError("Missing ID or Token in API response")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id}.")
        return tunnel_id, token
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating tunnel '{name}': {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error creating tunnel '{name}': {e}", exc_info=True)
        tunnel_state["error"] = f"Unexpected error creating tunnel: {e}"
        return None, None

def initialize_tunnel():
    """Finds or creates the tunnel and gets its token."""
    logging.info("Initializing tunnel...")
    tunnel_state["status_message"] = f"Checking for tunnel '{TUNNEL_NAME}' via API..."
    tunnel_state["error"] = None
    tunnel_id = None
    token = None
    try:
        tunnel_id, token = find_tunnel_via_api(TUNNEL_NAME)

        if not tunnel_id and not tunnel_state.get("error"):
            tunnel_state["status_message"] = f"Tunnel '{TUNNEL_NAME}' not found. Creating via API..."
            tunnel_id, token = create_tunnel_via_api(TUNNEL_NAME)

        if tunnel_id and token:
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = token
            tunnel_state["status_message"] = "Tunnel setup complete (using API)."
            tunnel_state["error"] = None
            logging.info(f"Tunnel '{TUNNEL_NAME}' initialized successfully. ID: {tunnel_id}")
        elif not tunnel_state.get("error"):
             tunnel_state["status_message"] = "Tunnel initialization failed."
             tunnel_state["error"] = "Failed to find/create tunnel or retrieve token. Check logs."
             logging.error(f"Tunnel initialization failed for '{TUNNEL_NAME}'. Could not get ID and Token.")
        else:
             tunnel_state["status_message"] = "Tunnel initialization failed (see error details)."

        logging.info(f"Tunnel init completed. State: ID={tunnel_state.get('id')}, Token Present={bool(tunnel_state.get('token'))}, Error={tunnel_state.get('error')}")

    except Exception as e:
        logging.error(f"Unhandled exception during tunnel initialization: {e}", exc_info=True)
        if not tunnel_state.get("error"):
            tunnel_state["error"] = f"Initialization failed unexpectedly: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (unexpected error)."

def get_current_cf_config():
    """Gets the current tunnel configuration from Cloudflare."""
    if not tunnel_state.get("id"):
        logging.warning("Cannot get CF config, tunnel ID not available.")
        return None

    logging.debug("Fetching current CF tunnel configuration.")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
    try:
        response_data = cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            result_data = response_data.get("result")
            config_data = None
            if isinstance(result_data, dict):
                 config_data = result_data.get("config")

            if isinstance(config_data, dict):
                 logging.debug(f"Fetched config: {config_data}")
                 return config_data
            elif config_data is None:
                 logging.info("Fetched config is null.")
                 return {}
            else:
                 logging.warning(f"Unexpected type for 'config' field in API response: {type(config_data)}. Result: {result_data}")
                 return {}
        else:
            logging.error(f"Get config API call failed or returned success=false: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching config: {e}")
        if not tunnel_state.get("error"):
            tunnel_state["error"] = f"Failed get tunnel config: {e}"
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching config: {e}", exc_info=True)
        if not tunnel_state.get("error"):
            tunnel_state["error"] = f"Unexpected error getting tunnel config: {e}"
        return None

def find_dns_record_id(zone_id, hostname, tunnel_id):
    """Finds the ID of a specific CNAME DNS record pointing to the tunnel."""
    if not zone_id or not hostname or not tunnel_id:
        logging.error("find_dns_record_id: Missing required arguments.")
        return None

    expected_content = f"{tunnel_id}.cfargotunnel.com"
    endpoint = f"/zones/{zone_id}/dns_records"
    params = {"type": "CNAME", "name": hostname, "content": expected_content, "match": "all"}

    try:
        logging.info(f"Searching DNS: Zone={zone_id}, Type=CNAME, Name={hostname}, Content={expected_content}")
        response_data = cf_api_request("GET", endpoint, params=params)
        results = response_data.get("result", [])

        if results and isinstance(results, list):
            record_id = results[0].get("id")
            if record_id:
                logging.info(f"Found DNS record for {hostname} in zone {zone_id} with ID: {record_id}")
                return record_id
            else:
                logging.warning(f"DNS record found for {hostname} but it lacks an ID field: {results[0]}")
                return None
        else:
            logging.info(f"No matching DNS record found for {hostname} in zone {zone_id}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding DNS record for {hostname}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error finding DNS record for {hostname}: {e}", exc_info=True)
        return None

def is_valid_hostname(hostname):
    if not hostname: return False
    return re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$", hostname) is not None

def is_valid_service(service):
    if not service: return False
    return (re.match(r"^(https?|tcp|unix)://", service) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)) is not None

def create_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    """Creates a CNAME DNS record pointing to the tunnel, handling existing records."""
    if not zone_id or not hostname or not tunnel_id:
        logging.error("create_cloudflare_dns_record: Missing required arguments.")
        return None

    record_name = hostname
    record_content = f"{tunnel_id}.cfargotunnel.com"
    endpoint = f"/zones/{zone_id}/dns_records"
    payload = {
        "type": "CNAME",
        "name": record_name,
        "content": record_content,
        "ttl": 1,
        "proxied": True
    }

    try:
        logging.info(f"Attempting to create DNS CNAME in zone {zone_id}: Name={record_name}, Content={record_content}, Proxied=True")
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        new_record_id = result.get("id")
        if new_record_id:
            logging.info(f"Successfully created DNS record for {hostname} in zone {zone_id}. New ID: {new_record_id}")
            return new_record_id
        else:
            logging.error(f"DNS record creation API call for {hostname} reported success but response missing ID: {result}")
            return None
    except requests.exceptions.RequestException as e:
        cf_error_code = getattr(e, 'cf_error_code', None)
        if cf_error_code == 81057 or (e.response is not None and "record already exists" in e.response.text.lower()):
             logging.warning(f"DNS CNAME for {hostname} in zone {zone_id} likely already exists (API error indicated duplication). Treating as success.")
             existing_id = find_dns_record_id(zone_id, hostname, tunnel_id)
             return existing_id if existing_id else "already_exists" 
        else:
             logging.error(f"API error creating DNS record for {hostname}: {e}")
             return None
    except Exception as e:
        logging.error(f"Unexpected error creating DNS record for {hostname}: {e}", exc_info=True)
        return None

def delete_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    """Deletes the specific CNAME DNS record pointing to the tunnel."""
    if not zone_id or not hostname or not tunnel_id:
        logging.error("delete_cloudflare_dns_record: Missing required arguments.")
        return False

    dns_record_id = find_dns_record_id(zone_id, hostname, tunnel_id)
    if not dns_record_id:
        logging.warning(f"DNS record for {hostname} in zone {zone_id} (pointing to tunnel {tunnel_id}) not found to delete. Assuming success.")
        return True

    logging.info(f"Attempting to delete DNS record for {hostname} in zone {zone_id} (ID: {dns_record_id})")
    endpoint = f"/zones/{zone_id}/dns_records/{dns_record_id}"
    try:
        cf_api_request("DELETE", endpoint)
        logging.info(f"Successfully deleted DNS record for {hostname} (ID: {dns_record_id}).")
        return True
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 404:
             logging.warning(f"DNS record {dns_record_id} for {hostname} not found during delete attempt (404). Treating as success.")
             return True
        logging.error(f"API error deleting DNS record {dns_record_id} for {hostname}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error deleting DNS record {dns_record_id} for {hostname}: {e}", exc_info=True)
        return False

def update_cloudflare_config():
    """Updates the Cloudflare tunnel ingress configuration if needed."""
    if not tunnel_state.get("id"):
        logging.warning("Cannot update CF config, tunnel ID missing.")
        return False

    final_ingress_rules = None
    needs_api_update = False

    with state_lock:
        logging.info("Checking for Cloudflare tunnel config updates...")
        desired_ingress_rules = []
        catch_all_rule = {"service": "http_status:404"}

        for hostname, rule_details in managed_rules.items():
            if rule_details.get("status") == "active":
                service = rule_details.get("service")
                if service:
                    no_tls_verify = rule_details.get("no_tls_verify", False)
                    desired_ingress_rules.append({
                        "hostname": hostname,
                        "service": service,
                        "originRequest": {
                            "noTLSVerify": no_tls_verify
                        }
                    })
                else:
                    logging.warning(f"Rule {hostname} is active but missing 'service' detail. Skipping.")

        desired_ingress_rules.sort(key=lambda x: x.get("hostname", ""))

        logging.debug("Fetching current CF config for comparison...")
        current_config = get_current_cf_config()
        if current_config is None:
            logging.error("Failed to fetch current CF config, aborting update check.")
            return False

        current_cf_ingress = [r for r in current_config.get("ingress", []) if r.get("service") != catch_all_rule["service"]]

        def rule_to_canonical(rule):
            items = sorted([(k, v) for k, v in rule.items() if k in ["hostname", "service"]])
            return tuple(items)

        try:
             current_cf_set = {rule_to_canonical(r) for r in current_cf_ingress if r.get("hostname") and r.get("service")}
             desired_set = {rule_to_canonical(r) for r in desired_ingress_rules if r.get("hostname") and r.get("service")}
        except Exception as e:
             logging.error(f"Error creating canonical rule sets for comparison: {e}", exc_info=True)
             return False

        if current_cf_set == desired_set:
            logging.info("No changes detected in CF tunnel config. Skipping API update.")
            needs_api_update = False
        else:
            logging.info("Change detected. Desired ingress rules differ from current CF config.")
            logging.debug(f"Current CF rules: {current_cf_set}")
            logging.debug(f"Desired rules: {desired_set}")
            needs_api_update = True
            final_ingress_rules = desired_ingress_rules + [catch_all_rule]

    if needs_api_update and final_ingress_rules is not None:
        endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        payload = {"config": {"ingress": final_ingress_rules}}
        last_exception = None

        for attempt in range(MAX_CF_UPDATE_RETRIES + 1):
            try:
                logging.info(f"Attempting CF config push (Attempt {attempt + 1}/{MAX_CF_UPDATE_RETRIES + 1})...")
                cf_api_request("PUT", endpoint, json_data=payload)
                logging.info("Successfully updated CF tunnel configuration via API.")
                cloudflared_agent_state["last_action_status"] = f"CF config updated successfully at {datetime.now(timezone.utc).isoformat()}"
                if tunnel_state.get("error") and ("Failed update tunnel config" in tunnel_state["error"] or "API Error" in tunnel_state["error"]):
                     logging.info(f"Clearing previous API error related to config update: {tunnel_state['error']}")
                     tunnel_state["error"] = None
                return True
            except requests.exceptions.RequestException as e:
                last_exception = e
                status_code = e.response.status_code if e.response is not None else None
                logging.warning(f"CF API update attempt {attempt + 1} failed: {e} (Status: {status_code})")

                is_retryable = isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)) or status_code in [429, 500, 502, 503, 504]

                if is_retryable and attempt < MAX_CF_UPDATE_RETRIES:
                    wait_time = CF_UPDATE_RETRY_DELAY * (CF_UPDATE_BACKOFF_FACTOR ** attempt)
                    wait_time *= (1 + random.uniform(-0.2, 0.2))
                    wait_time = max(1, wait_time)

                    if status_code == 429 and e.response is not None:
                         retry_after = e.response.headers.get("Retry-After")
                         if retry_after:
                              try:
                                   wait_time = max(wait_time, int(retry_after))
                                   logging.info(f"Respecting Retry-After header: {retry_after} seconds.")
                              except ValueError:
                                   logging.warning(f"Could not parse Retry-After header value: {retry_after}")

                    logging.info(f"Retrying CF update in {wait_time:.1f} seconds...")
                    if stop_event.wait(wait_time):
                        logging.warning("Shutdown requested during CF update retry wait.")
                        cloudflared_agent_state["last_action_status"] = "Error: CF update aborted (shutdown during retry)."
                        tunnel_state["error"] = "Failed update tunnel config: aborted retry"
                        return False
                    continue
                else:
                    logging.error(f"CF API update failed permanently (Retryable: {is_retryable}, Attempt: {attempt + 1}).")
                    break
            except Exception as e:
                last_exception = e
                logging.error(f"Unexpected error during CF API update attempt {attempt + 1}: {e}", exc_info=True)
                break

        logging.error(f"Failed to update CF tunnel config after {MAX_CF_UPDATE_RETRIES + 1} attempts.")
        error_message = f"Failed update tunnel config: {last_exception}"
        cloudflared_agent_state["last_action_status"] = f"Error: {error_message}"
        if not tunnel_state.get("error"):
            tunnel_state["error"] = error_message
        return False

    elif needs_api_update and final_ingress_rules is None:
        logging.error("Internal error: update needed but final ingress rules were not generated.")
        return False
    else:
        return True

def process_container_start(container):
    """Processes a container start event based on labels."""
    if not container: return
    container_id = None
    container_name = "Unknown"
    try:
        container_id = container.id
        try:
             container.reload()
             container_name = container.name
        except NotFound:
             logging.warning(f"Container {container_id[:12]} not found processing start (likely stopped very quickly?).")
             return
        except APIError as e:
             logging.error(f"Docker API error reloading container {container_id[:12]}: {e}")
             return

        labels = container.labels
        enabled_label = f"{LABEL_PREFIX}.enable"
        hostname_label = f"{LABEL_PREFIX}.hostname"
        service_label = f"{LABEL_PREFIX}.service"
        zone_name_label = f"{LABEL_PREFIX}.zonename"
        no_tls_verify_label = f"{LABEL_PREFIX}.no_tls_verify"

        is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
        hostname = labels.get(hostname_label)
        service = labels.get(service_label)
        zone_name = labels.get(zone_name_label)
        no_tls_verify = labels.get(no_tls_verify_label, "false").lower() in ["true", "1", "t", "yes"]

        if not is_enabled:
            logging.debug(f"Ignoring start: {container_name} ({container_id[:12]}): '{enabled_label}' not true.")
            return
        if not hostname or not service:
            logging.warning(f"Ignoring start: {container_name} ({container_id[:12]}): Missing '{hostname_label}' or '{service_label}'.")
            return

        if not is_valid_hostname(hostname):
             logging.warning(f"Ignoring start: {container_name} ({container_id[:12]}): Invalid hostname format '{hostname}'.")
             return
        if not is_valid_service(service):
             logging.warning(f"Ignoring start: {container_name} ({container_id[:12]}): Invalid service format '{service}'. Needs protocol (http/https/tcp/unix) or host:port.")
             return

        target_zone_id = None
        if zone_name:
            logging.info(f"Container {container_name} specified zone name: '{zone_name}'. Looking up ID.")
            target_zone_id = get_zone_id_from_name(zone_name)
            if not target_zone_id:
                logging.error(f"Failed to find Zone ID for specified name '{zone_name}' for container {container_name}. Cannot manage DNS for {hostname}.")
                return
        else:
            logging.debug(f"Container {container_name} did not specify zone name. Using default Zone ID if available.")
            target_zone_id = CF_ZONE_ID

        if not target_zone_id:
             logging.error(f"Cannot manage DNS for {hostname} (container {container_name}): No valid Zone ID found (label lookup failed and no default CF_ZONE_ID set?).")
             return

        logging.info(f"Managing {hostname} (from {container_name}) in Zone ID: {target_zone_id}")

        needs_cf_update = False
        state_changed_locally = False
        with state_lock:
            existing_rule = managed_rules.get(hostname)
            if existing_rule:
                zone_id_changed = existing_rule.get("zone_id") != target_zone_id

                if existing_rule.get("status") == "pending_deletion":
                    logging.info(f"Rule for {hostname} was pending deletion. Reactivating.")
                    existing_rule["status"] = "active"
                    existing_rule["delete_at"] = None
                    existing_rule["service"] = service
                    existing_rule["container_id"] = container_id
                    existing_rule["zone_id"] = target_zone_id
                    existing_rule["no_tls_verify"] = no_tls_verify
                    state_changed_locally = True
                    needs_cf_update = True
                    if zone_id_changed:
                        logging.info(f"Zone ID for reactivated rule {hostname} updated to {target_zone_id}.")
                elif existing_rule.get("status") == "active":
                    service_changed = existing_rule.get("service") != service
                    container_changed = existing_rule.get("container_id") != container_id
                    no_tls_verify_changed = existing_rule.get("no_tls_verify") != no_tls_verify

                    if container_changed:
                        logging.info(f"Updating container ID for active rule {hostname}: '{existing_rule.get('container_id')[:12]}' -> '{container_id[:12]}'.")
                        existing_rule["container_id"] = container_id
                        state_changed_locally = True
                    if service_changed:
                         logging.info(f"Updating service for active rule {hostname}: '{existing_rule.get('service')}' -> '{service}'.")
                         existing_rule["service"] = service
                         state_changed_locally = True
                         needs_cf_update = True
                    if no_tls_verify_changed:
                         logging.info(f"Updating noTLSVerify for active rule {hostname}: '{existing_rule.get('no_tls_verify')}' -> '{no_tls_verify}'.")
                         existing_rule["no_tls_verify"] = no_tls_verify
                         state_changed_locally = True
                         needs_cf_update = True
                    if zone_id_changed:
                         logging.warning(f"Zone ID for active rule {hostname} changed ('{existing_rule.get('zone_id')}' -> '{target_zone_id}'). DNS in old zone may be stale if cleanup failed.")
                         existing_rule["zone_id"] = target_zone_id
                         state_changed_locally = True
                         needs_cf_update = True
            else:
                logging.info(f"Adding new active rule for hostname: {hostname}")
                managed_rules[hostname] = {
                    "service": service,
                    "container_id": container_id,
                    "status": "active",
                    "delete_at": None,
                    "zone_id": target_zone_id,
                    "no_tls_verify": no_tls_verify
                }
                state_changed_locally = True
                needs_cf_update = True

            if state_changed_locally:
                logging.debug(f"Saving state after processing start for {hostname}.")
                save_state()

        if needs_cf_update:
            logging.info(f"Triggering Cloudflare config update due to change for {hostname}.")
            if update_cloudflare_config():
                logging.info(f"Tunnel config update successful for {hostname}.")
                if tunnel_state.get("id"):
                    dns_record_id = create_cloudflare_dns_record(target_zone_id, hostname, tunnel_state["id"])
                    if dns_record_id:
                         logging.info(f"DNS record management in zone {target_zone_id} successful for {hostname}.")
                    else:
                         logging.error(f"CRITICAL: Tunnel config updated for {hostname} but failed to create/verify DNS record in zone {target_zone_id}!")
                         cloudflared_agent_state["last_action_status"] = f"Error: Failed creating DNS for {hostname} in zone {target_zone_id}."
                else:
                     logging.error("Missing Tunnel ID - cannot manage DNS record for {hostname}.")
            else:
                logging.error(f"Failed to update Cloudflare tunnel config after processing start for {hostname}. DNS record not managed.")
        elif state_changed_locally:
             logging.debug(f"Local state updated for {hostname} (e.g., container ID), no Cloudflare config change needed.")

    except NotFound:
        logging.warning(f"Container {container_name} ({container_id[:12] if container_id else 'Unknown'}) not found during start processing.")
    except APIError as e:
        logging.error(f"Docker API error processing container start ({container_name}): {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error processing container start ({container_name}): {e}", exc_info=True)

def schedule_container_stop(container_id):
    """Schedules a rule for deletion when its container stops."""
    if not container_id: return
    logging.info(f"Processing stop event for container {container_id[:12]}.")
    hostname_to_schedule = None
    state_changed = False
    with state_lock:
        for hn, details in managed_rules.items():
            if details.get("container_id") == container_id and details.get("status") == "active":
                hostname_to_schedule = hn
                break

        if hostname_to_schedule:
            logging.info(f"Container {container_id[:12]} managed hostname '{hostname_to_schedule}'. Marking rule for deletion.")
            rule = managed_rules[hostname_to_schedule]
            if rule.get("status") != "pending_deletion":
                 rule["status"] = "pending_deletion"
                 rule["delete_at"] = datetime.now(timezone.utc) + timedelta(seconds=GRACE_PERIOD_SECONDS)
                 logging.info(f"Rule for {hostname_to_schedule} scheduled for deletion at {rule['delete_at'].isoformat()}")
                 state_changed = True
            else:
                 logging.info(f"Rule for {hostname_to_schedule} was already pending deletion.")
        else:
            logging.info(f"Stop event for {container_id[:12]}, but it didn't manage an active rule in current state.")

        if state_changed:
            save_state()

def docker_event_listener():
    """Listens for Docker start/stop events and processes them."""
    if not docker_client:
        logging.error("Docker client unavailable, event listener cannot start.")
        return

    logging.info("Starting Docker event listener...")
    error_count = 0
    max_errors = 5

    while not stop_event.is_set() and error_count < max_errors:
        try:
            logging.info("Connecting to Docker event stream...")
            events = docker_client.events(decode=True, since=int(time.time()))
            logging.info("Successfully connected to Docker event stream.")
            error_count = 0

            for event in events:
                if stop_event.is_set():
                    logging.info("Stop event received, exiting listener loop.")
                    break

                ev_type = event.get("Type")
                action = event.get("Action")
                actor = event.get("Actor", {})
                cont_id = actor.get("ID")

                logging.debug(f"Docker Event: Type={ev_type}, Action={action}, ID={cont_id[:12] if cont_id else 'N/A'}")

                if ev_type == "container" and cont_id:
                    if action == "start":
                        container = None
                        for attempt in range(3): 
                            try:
                                container = docker_client.containers.get(cont_id)
                                if container.labels.get(f"{LABEL_PREFIX}.hostname"):
                                     logging.debug(f"Container {cont_id[:12]} details retrieved on attempt {attempt+1}.")
                                     break 
                                else:
                                     logging.debug(f"Container {cont_id[:12]} found but labels might be missing, retrying ({attempt+1}/3)...")
                            except NotFound:
                                logging.debug(f"Container {cont_id[:12]} not found on attempt {attempt+1}, retrying...")
                            except APIError as e:
                                logging.error(f"Docker API error getting container {cont_id[:12]} on attempt {attempt+1}: {e}")
                                break 
                            except Exception as e:
                                logging.error(f"Unexpected error getting container {cont_id[:12]} details: {e}", exc_info=True)
                                break 

                            if attempt < 2: 
                                time.sleep(0.1) 
                            else:
                                logging.warning(f"Failed to get container {cont_id[:12]} details after multiple attempts.")

                        if container:
                            try:
                                process_container_start(container)
                            except Exception as e:
                                logging.error(f"Unexpected error processing start event for {cont_id[:12]} after retrieval: {e}", exc_info=True)
                        
                    elif action in ["stop", "die", "destroy", "kill"]:
                         try:
                             schedule_container_stop(cont_id)
                         except Exception as e:
                             logging.error(f"Unexpected error processing stop/die/destroy event for {cont_id[:12]}: {e}", exc_info=True)

        except requests.exceptions.ConnectionError as e:
            error_count += 1
            logging.error(f"Docker listener connection error: {e}. Reconnecting ({error_count}/{max_errors})...")
            stop_event.wait(min(30, 5 * error_count))
        except APIError as e:
             error_count += 1
             logging.error(f"Docker listener API error: {e}. Reconnecting ({error_count}/{max_errors})...")
             stop_event.wait(min(30, 5 * error_count))
        except Exception as e:
            error_count += 1
            logging.error(f"Unexpected error in Docker event listener: {e}. Reconnecting ({error_count}/{max_errors})...", exc_info=True)
            stop_event.wait(min(30, 5 * error_count))

        if stop_event.is_set():
            break

    if error_count >= max_errors:
        logging.error("Docker event listener stopping after multiple consecutive errors.")
    logging.info("Docker event listener stopped.")

def cleanup_expired_rules():
    """Periodically checks for and cleans up expired rules."""
    logging.info("Starting cleanup task...")
    while not stop_event.is_set():
        next_check_time = time.time() + CLEANUP_INTERVAL_SECONDS
        try:
            logging.debug("Running cleanup check for expired rules...")
            rules_to_delete = {}
            now_utc = datetime.now(timezone.utc)
            state_changed_in_cleanup = False

            with state_lock:
                for hostname, details in managed_rules.items():
                    if details.get("status") == "pending_deletion":
                        delete_at = details.get("delete_at")
                        is_expired = False
                        if isinstance(delete_at, datetime):
                             delete_at_utc = delete_at.astimezone(timezone.utc)
                             if delete_at_utc <= now_utc:
                                 is_expired = True
                        else:
                             logging.warning(f"Rule {hostname} pending delete but has invalid delete_at timestamp: {delete_at}. Deleting immediately.")
                             is_expired = True

                        if is_expired:
                            zone_id_for_delete = details.get("zone_id", CF_ZONE_ID)
                            if not zone_id_for_delete:
                                logging.error(f"Cannot schedule DNS deletion for expired rule {hostname}: Zone ID is missing in state and no default CF_ZONE_ID is set.")
                            else:
                                rules_to_delete[hostname] = zone_id_for_delete
                                logging.info(f"Rule for {hostname} in zone {zone_id_for_delete} expired. Scheduling for full deletion.")

            if rules_to_delete:
                logging.info(f"Processing cleanup for hostnames: {list(rules_to_delete.keys())}")
                processed_hostnames_for_cf_update = []
                dns_delete_success_all = True

                for hostname, zone_id in rules_to_delete.items():
                    if tunnel_state.get("id"):
                         logging.info(f"Attempting DNS record deletion for expired rule: {hostname} in zone {zone_id}")
                         if delete_cloudflare_dns_record(zone_id, hostname, tunnel_state["id"]):
                              processed_hostnames_for_cf_update.append(hostname)
                         else:
                              logging.error(f"Failed to delete DNS record for {hostname} in zone {zone_id}. Tunnel config update will proceed, but DNS record may remain stale.")
                              dns_delete_success_all = False
                              processed_hostnames_for_cf_update.append(hostname)
                    else:
                         logging.error(f"Cannot delete DNS for expired rule {hostname}: Missing Tunnel ID.")
                         dns_delete_success_all = False
                         processed_hostnames_for_cf_update.append(hostname)

                if processed_hostnames_for_cf_update:
                    logging.info(f"Attempting Cloudflare tunnel config update after processing DNS deletions for: {processed_hostnames_for_cf_update}")
                    if update_cloudflare_config():
                        logging.info(f"Cloudflare tunnel config updated. Removing rules from local state: {processed_hostnames_for_cf_update}")
                        with state_lock:
                            deleted_count = 0
                            for hostname in processed_hostnames_for_cf_update:
                                if hostname in managed_rules and managed_rules[hostname].get("status") == "pending_deletion":
                                    del managed_rules[hostname]
                                    deleted_count += 1
                                    state_changed_in_cleanup = True
                                else:
                                    logging.warning(f"Rule {hostname} was scheduled for removal but not found or not pending when removing from state.")
                            logging.info(f"Removed {deleted_count} rules from local state.")
                            if state_changed_in_cleanup:
                                save_state()
                    else:
                        logging.error("Failed to update Cloudflare tunnel config during rule cleanup. Rules remain in local state. Will retry on next cycle.")
                else:
                     logging.info("No hostnames eligible for tunnel config update after DNS processing during cleanup.")

            else:
                logging.debug("No expired rules found requiring cleanup.")

        except Exception as e:
            logging.error(f"Error in cleanup task loop: {e}", exc_info=True)

        wait_duration = max(0, next_check_time - time.time())
        stop_event.wait(wait_duration)

    logging.info("Cleanup task stopped.")

def reconcile_state():
    """Compares Docker state, local state, and Cloudflare state, making necessary adjustments."""
    if not docker_client:
        logging.warning("Docker client unavailable, skipping reconciliation.")
        return
    if not tunnel_state.get("id"):
        logging.warning("Tunnel not initialized, skipping reconciliation.")
        return

    logging.info("Starting state reconciliation...")
    needs_cf_update = False
    state_changed_locally = False
    try:
        running_labeled_containers = {}
        try:
             containers = docker_client.containers.list(sparse=False)
             logging.debug(f"[Reconcile] Found {len(containers)} running containers.")
             for c in containers:
                 try:
                     labels = c.labels
                     container_id = c.id
                     container_name = c.name
                     enabled = labels.get(f"{LABEL_PREFIX}.enable", "false").lower() in ["true", "1", "t", "yes"]
                     hostname = labels.get(f"{LABEL_PREFIX}.hostname")
                     service = labels.get(f"{LABEL_PREFIX}.service")
                     zone_name = labels.get(f"{LABEL_PREFIX}.zonename")
                     no_tls_verify = labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]

                     if enabled and hostname and service:
                         if not is_valid_hostname(hostname): continue
                         if not is_valid_service(service): continue

                         if hostname in running_labeled_containers:
                              logging.warning(f"[Reconcile] Duplicate hostname label '{hostname}' found on running containers: {container_name} and {running_labeled_containers[hostname]['container_name']}. Using latest found: {container_name}.")
                         running_labeled_containers[hostname] = {
                             "service": service,
                             "container_id": container_id,
                             "container_name": container_name,
                             "zone_name": zone_name,
                             "no_tls_verify": no_tls_verify
                         }
                 except (NotFound, APIError) as e:
                      logging.warning(f"[Reconcile] Docker error processing container {c.id[:12]}: {e}. Skipping this container.");
                      continue
             logging.info(f"[Reconcile] Found {len(running_labeled_containers)} running containers with valid Dockflare labels.")
        except (APIError, requests.exceptions.ConnectionError) as e:
             logging.error(f"[Reconcile] Docker error listing containers: {e}. Aborting reconciliation.");
             return

        with state_lock:
            logging.debug("[Reconcile] Acquired state lock for comparison.")
            now_utc = datetime.now(timezone.utc)
            managed_hostnames = set(managed_rules.keys())
            running_hostnames = set(running_labeled_containers.keys())
            hostnames_requiring_dns_check = []

            for hostname, running_details in running_labeled_containers.items():
                target_zone_id = get_zone_id_from_name(running_details.get("zone_name")) if running_details.get("zone_name") else CF_ZONE_ID
                if not target_zone_id:
                     logging.error(f"[Reconcile] Skipping management for running container {running_details['container_name']} ({hostname}): No valid Zone ID determined.")
                     continue

                if hostname in managed_rules:
                    rule = managed_rules[hostname]
                    zone_id_changed = rule.get("zone_id") != target_zone_id

                    if rule.get("status") == "pending_deletion":
                        logging.info(f"[Reconcile] Hostname {hostname} is running again, reactivating pending rule.")
                        rule["status"] = "active"; rule["delete_at"] = None
                        rule["service"] = running_details["service"]; rule["container_id"] = running_details["container_id"]
                        rule["zone_id"] = target_zone_id; rule["no_tls_verify"] = running_details["no_tls_verify"]
                        state_changed_locally = True; needs_cf_update = True
                        hostnames_requiring_dns_check.append(hostname)
                        if zone_id_changed: logging.info(f"[Reconcile] Zone ID for reactivated rule {hostname} updated to {target_zone_id}.")
                    elif rule.get("status") == "active":
                        container_changed = rule.get("container_id") != running_details["container_id"]
                        service_changed = rule.get("service") != running_details["service"]
                        no_tls_verify_changed = rule.get("no_tls_verify") != running_details["no_tls_verify"]
                        if container_changed:
                             logging.info(f"[Reconcile] Updating container ID for active rule {hostname}.");
                             rule["container_id"] = running_details["container_id"]; state_changed_locally = True
                        if service_changed:
                             logging.info(f"[Reconcile] Updating service for active rule {hostname}.");
                             rule["service"] = running_details["service"]; state_changed_locally = True; needs_cf_update = True
                        if no_tls_verify_changed:
                             logging.info(f"[Reconcile] Updating noTLSVerify for active rule {hostname}.");
                             rule["no_tls_verify"] = running_details["no_tls_verify"]; state_changed_locally = True; needs_cf_update = True
                        if zone_id_changed:
                             logging.warning(f"[Reconcile] Zone ID for active rule {hostname} changed ('{rule.get('zone_id')}' -> '{target_zone_id}'). Updating state.");
                             rule["zone_id"] = target_zone_id; state_changed_locally = True;
                             hostnames_requiring_dns_check.append(hostname)
                             needs_cf_update = True
                else:
                    logging.info(f"[Reconcile] Found running container for new hostname {hostname}. Adding rule.")
                    managed_rules[hostname] = {
                        "service": running_details["service"], "container_id": running_details["container_id"],
                        "status": "active", "delete_at": None, "zone_id": target_zone_id,
                        "no_tls_verify": running_details["no_tls_verify"]
                    }
                    state_changed_locally = True; needs_cf_update = True
                    hostnames_requiring_dns_check.append(hostname)

            for hostname in list(managed_hostnames):
                if hostname not in running_hostnames:
                     if hostname in managed_rules and managed_rules[hostname].get("status") == "active":
                         logging.info(f"[Reconcile] Rule {hostname} is active in state but no matching container running. Scheduling deletion.")
                         rule = managed_rules[hostname]
                         rule["status"] = "pending_deletion"
                         rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS)
                         state_changed_locally = True

            logging.debug("[Reconcile] Fetching current CF config for final comparison...")
            current_cf_config = get_current_cf_config()
            if current_cf_config is not None:
                cf_ingress_hostnames = {r.get("hostname") for r in current_cf_config.get("ingress", []) if r.get("hostname") and r.get("service") != "http_status:404"}
                active_managed_hostnames = {hn for hn, d in managed_rules.items() if d.get("status") == "active"}

                if cf_ingress_hostnames != active_managed_hostnames:
                     logging.warning(f"[Reconcile] Mismatch detected between locally managed active rules ({len(active_managed_hostnames)}) and Cloudflare tunnel config ({len(cf_ingress_hostnames)})!")
                     logging.info(f"[Reconcile] Hostnames managed locally (active): {sorted(list(active_managed_hostnames))}")
                     logging.info(f"[Reconcile] Hostnames found in Cloudflare config: {sorted(list(cf_ingress_hostnames))}")
                     needs_cf_update = True
                else:
                     logging.debug("[Reconcile] Locally managed active rules match Cloudflare tunnel config.")
            else:
                 logging.error("[Reconcile] Could not fetch current Cloudflare config for comparison.")

            if state_changed_locally:
                logging.info("[Reconcile] Saving local state changes made during reconciliation.")
                save_state()

            logging.debug("[Reconcile] Releasing state lock.")

        if needs_cf_update:
            logging.info("[Reconcile] Triggering Cloudflare tunnel config update based on reconciliation results.")
            if update_cloudflare_config():
                 if hostnames_requiring_dns_check:
                      logging.info(f"[Reconcile] Checking/Creating DNS records for new/reactivated rules: {hostnames_requiring_dns_check}")
                      for hostname in hostnames_requiring_dns_check:
                           rule_details = None
                           with state_lock:
                               rule_details = managed_rules.get(hostname)
                           if rule_details and rule_details.get("zone_id") and tunnel_state.get("id"):
                                if not create_cloudflare_dns_record(rule_details["zone_id"], hostname, tunnel_state["id"]):
                                     logging.error(f"[Reconcile] CRITICAL: Failed DNS check/create for {hostname} in zone {rule_details['zone_id']} after tunnel config update.")
                                else:
                                     logging.debug(f"[Reconcile] DNS check/create successful for {hostname} in zone {rule_details['zone_id']}.")
                           else:
                                logging.error(f"[Reconcile] Cannot check/create DNS for {hostname}: Missing rule details, zone ID, or tunnel ID in current state.")
            else:
                 logging.error("[Reconcile] Failed Cloudflare tunnel config update during reconciliation. DNS checks for new/reactivated rules skipped.")
        elif state_changed_locally:
            logging.info("[Reconcile] Local state changes made (e.g., scheduling deletion), no immediate Cloudflare config update required.")
        else:
            logging.info("[Reconcile] No changes required based on reconciliation.")

    except Exception as e:
        logging.error(f"Unexpected error during state reconciliation: {e}", exc_info=True)
    finally:
        logging.info("Reconciliation complete.")

def get_cloudflared_container():
    """Gets the cloudflared agent container object."""
    if not docker_client:
        logging.warning("Docker client unavailable.")
        return None
    try:
        return docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
    except NotFound:
        logging.debug(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found.")
        return None
    except APIError as e:
        logging.error(f"Docker API error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error get agent: {e}"
        return None
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Docker connection error getting container: {e}")
        cloudflared_agent_state["last_action_status"] = f"Error connect Docker: {e}"
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error unexpected get agent: {e}"
        return None

def update_cloudflared_container_status():
    """Updates the global state with the agent container's current status."""
    global docker_client
    current_status = cloudflared_agent_state.get("container_status")

    if not docker_client:
        if current_status != "docker_unavailable":
            logging.warning("Docker client unavailable, attempting reconnect...")
            try:
                docker_client = docker.from_env(timeout=5)
                docker_client.ping()
                logging.info("Reconnected to Docker daemon.")
                
                new_container = get_cloudflared_container()
                new_status = new_container.status if new_container else "not_found"
                if current_status != new_status:
                     logging.info(f"Agent container '{CLOUDFLARED_CONTAINER_NAME}' status updated post-reconnect: {current_status} -> {new_status}")
                     cloudflared_agent_state["container_status"] = new_status
                return 
            except Exception as e:
                logging.error(f"Failed to reconnect to Docker daemon: {e}")
                if current_status != "docker_unavailable":
                    logging.info(f"Agent container '{CLOUDFLARED_CONTAINER_NAME}' status changed: {current_status} -> docker_unavailable")
                    cloudflared_agent_state["container_status"] = "docker_unavailable"
                docker_client = None
                return
        else:
             
             return

    container = get_cloudflared_container()
    if container:
        try:
            container.reload()
            new_status = container.status
            if current_status != new_status:
                 logging.info(f"Agent container '{CLOUDFLARED_CONTAINER_NAME}' status changed: {current_status} -> {new_status}")
                 cloudflared_agent_state["container_status"] = new_status
                 if new_status == 'running' and cloudflared_agent_state.get("last_action_status"):
                     
                     cloudflared_agent_state["last_action_status"] = None
        except (NotFound, APIError) as e:
             new_status = "not_found"
             if current_status != new_status:
                 logging.warning(f"Error reloading agent container status (assuming 'not_found'): {e}")
                 cloudflared_agent_state["container_status"] = new_status
                 cloudflared_agent_state["last_action_status"] = "Agent container disappeared."
        except requests.exceptions.ConnectionError as e:
             new_status = "docker_unavailable"
             if current_status != new_status:
                 logging.error(f"Docker connection error updating agent status: {e}")
                 cloudflared_agent_state["container_status"] = new_status
             docker_client = None 
             return
        except Exception as e:
             logging.error(f"Unexpected error updating agent status for {container.name}: {e}", exc_info=True)
             
             return
    else:
        
        new_status = "not_found"
        if current_status != new_status and current_status != "docker_unavailable":
            logging.info(f"Agent container '{CLOUDFLARED_CONTAINER_NAME}' not found.")
            cloudflared_agent_state["container_status"] = new_status

def periodic_agent_status_updater():
    """Periodically updates the cloudflared agent status in the background."""
    logging.info("Starting periodic agent status updater task...")
    while not stop_event.is_set():
        try:
            logging.debug("Running periodic agent status update check...")
            update_cloudflared_container_status()
        except Exception as e:
            logging.error(f"Error in periodic agent status updater loop: {e}", exc_info=True)

        stop_event.wait(AGENT_STATUS_UPDATE_INTERVAL_SECONDS)

    logging.info("Periodic agent status updater task stopped.")

def ensure_docker_network_exists(network_name):
     """Checks if the required Docker network exists, creates if not."""
     if not docker_client:
         logging.error("Docker client unavailable, cannot check/create network.")
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
        except APIError as e:
            if "already exists" in str(e):
                logging.warning(f"Network '{network_name}' created concurrently? Treating as success.")
                return True
            logging.error(f"Failed to create Docker network '{network_name}': {e}", exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error create net: {e}"
            return False
        except Exception as e:
             logging.error(f"Unexpected error creating Docker network '{network_name}': {e}", exc_info=True);
             cloudflared_agent_state["last_action_status"] = f"Error: Unexpected create net: {e}"; return False
     except APIError as e:
         logging.error(f"Docker API error checking network '{network_name}': {e}", exc_info=True)
         cloudflared_agent_state["last_action_status"] = f"Error check net: {e}"
         return False
     except requests.exceptions.ConnectionError as e:
         logging.error(f"Docker connection error checking network '{network_name}': {e}")
         cloudflared_agent_state["last_action_status"] = f"Error: Docker connect check net."
         return False
     except Exception as e:
         logging.error(f"Unexpected error checking network '{network_name}': {e}", exc_info=True)
         cloudflared_agent_state["last_action_status"] = f"Error: Unexpected check net: {e}"
         return False

def start_cloudflared_container():
    """Starts or creates the cloudflared agent container."""
    logging.info(f"Attempting to start agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Starting..."
    success_flag = False
    try:
        if not docker_client:
            msg = "Docker client not available."; logging.error(msg)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
        if not tunnel_state.get("token"):
            msg = "Tunnel token not available."; logging.error(msg)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
        if not ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME):
             logging.error(f"Failed network check/create for '{CLOUDFLARED_NETWORK_NAME}'. Cannot start agent.")
             return False

        token = tunnel_state["token"]
        container = get_cloudflared_container()
        needs_recreate = False

        if container:
             try:
                 container.reload()
                 logging.info(f"Found existing container '{CLOUDFLARED_CONTAINER_NAME}' status: {container.status}")
                 if container.status == 'running':
                     msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is already running."; logging.info(msg)
                     cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True

                 current_networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                 network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', 'default')
                 if network_mode == 'host' or network_mode == CLOUDFLARED_NETWORK_NAME:
                     logging.warning(f"Existing container '{CLOUDFLARED_CONTAINER_NAME}' is in an unexpected network mode ('{network_mode}'). Needs recreation.")
                     needs_recreate = True
                 elif CLOUDFLARED_NETWORK_NAME not in current_networks:
                     logging.warning(f"Existing container '{CLOUDFLARED_CONTAINER_NAME}' is not attached to the required network '{CLOUDFLARED_NETWORK_NAME}'. Needs recreation.")
                     needs_recreate = True

                 if needs_recreate:
                      logging.info(f"Removing misconfigured/stopped container '{CLOUDFLARED_CONTAINER_NAME}' before creating a new one...")
                      try:
                          container.remove(force=True)
                          container = None
                      except (APIError, requests.exceptions.ConnectionError) as rm_err:
                           logging.error(f"Failed to remove misconfigured container '{CLOUDFLARED_CONTAINER_NAME}': {rm_err}. Cannot proceed.")
                           cloudflared_agent_state["last_action_status"] = f"Error: Failed remove old agent: {rm_err}"; return False
                 else:
                      logging.info(f"Starting existing stopped container '{CLOUDFLARED_CONTAINER_NAME}'...");
                      container.start()
                      msg = f"Started existing container '{CLOUDFLARED_CONTAINER_NAME}'.";
                      cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

             except (NotFound, APIError) as e:
                  logging.warning(f"Error checking existing container '{CLOUDFLARED_CONTAINER_NAME}': {e}. Assuming creation is needed.");
                  container = None
             except requests.exceptions.ConnectionError as e:
                  logging.error(f"Docker connection error checking existing container: {e}")
                  cloudflared_agent_state["last_action_status"] = f"Error: Docker connect check agent."; return False

        if not container and not success_flag:
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found or needs recreation. Creating...")
            try:
                try:
                    logging.info(f"Pulling image {CLOUDFLARED_IMAGE}...");
                    docker_client.images.pull(CLOUDFLARED_IMAGE);
                    logging.info("Image pull complete.")
                except APIError as img_err:
                    logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Container run will attempt using local image if available.")
                except requests.exceptions.ConnectionError as e:
                    logging.error(f"Docker connection failed during image pull: {e}")
                    cloudflared_agent_state["last_action_status"] = f"Error: Docker connect pull image."; return False

                container_params = {
                    "image": CLOUDFLARED_IMAGE,
                    "command": f"tunnel --no-autoupdate run --token {token}",
                    "name": CLOUDFLARED_CONTAINER_NAME,
                    "network": CLOUDFLARED_NETWORK_NAME,
                    "restart_policy": {"Name": "unless-stopped"},
                    "detach": True,
                    "remove": False,
                    "labels": {"managed-by": "dockflare"}
                }
                new_container = docker_client.containers.run(**container_params)
                msg = f"Successfully created and started container '{new_container.name}' ({new_container.id[:12]})."
                cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

            except APIError as create_err:
                if "is already in use" in str(create_err):
                    logging.error(f"Container name '{CLOUDFLARED_CONTAINER_NAME}' is already in use by another container.")
                    msg = f"Error: Container name '{CLOUDFLARED_CONTAINER_NAME}' conflict. Remove the conflicting container manually and retry."
                else:
                     msg = f"Docker API error creating container: {create_err}"
                     logging.error(msg, exc_info=True)
                cloudflared_agent_state["last_action_status"] = msg; success_flag = False
            except requests.exceptions.ConnectionError as e:
                logging.error(f"Docker connection failed running container: {e}")
                cloudflared_agent_state["last_action_status"] = f"Error: Docker connect run agent."; success_flag = False

    except APIError as e:
        msg = f"Docker API error during start sequence: {e}"; logging.error(msg, exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except requests.exceptions.ConnectionError as e:
        msg = f"Docker connection error during start sequence: {e}"; logging.error(msg)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        msg = f"Unexpected error starting container: {e}"; logging.error(msg, exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        if docker_client:
             logging.debug("Updating agent status after start attempt...");
             time.sleep(2);
             update_cloudflared_container_status()
        logging.info(f"Exiting start_cloudflared_container function (Success: {success_flag}).")
        return success_flag

def stop_cloudflared_container():
    """Stops the cloudflared agent container."""
    logging.info(f"Attempting to stop agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Stopping..."
    success_flag = False
    try:
        if not docker_client:
            msg = "Docker client unavailable."; logging.error(msg)
            cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        container = get_cloudflared_container()
        if not container:
            msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found (already stopped or removed?)."; logging.warning(msg)
            cloudflared_agent_state["last_action_status"] = msg
            if cloudflared_agent_state["container_status"] != "not_found":
                 cloudflared_agent_state["container_status"] = "not_found"
            success_flag = True; return True

        container.reload()
        if container.status != 'running':
            msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is not running (status: {container.status})."; logging.info(msg)
            cloudflared_agent_state["last_action_status"] = msg
            if cloudflared_agent_state["container_status"] != container.status:
                 cloudflared_agent_state["container_status"] = container.status
            success_flag = True; return True

        logging.info(f"Stopping running container '{CLOUDFLARED_CONTAINER_NAME}'...");
        container.stop(timeout=30)
        msg = f"Successfully stopped container '{CLOUDFLARED_CONTAINER_NAME}'.";
        cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

    except (APIError, NotFound) as e:
        msg = f"Docker API error stopping container '{CLOUDFLARED_CONTAINER_NAME}': {e}"; logging.error(msg, exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except requests.exceptions.ConnectionError as e:
        msg = f"Docker connection error stopping container: {e}"; logging.error(msg)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        msg = f"Unexpected error stopping container '{CLOUDFLARED_CONTAINER_NAME}': {e}"; logging.error(msg, exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        if docker_client:
             logging.debug("Updating agent status after stop attempt...");
             time.sleep(2);
             update_cloudflared_container_status()
        logging.info(f"Exiting stop_cloudflared_container function (Success: {success_flag}).")
        return success_flag

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_display_token(token):
    """Returns a truncated token for display."""
    if not token:
        return "Not available"
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token retrieved (short)"

@app.route('/')
def status_page():
    """Renders the main status dashboard page."""
    with state_lock:
        rules_for_template = {}
        for hostname, rule in managed_rules.items():
            rule_copy = copy.deepcopy(rule)
            if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
                 try:
                     rule_copy["delete_at"] = rule_copy["delete_at"].replace(tzinfo=timezone.utc) if rule_copy["delete_at"].tzinfo is None else rule_copy["delete_at"].astimezone(timezone.utc)
                 except Exception as date_parse_err:
                      logging.warning(f"Error preparing delete_at ('{rule_copy['delete_at']}') for template: {date_parse_err}")
                      rule_copy["delete_at"] = None
            rules_for_template[hostname] = rule_copy

        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()

    display_token = get_display_token(template_tunnel_state.get("token"))
    docker_available = docker_client is not None

    return render_template('status_page.html',
                            tunnel_state=template_tunnel_state,
                            agent_state=template_agent_state,
                            display_token=display_token,
                            cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                            docker_available=docker_available,
                            rules=rules_for_template)

@app.route('/start-tunnel', methods=['POST'])
def start_tunnel():
    """Handles request to start the tunnel agent."""
    logging.info("UI request: Start tunnel agent.")
    start_cloudflared_container()
    time.sleep(1)
    return redirect(url_for('status_page'))

@app.route('/stop-tunnel', methods=['POST'])
def stop_tunnel():
    """Handles request to stop the tunnel agent."""
    logging.info("UI request: Stop tunnel agent.")
    stop_cloudflared_container()
    time.sleep(1)
    return redirect(url_for('status_page'))

@app.route('/force_delete_rule/<hostname>', methods=['POST'])
def force_delete_rule(hostname):
    """Handles request to immediately delete a rule and its DNS record."""
    logging.info(f"UI request: Force delete rule for hostname: {hostname}")
    rule_removed_from_state = False
    dns_delete_success = False
    zone_id_for_delete = None

    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details:
            zone_id_for_delete = rule_details.get("zone_id")
        else:
            logging.warning(f"Rule {hostname} not found in state during force delete. Attempting DNS delete in default zone ID ({CF_ZONE_ID}) if available.")
            zone_id_for_delete = CF_ZONE_ID

    if zone_id_for_delete and tunnel_state.get("id"):
        logging.info(f"Attempting immediate DNS record deletion for force-deleted rule: {hostname} in zone {zone_id_for_delete}")
        dns_delete_success = delete_cloudflare_dns_record(zone_id_for_delete, hostname, tunnel_state["id"])
        if not dns_delete_success:
             logging.error(f"Failed immediate DNS delete for {hostname} in zone {zone_id_for_delete}. Tunnel config update will proceed.")
             cloudflared_agent_state["last_action_status"] = f"Warning: Failed DNS delete for {hostname}. Tunnel update proceeding."
    elif not zone_id_for_delete:
        logging.error(f"Cannot delete DNS for {hostname}: Zone ID could not be determined.")
        cloudflared_agent_state["last_action_status"] = f"Error: Cannot delete DNS for {hostname} (missing zone ID)."
    else:
        logging.error(f"Cannot delete DNS for {hostname}: Missing Tunnel ID.")
        cloudflared_agent_state["last_action_status"] = f"Error: Cannot delete DNS for {hostname} (missing tunnel ID)."

    with state_lock:
        if hostname in managed_rules:
            logging.info(f"Force deleting rule for {hostname} from local state.")
            del managed_rules[hostname]
            rule_removed_from_state = True
            save_state()
        else:
            logging.warning(f"Rule '{hostname}' was already removed from state when force delete requested.")
            rule_removed_from_state = True

    if rule_removed_from_state:
        logging.info(f"Triggering Cloudflare tunnel config update after force deleting {hostname}.")
        if update_cloudflare_config():
            logging.info(f"CF tunnel config update successful after force deleting {hostname}.")
            status_msg = f"Successfully force deleted rule for {hostname} and updated Cloudflare."
            if not dns_delete_success:
                status_msg += " (Note: DNS deletion failed or was skipped)."
            cloudflared_agent_state["last_action_status"] = status_msg
        else:
            logging.error(f"CRITICAL: State updated after force delete of {hostname} (DNS delete success: {dns_delete_success}), but subsequent tunnel config update FAILED!")
            cloudflared_agent_state["last_action_status"] = f"Error: Removed {hostname} locally (DNS delete: {dns_delete_success}), but FAILED tunnel config update! Reconciliation needed."

    time.sleep(1)
    return redirect(url_for('status_page'))

@app.route('/stream-logs')
def stream_logs():
    """Streams log messages using Server-Sent Events."""
    @stream_with_context
    def event_stream():
        logging.info("Log stream client connected.")
        yield f"data: --- Log stream connected ---\n\n"
        try:
            while True:
                try:
                    log_entry = log_queue.get(timeout=10)  # Add timeout to prevent indefinite blocking
                    yield f"data: {log_entry}\n\n"
                except queue.Empty:
                    continue  # No log entry, continue waiting
        except GeneratorExit:
            logging.info("Log stream client disconnected.")
        except Exception as e:
            logging.error(f"Unexpected error in log stream: {e}", exc_info=True)
        finally:
            pass
    return Response(event_stream(), mimetype='text/event-stream')

def run_background_tasks():
    """Starts the Docker event listener and cleanup threads."""
    threads = []
    if not docker_client:
        logging.warning("Docker client unavailable. Background tasks (Event Listener, Cleanup) cannot start.")
        return threads 
    if not tunnel_state.get("id"):
        logging.warning("Tunnel not initialized. Background tasks (Event Listener, Cleanup) cannot start.")
        return threads 

    logging.info("Starting background threads (Docker Listener, Cleanup Task)...");
    event_thread = threading.Thread(target=docker_event_listener, name="DockerEventListener", daemon=True)
    cleanup_thread = threading.Thread(target=cleanup_expired_rules, name="CleanupTask", daemon=True)
    event_thread.start()
    cleanup_thread.start()
    threads.extend([event_thread, cleanup_thread])
    logging.info("Event Listener and Cleanup threads started.")
    return threads

if __name__ == '__main__':
    logging.info("-" * 52)
    logging.info("--- Dockflare Starting ---")
    logging.info("-" * 52)

    load_state()
    logging.info("Initial state loading complete.")
    background_threads = []
    agent_status_thread = None

    if not docker_client:
         logging.error("Docker client unavailable at startup. Dockflare will run with limited functionality.")
         tunnel_state["status_message"] = "Error: Docker client unavailable."
         tunnel_state["error"] = "Failed to connect to Docker daemon."
         cloudflared_agent_state["container_status"] = "docker_unavailable"
         logging.warning("Skipping tunnel initialization, reconciliation, agent management, and background tasks due to Docker connection failure.")
    else:
         logging.info("Docker client available.")

         logging.info("Starting periodic agent status updater thread...")
         agent_status_thread = threading.Thread(target=periodic_agent_status_updater, name="AgentStatusUpdater", daemon=True)
         agent_status_thread.start()

         initialize_tunnel()
         logging.info(f"Tunnel initialization complete. Status: {tunnel_state.get('status_message')}")

         if tunnel_state.get("id") and tunnel_state.get("token"):
             logging.info("Tunnel initialized. Proceeding with initial reconciliation & agent checks.")

             reconcile_state()
             logging.info("Initial state reconciliation complete.")

             logging.info("Checking cloudflared agent container status...")
             update_cloudflared_container_status()
             if cloudflared_agent_state.get("container_status") != 'running':
                 logging.info("Agent container not running, attempting auto-start...")
                 start_cloudflared_container()
             else:
                 logging.info(f"Agent container '{CLOUDFLARED_CONTAINER_NAME}' is already running.")

             background_threads = run_background_tasks()
         else:
             logging.warning("Tunnel not fully initialized (missing ID or Token). Skipping reconciliation, agent start, and event/cleanup tasks.")
             if not tunnel_state.get("error"):
                 tunnel_state["status_message"] = "Tunnel setup incomplete (missing ID/Token)."

    logging.info("Starting Flask web server...")
    flask_thread = None
    try:
        from waitress import serve
        flask_thread = threading.Thread(
            target=serve,
            args=(app,),
            kwargs={'host':'0.0.0.0','port':5000},
            daemon=True,
            name="FlaskWaitressServer"
        )
        flask_thread.start()
        logging.info("Flask server started using waitress on 0.0.0.0:5000.")

        while True:
            try:
                all_threads_alive = True
                if flask_thread and not flask_thread.is_alive():
                    logging.error("Flask server thread terminated unexpectedly!")
                    all_threads_alive = False
                if agent_status_thread and not agent_status_thread.is_alive():
                    logging.warning("Agent status updater thread terminated.")
                for bg_thread in background_threads:
                    if bg_thread and not bg_thread.is_alive():
                        logging.warning(f"{bg_thread.name} thread terminated.")

                if not all_threads_alive:
                    logging.error("A critical thread (Flask server) terminated. Initiating shutdown.")
                    stop_event.set()
                    break
                if stop_event.is_set():
                    logging.info("Stop event detected by main thread.")
                    break

                time.sleep(10)
            except Exception as e:
                logging.error(f"Unexpected error in main thread monitoring loop: {e}", exc_info=True)
                stop_event.set()
                break

    except ImportError:
        logging.warning("Waitress not found. Using Flask development server (not recommended for production). Install using: pip install waitress")
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Shutting down...")
    except Exception as server_err:
        logging.error(f"Web server failed unexpectedly: {server_err}", exc_info=True)
    finally:
        logging.info("Shutdown initiated...")
        stop_event.set()
        logging.info("Stop event set for background tasks.")

        logging.info("Exiting Dockflare application.")
        exit_code = 1 if tunnel_state.get("error") or cloudflared_agent_state.get("container_status") == "docker_unavailable" else 0
        sys.exit(exit_code)