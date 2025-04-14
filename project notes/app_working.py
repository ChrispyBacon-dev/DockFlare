import os
import sys
import logging
import re
import json
import threading
import time
from datetime import datetime, timedelta, timezone
import random

import docker
from docker.errors import NotFound, APIError
from flask import Flask, jsonify, render_template_string, redirect, url_for, request
from dotenv import load_dotenv
import requests

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')
load_dotenv()

# Retry Config for CF PUT Tunnel Config
MAX_CF_UPDATE_RETRIES = 3
CF_UPDATE_RETRY_DELAY = 2
CF_UPDATE_BACKOFF_FACTOR = 2

# Cloudflare Config
CF_API_TOKEN = os.getenv('CF_API_TOKEN')
TUNNEL_NAME = os.getenv('TUNNEL_NAME')
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_ZONE_ID = os.getenv('CF_ZONE_ID') # Added Zone ID
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}

# App Config
LABEL_PREFIX = os.getenv('LABEL_PREFIX', 'cloudflare.tunnel')
GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 28800))
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 300))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')

# Cloudflared Agent Config
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"
CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net')

# Environment Variable Checks
if not CF_API_TOKEN or not TUNNEL_NAME or not CF_ACCOUNT_ID or not CF_ZONE_ID: # Added CF_ZONE_ID
    logging.error("FATAL: Missing required environment variables (CF_API_TOKEN, TUNNEL_NAME, CF_ACCOUNT_ID, CF_ZONE_ID)") # Added CF_ZONE_ID
    sys.exit(1)

# Docker Client Setup
try:
    docker_client = docker.from_env(timeout=10)
    docker_client.ping()
    logging.info("Successfully connected to Docker daemon.")
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    docker_client = None

# Global State
tunnel_state = { "name": TUNNEL_NAME, "id": None, "token": None, "status_message": "Initializing...", "error": None }
cloudflared_agent_state = { "container_status": "unknown", "last_action_status": None }
managed_rules = {}
state_lock = threading.Lock()
stop_event = threading.Event()


# --- load_state ---
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
                        rule["delete_at"] = datetime.fromisoformat(rule["delete_at"].replace('Z', '+00:00'))
                     else:
                         dt = datetime.fromisoformat(rule["delete_at"])
                         rule["delete_at"] = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                 except ValueError as date_err:
                     logging.warning(f"Could not parse delete_at for {hostname}: {rule['delete_at']} Error: {date_err}. Setting to None.")
                     rule["delete_at"] = None
             elif not isinstance(rule.get("delete_at"), datetime):
                 rule["delete_at"] = None
        managed_rules = loaded_data
        logging.info(f"Loaded state for {len(managed_rules)} rules from {STATE_FILE_PATH}")
    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Error loading state from {STATE_FILE_PATH}: {e}. Starting fresh.", exc_info=True)
        managed_rules = {}


# --- save_state ---
def save_state():
    serializable_state = {}
    for hostname, rule in managed_rules.items():
        rule_copy = rule.copy()
        if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
            dt_utc = rule_copy["delete_at"].astimezone(timezone.utc)
            rule_copy["delete_at"] = dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
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


# --- cf_api_request ---
def cf_api_request(method, endpoint, json_data=None, params=None):
    url = f"{CF_API_BASE_URL}{endpoint}"
    error_msg = None
    try:
        logging.info(f"API Request: {method} {url} Params: {params} Data: {json_data}")
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
                      if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                           error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                           logging.error(f"API Request Failed ({method} {url}): {error_msg} - Full Errors: {cf_errors}")
                      else:
                           error_msg = f"API reported failure but no error details provided. Response: {response_data}"
                           logging.error(f"API Request Failed ({method} {url}): {error_msg}")
                      raise requests.exceptions.RequestException(error_msg, response=response)
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
                    logging.error(f"Response Body: {error_data}")
                    cf_errors = error_data.get('errors', [])
                    if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                        error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                    else:
                        error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
                except (ValueError, AttributeError, json.JSONDecodeError):
                     error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
            else:
                logging.error(f"Error details (no response received): {e}")

        if "cfd_tunnel" in endpoint and tunnel_state.get("id") is None and "token" not in endpoint:
             tunnel_state["error"] = error_msg
        raise requests.exceptions.RequestException(error_msg, response=e.response)


# --- find_tunnel_via_api ---
def find_tunnel_via_api(name):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"name": name, "is_deleted": "false"}
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])
        if tunnels and isinstance(tunnels, list):
            tunnel = tunnels[0]
            tunnel_id = tunnel.get("id")
            if tunnel_id:
                logging.info(f"Found existing tunnel '{name}' with ID: {tunnel_id} via API.")
                token = get_tunnel_token_via_api(tunnel_id)
                return tunnel_id, token
            else:
                 logging.warning(f"Found tunnel entry for '{name}' but it has no ID in API response: {tunnel}")
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


# --- get_tunnel_token_via_api ---
def get_tunnel_token_via_api(tunnel_id):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    url = f"{CF_API_BASE_URL}{endpoint}"
    try:
        logging.info(f"API Request: GET {url} (for token)")
        response = requests.request("GET", url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"}, timeout=30)
        response.raise_for_status()
        token = response.text.strip()
        if not token or len(token) < 50:
            logging.error(f"Retrieved token for tunnel {tunnel_id} appears invalid (too short or empty).")
            raise ValueError("Invalid token format received from API")
        logging.info(f"Successfully retrieved token via API for tunnel {tunnel_id}")
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


# --- create_tunnel_via_api ---
def create_tunnel_via_api(name):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    payload = {"name": name, "config_src": "cloudflare"}
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        token = result.get("token")
        if not tunnel_id or not token:
            logging.error(f"API response for tunnel creation missing ID or Token: {result}")
            raise ValueError("Missing ID or Token in API response for tunnel creation")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id} via API.")
        return tunnel_id, token
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating tunnel '{name}': {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error creating tunnel '{name}': {e}", exc_info=True)
        tunnel_state["error"] = f"Unexpected error creating tunnel: {e}"
        return None, None


# --- initialize_tunnel ---
def initialize_tunnel():
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
            logging.info(f"Tunnel '{TUNNEL_NAME}' initialized successfully. ID: {tunnel_id}, Token retrieved.")
        elif not tunnel_state.get("error"):
             tunnel_state["status_message"] = "Tunnel initialization failed."
             tunnel_state["error"] = "Failed to find/create tunnel or retrieve token. Check logs."
             logging.error(f"Tunnel initialization failed for '{TUNNEL_NAME}'. Could not get ID and Token.")
        else:
             tunnel_state["status_message"] = "Tunnel initialization failed (see error details)."
             logging.error(f"Tunnel initialization failed for '{TUNNEL_NAME}' due to API error: {tunnel_state['error']}")
    except Exception as e:
        logging.error(f"Unhandled exception during tunnel initialization: {e}", exc_info=True)
        if not tunnel_state.get("error"):
            tunnel_state["error"] = f"Initialization failed unexpectedly: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (unexpected error)."


# --- get_current_cf_config ---
def get_current_cf_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot get CF config, tunnel ID not available.")
        return None
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
    try:
        response_data = cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            result_data = response_data.get("result")
            if isinstance(result_data, dict):
                 config_data = result_data.get("config")
                 if isinstance(config_data, dict):
                     logging.debug(f"Successfully fetched and parsed config: {config_data}")
                     return config_data
                 elif config_data is None:
                     logging.info("Fetched config is null (no configuration set yet). Returning empty config.")
                     return {}
                 else:
                     logging.warning(f"Unexpected type for 'config' field in API response. Expected dict or null, got {type(config_data)}. Response: {response_data}")
                     return {}
            elif result_data is None and response_data.get("success"):
                 logging.info("Fetched config result is null (no configuration set yet). Returning empty config.")
                 return {}
            else:
                logging.warning(f"API response success but 'result' has unexpected format or is missing. Response: {response_data}")
                return {}
        else:
            logging.error(f"get_current_cf_config: cf_api_request did not return success or expected data. Response: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching config for tunnel {tunnel_state['id']}: {e}")
        if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
             tunnel_state["error"] = f"Failed get tunnel config: {e}"
        return None
    except Exception as e:
        logging.error(f"Unexpected exception in get_current_cf_config: {e}", exc_info=True)
        if not tunnel_state.get("error"): tunnel_state["error"] = f"Unexpected error getting tunnel config: {e}"
        return None


# --- find_dns_record_id ---
def find_dns_record_id(zone_id, hostname, tunnel_id):
    if not zone_id or not hostname or not tunnel_id:
        logging.error("find_dns_record_id: Missing required arguments.")
        return None

    expected_content = f"{tunnel_id}.cfargotunnel.com"
    endpoint = f"/zones/{zone_id}/dns_records"
    params = {
        "type": "CNAME",
        "name": hostname,
        "content": expected_content,
        "match": "all"
    }
    try:
        logging.info(f"Searching for DNS record: Type=CNAME, Name={hostname}, Content={expected_content}")
        response_data = cf_api_request("GET", endpoint, params=params)
        results = response_data.get("result", [])
        if results and isinstance(results, list):
            record_id = results[0].get("id")
            if record_id:
                 logging.info(f"Found DNS record for {hostname} with ID: {record_id}")
                 return record_id
            else:
                 logging.warning(f"Found matching DNS record entry for {hostname}, but it lacks an ID: {results[0]}")
                 return None
        else:
            logging.info(f"No matching DNS record found for hostname: {hostname}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding DNS record for {hostname}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error finding DNS record for {hostname}: {e}", exc_info=True)
        return None


# --- create_cloudflare_dns_record ---
def create_cloudflare_dns_record(zone_id, hostname, tunnel_id):
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
        existing_id = find_dns_record_id(zone_id, hostname, tunnel_id)
        if existing_id:
             logging.info(f"DNS CNAME record for {hostname} pointing to {record_content} already exists (ID: {existing_id}). No action needed.")
             return existing_id

        logging.info(f"Creating DNS CNAME record: Name={record_name}, Content={record_content}, Proxied=True")
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        new_record_id = result.get("id")
        if new_record_id:
             logging.info(f"Successfully created DNS record for {hostname}. New ID: {new_record_id}")
             return new_record_id
        else:
             logging.error(f"DNS record creation for {hostname} succeeded according to API status, but no ID was returned in result: {result}")
             return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating DNS record for {hostname}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating DNS record for {hostname}: {e}", exc_info=True)
        return None


# --- delete_cloudflare_dns_record ---
def delete_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    if not zone_id or not hostname or not tunnel_id:
        logging.error("delete_cloudflare_dns_record: Missing required arguments.")
        return False

    dns_record_id = find_dns_record_id(zone_id, hostname, tunnel_id)

    if not dns_record_id:
        logging.warning(f"Could not find DNS record for {hostname} to delete. Assuming already deleted or never created.")
        return True

    logging.info(f"Attempting to delete DNS record for {hostname} (ID: {dns_record_id})")
    endpoint = f"/zones/{zone_id}/dns_records/{dns_record_id}"
    try:
        cf_api_request("DELETE", endpoint)
        logging.info(f"Successfully deleted DNS record for {hostname} (ID: {dns_record_id}).")
        return True
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 404:
             logging.warning(f"Attempted to delete DNS record {dns_record_id} for {hostname}, but API returned 404 (already deleted?). Treating as success.")
             return True
        logging.error(f"API error deleting DNS record {dns_record_id} for {hostname}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error deleting DNS record {dns_record_id} for {hostname}: {e}", exc_info=True)
        return False


# --- update_cloudflare_config ---
def update_cloudflare_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot update Cloudflare config, tunnel ID not available.")
        return False

    final_ingress_rules = None
    needs_api_update = False

    with state_lock:
        logging.info("Preparing potential Cloudflare tunnel configuration update...")
        desired_ingress_rules = []
        catch_all_rule = {"service": "http_status:404"}
        for hostname, rule_details in managed_rules.items():
            if rule_details.get("status") == "active":
                service = rule_details.get("service")
                if service:
                    desired_rule = {"hostname": hostname, "service": service}
                    desired_ingress_rules.append(desired_rule)
                else:
                    logging.warning(f"Managed rule for '{hostname}' is active but missing 'service' detail. Skipping.")

        logging.debug("Fetching current Cloudflare config for comparison...")
        current_config = get_current_cf_config()
        if current_config is None:
            logging.error("Failed to fetch current Cloudflare config within lock, aborting update.")
            return False

        current_cf_ingress = [rule for rule in current_config.get("ingress", [])
                              if rule.get("service") != catch_all_rule["service"]]

        def rule_to_canonical(rule):
            items = sorted([(k, v) for k, v in rule.items() if k in ["hostname", "service"]])
            return tuple(items)

        try:
             current_cf_set = {rule_to_canonical(rule) for rule in current_cf_ingress if rule.get("hostname") and rule.get("service")}
             desired_set = {rule_to_canonical(rule) for rule in desired_ingress_rules if rule.get("hostname") and rule.get("service")}
        except Exception as e:
             logging.error(f"Error creating canonical rule sets for comparison: {e}", exc_info=True)
             return False

        if current_cf_set == desired_set:
            logging.info("No changes detected between managed state and Cloudflare config. Skipping API update.")
            needs_api_update = False
        else:
            logging.info("Change detected. Desired ingress rules differ from current Cloudflare config.")
            logging.debug(f"Current CF rules (non-404, canonical): {current_cf_set}")
            logging.debug(f"Desired rules (from state, canonical): {desired_set}")
            needs_api_update = True
            final_ingress_rules = desired_ingress_rules + [catch_all_rule]

    if needs_api_update and final_ingress_rules is not None:
        endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        payload = {"config": {"ingress": final_ingress_rules}}
        last_exception = None

        for attempt in range(MAX_CF_UPDATE_RETRIES + 1):
            try:
                logging.info(f"Attempting to push config to Cloudflare (Attempt {attempt + 1}/{MAX_CF_UPDATE_RETRIES + 1})...")
                cf_api_request("PUT", endpoint, json_data=payload)

                logging.info("Successfully updated Cloudflare tunnel configuration via API.")
                cloudflared_agent_state["last_action_status"] = f"Cloudflare config updated successfully at {datetime.now(timezone.utc).isoformat()}"
                if tunnel_state.get("error") and ("Failed update tunnel config" in tunnel_state["error"] or "API Error" in tunnel_state["error"]):
                     logging.info(f"Clearing previous API error after successful update: {tunnel_state['error']}")
                     tunnel_state["error"] = None
                return True

            except requests.exceptions.RequestException as e:
                last_exception = e
                status_code = e.response.status_code if e.response is not None else None
                logging.warning(f"Cloudflare API update attempt {attempt + 1} failed: {e} (Status Code: {status_code})")

                is_retryable = False
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    is_retryable = True
                elif status_code in [429, 500, 502, 503, 504]:
                    is_retryable = True

                if is_retryable and attempt < MAX_CF_UPDATE_RETRIES:
                    wait_time = CF_UPDATE_RETRY_DELAY * (CF_UPDATE_BACKOFF_FACTOR ** attempt)
                    if status_code == 429 and e.response is not None:
                         retry_after = e.response.headers.get("Retry-After")
                         if retry_after:
                              try:
                                  retry_after_seconds = int(retry_after)
                                  logging.info(f"Cloudflare API rate limit hit. Respecting Retry-After header: {retry_after_seconds}s")
                                  wait_time = max(wait_time, retry_after_seconds)
                              except ValueError:
                                  logging.warning(f"Could not parse Retry-After header value '{retry_after}'. Using calculated backoff ({wait_time:.1f}s).")
                    logging.info(f"Retrying Cloudflare update in {wait_time:.1f} seconds...")
                    interrupted = stop_event.wait(wait_time)
                    if interrupted:
                         logging.warning("Shutdown requested during Cloudflare update retry wait. Aborting.")
                         cloudflared_agent_state["last_action_status"] = f"Error: CF update aborted during retry (shutdown)."
                         if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
                              tunnel_state["error"] = f"Failed update tunnel config: aborted during retry"
                         return False
                    continue
                else:
                    logging.error(f"Cloudflare API update failed and will not be retried (Retryable: {is_retryable}, Attempt: {attempt + 1}).")
                    break

            except Exception as e:
                 last_exception = e
                 logging.error(f"Unexpected error during Cloudflare API update attempt {attempt + 1}: {e}", exc_info=True)
                 break

        logging.error(f"Failed to update Cloudflare tunnel configuration after {MAX_CF_UPDATE_RETRIES + 1} attempts.")
        error_message = f"Failed update tunnel config after retries: {last_exception}"
        cloudflared_agent_state["last_action_status"] = f"Error: {error_message}"
        if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
             tunnel_state["error"] = error_message
        return False

    elif needs_api_update and final_ingress_rules is None:
         logging.error("Internal error: Needs API update but final_ingress_rules not set.")
         return False
    else:
         return True


# --- process_container_start ---
def process_container_start(container):
    if not container: return
    try:
        container_id = container.id
        try:
             container.reload()
        except NotFound:
             logging.warning(f"Container {container_id[:12]} not found when processing start event (likely stopped quickly).")
             return

        labels = container.labels
        container_name = container.name

        enabled_label = f"{LABEL_PREFIX}.enable"
        hostname_label = f"{LABEL_PREFIX}.hostname"
        service_label = f"{LABEL_PREFIX}.service"

        is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
        hostname = labels.get(hostname_label)
        service = labels.get(service_label)

        if not is_enabled:
            logging.debug(f"Ignoring start event for container {container_name} ({container_id[:12]}): '{enabled_label}' is not 'true'.")
            return
        if not hostname or not service:
            logging.warning(f"Ignoring start event for container {container_name} ({container_id[:12]}): Missing required labels '{hostname_label}' or '{service_label}'.")
            return
        if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$", hostname):
             logging.warning(f"Ignoring start event for container {container_name} ({container_id[:12]}): Invalid hostname format '{hostname}'.")
             return
        if not (re.match(r"^(https?|tcp|unix)://", service) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)):
             logging.warning(f"Ignoring start event for {container_name} ({container_id[:12]}): Invalid service format '{service}'. Needs scheme (http/https/tcp/unix) or be host_or_container_name:port.")
             return

        logging.info(f"Detected start for managed container: {container_name} ({container_id[:12]}) - Hostname: {hostname}, Service: {service}")
        needs_cf_update = False
        state_changed_locally = False

        with state_lock:
            existing_rule = managed_rules.get(hostname)
            if existing_rule:
                if existing_rule.get("status") == "pending_deletion":
                    logging.info(f"Rule for {hostname} was pending deletion. Reactivating.")
                    existing_rule["status"] = "active"
                    existing_rule["delete_at"] = None
                    existing_rule["service"] = service
                    existing_rule["container_id"] = container_id
                    state_changed_locally = True
                    needs_cf_update = True
                elif existing_rule.get("status") == "active":
                    service_changed = existing_rule.get("service") != service
                    if existing_rule.get("container_id") != container_id:
                        logging.info(f"Updating container ID for active rule {hostname}: '{existing_rule.get('container_id', 'N/A')[:12]}' -> '{container_id[:12]}'.")
                        existing_rule["container_id"] = container_id
                        state_changed_locally = True
                    if service_changed:
                         logging.info(f"Updating service for active rule {hostname}: '{existing_rule.get('service')}' -> '{service}'.")
                         existing_rule["service"] = service
                         state_changed_locally = True
                         needs_cf_update = True
                    elif not state_changed_locally:
                         logging.info(f"Container start event for {hostname}, but rule is already active with same details.")
            else:
                logging.info(f"Adding new active rule for hostname: {hostname}")
                managed_rules[hostname] = {
                    "service": service,
                    "container_id": container_id,
                    "status": "active",
                    "delete_at": None
                }
                state_changed_locally = True
                needs_cf_update = True

            if state_changed_locally:
                logging.debug(f"Local state changed for {hostname}, saving state file...")
                save_state()

        if needs_cf_update:
            logging.info(f"Triggering Cloudflare config update due to change for {hostname}.")
            if update_cloudflare_config():
                logging.info(f"Tunnel config update successful for {hostname}.")
                if tunnel_state.get("id") and CF_ZONE_ID:
                    dns_record_id = create_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"])
                    if dns_record_id:
                         logging.info(f"DNS record management successful for {hostname}.")
                    else:
                         logging.error(f"CRITICAL: Tunnel config updated for {hostname} but failed to create/verify DNS record!")
                         cloudflared_agent_state["last_action_status"] = f"Error: Failed creating DNS record for {hostname} after tunnel update."
                else:
                     logging.error("Missing Tunnel ID or Zone ID - cannot manage DNS record.")
            else:
                logging.error(f"Failed to update Cloudflare tunnel config after processing start for {hostname}. DNS record not managed.")
        elif state_changed_locally:
             logging.debug(f"Local state updated for {hostname} (e.g., container ID), no Cloudflare config change needed.")
    except NotFound:
        logging.warning(f"Container {container_id[:12] if 'container_id' in locals() else 'Unknown'} not found during start processing.")
    except APIError as e:
        logging.error(f"Docker API error processing container start ({container_id[:12] if 'container_id' in locals() else 'Unknown'}): {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error processing container start ({container_id[:12] if 'container_id' in locals() else 'Unknown'}): {e}", exc_info=True)


# --- schedule_container_stop ---
def schedule_container_stop(container_id):
    if not container_id: return
    logging.info(f"Processing stop event for container {container_id[:12]}. Checking for managed rules.")
    hostname_to_schedule = None
    state_changed = False
    with state_lock:
        for hn, details in managed_rules.items():
            if details.get("container_id") == container_id and details.get("status") == "active":
                hostname_to_schedule = hn
                break
        if hostname_to_schedule:
            logging.info(f"Container {container_id[:12]} managed active rule for {hostname_to_schedule}. Marking for deletion.")
            rule = managed_rules[hostname_to_schedule]
            if rule.get("status") != "pending_deletion":
                 rule["status"] = "pending_deletion"
                 rule["delete_at"] = datetime.now(timezone.utc) + timedelta(seconds=GRACE_PERIOD_SECONDS)
                 logging.info(f"Rule for {hostname_to_schedule} scheduled for deletion at {rule['delete_at'].isoformat()}")
                 state_changed = True
            else:
                 logging.info(f"Rule for {hostname_to_schedule} was already pending deletion.")
        else:
            logging.info(f"Stop event for container {container_id[:12]}, but it didn't manage any active rule in the current state.")
        if state_changed:
            save_state()


# --- docker_event_listener ---
def docker_event_listener():
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
                    logging.info("Stop event received, exiting Docker event listener loop.")
                    break
                ev_type = event.get("Type")
                action = event.get("Action")
                actor = event.get("Actor", {})
                cont_id = actor.get("ID")
                logging.debug(f"Docker Event: Type={ev_type}, Action={action}, ActorID={cont_id[:12] if cont_id else 'N/A'}")
                if ev_type == "container" and cont_id:
                    if action == "start":
                        try:
                            container = docker_client.containers.get(cont_id)
                            process_container_start(container)
                        except NotFound:
                            logging.warning(f"Container {cont_id[:12]} not found shortly after 'start' event.")
                        except APIError as e:
                             logging.error(f"Docker API error getting container {cont_id[:12]} after start event: {e}")
                        except Exception as e:
                             logging.error(f"Error processing start event for {cont_id[:12]}: {e}", exc_info=True)
                    elif action in ["stop", "die", "destroy", "kill"]:
                         try:
                             schedule_container_stop(cont_id)
                         except Exception as e:
                             logging.error(f"Error processing stop/die/destroy/kill event for {cont_id[:12]}: {e}", exc_info=True)
        except requests.exceptions.ConnectionError as e:
             error_count += 1
             logging.error(f"Connection error with Docker daemon in event listener: {e}. Attempting reconnect ({error_count}/{max_errors})...")
             stop_event.wait(5 * error_count)
        except APIError as e:
             error_count += 1
             logging.error(f"Docker API error in event listener stream: {e}. Attempting reconnect ({error_count}/{max_errors})...")
             stop_event.wait(5 * error_count)
        except Exception as e:
             error_count += 1
             logging.error(f"Unexpected error in Docker event listener: {e}. Attempting reconnect ({error_count}/{max_errors})...", exc_info=True)
             stop_event.wait(5 * error_count)
        if stop_event.is_set(): break
    if error_count >= max_errors:
         logging.error("Docker event listener stopping after multiple connection/API errors.")
    logging.info("Docker event listener stopped.")


# --- cleanup_expired_rules ---
def cleanup_expired_rules():
    logging.info("Starting cleanup task...")
    while not stop_event.is_set():
        next_check_time = time.time() + CLEANUP_INTERVAL_SECONDS
        try:
            logging.debug("Running cleanup check for expired rules...")
            hostnames_to_process_for_deletion = []
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
                                 logging.info(f"Rule for {hostname} deletion grace period expired ({delete_at_utc.isoformat()}). Scheduling for full deletion.")
                                 is_expired = True
                        else:
                             logging.warning(f"Rule {hostname} is pending_deletion but delete_at is invalid or missing: {delete_at}. Scheduling for immediate full deletion.")
                             is_expired = True
                        if is_expired:
                             hostnames_to_process_for_deletion.append(hostname)

            if hostnames_to_process_for_deletion:
                logging.info(f"Processing cleanup for: {hostnames_to_process_for_deletion}")
                processed_hostnames = []
                dns_delete_success_all = True
                for hostname in hostnames_to_process_for_deletion:
                    if tunnel_state.get("id") and CF_ZONE_ID:
                         logging.info(f"Attempting DNS record deletion for expired rule: {hostname}")
                         if not delete_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"]):
                              logging.error(f"Failed to delete DNS record for {hostname}. Tunnel config update will proceed, but DNS record may remain stale.")
                              dns_delete_success_all = False
                    else:
                         logging.error(f"Cannot delete DNS for {hostname}: Missing Tunnel ID or Zone ID.")
                         dns_delete_success_all = False
                    processed_hostnames.append(hostname)

                if processed_hostnames:
                    logging.info(f"Attempting Cloudflare tunnel config update to remove rules: {processed_hostnames}")
                    if update_cloudflare_config():
                        logging.info(f"Cloudflare tunnel config updated successfully. Removing rules from local state: {processed_hostnames}")
                        with state_lock:
                            deleted_count = 0
                            for hostname in processed_hostnames:
                                if hostname in managed_rules and managed_rules[hostname].get("status") == "pending_deletion":
                                    del managed_rules[hostname]
                                    deleted_count += 1
                                    state_changed_in_cleanup = True
                                else:
                                    logging.warning(f"Rule {hostname} was scheduled for removal but not found or no longer 'pending_deletion' when removing from state.")
                            logging.info(f"Removed {deleted_count} rules from local state.")
                            if state_changed_in_cleanup:
                                save_state()
                    else:
                        logging.error("Failed to update Cloudflare tunnel config during rule cleanup. Rules remain in local state and potentially in Cloudflare. Will retry on next cleanup/reconcile cycle.")
                else:
                     logging.info("No hostnames ended up being processed for deletion.")

            else:
                logging.debug("No expired rules found requiring cleanup.")
        except Exception as e:
            logging.error(f"Error in cleanup task loop: {e}", exc_info=True)
        wait_time = max(0, next_check_time - time.time())
        stop_event.wait(wait_time)
    logging.info("Cleanup task stopped.")


# --- reconcile_state ---
def reconcile_state():
    if not docker_client:
        logging.warning("Docker client unavailable, skipping reconciliation.")
        return
    if not tunnel_state.get("id"):
        logging.warning("Tunnel not initialized (no ID), skipping reconciliation.")
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
                     enabled_label = f"{LABEL_PREFIX}.enable"
                     hostname_label = f"{LABEL_PREFIX}.hostname"
                     service_label = f"{LABEL_PREFIX}.service"
                     is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
                     hostname = labels.get(hostname_label)
                     service = labels.get(service_label)
                     if is_enabled and hostname and service:
                         if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$", hostname): continue
                         if not (re.match(r"^(https?|tcp|unix)://", service) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)): continue
                         if hostname in running_labeled_containers:
                              logging.warning(f"[Reconcile] Duplicate hostname label '{hostname}' found on container {container_name} ({container_id[:12]}) and container {running_labeled_containers[hostname]['container_name']} ({running_labeled_containers[hostname]['container_id'][:12]}). Using the latest one found ({container_name}).")
                         running_labeled_containers[hostname] = {
                             "service": service, "container_id": container_id, "container_name": container_name
                         }
                 except NotFound:
                      logging.warning(f"[Reconcile] Container {c.id[:12]} listed but then not found during processing. Skipping.")
                      continue
                 except APIError as e:
                      logging.error(f"[Reconcile] Docker API error processing container {c.id[:12]}: {e}. Skipping.")
                      continue
             logging.info(f"[Reconcile] Found {len(running_labeled_containers)} running containers with valid labels.")
        except APIError as e:
             logging.error(f"[Reconcile] Docker API error listing containers: {e}. Aborting reconciliation.")
             return
        except requests.exceptions.ConnectionError as e:
             logging.error(f"[Reconcile] Failed to connect to Docker daemon while listing containers: {e}. Aborting reconciliation.")
             return

        with state_lock:
            logging.debug("[Reconcile] Acquired state lock.")
            now_utc = datetime.now(timezone.utc)
            managed_hostnames = set(managed_rules.keys())
            running_hostnames = set(running_labeled_containers.keys())
            hostnames_requiring_dns_check_on_reactivate = []

            for hostname, running_details in running_labeled_containers.items():
                if hostname in managed_rules:
                    rule = managed_rules[hostname]
                    if rule.get("status") == "pending_deletion":
                        logging.info(f"[Reconcile] Hostname {hostname} is running but rule was pending deletion. Reactivating.")
                        rule["status"] = "active"; rule["delete_at"] = None; rule["service"] = running_details["service"]; rule["container_id"] = running_details["container_id"]
                        state_changed_locally = True; needs_cf_update = True
                        hostnames_requiring_dns_check_on_reactivate.append(hostname)
                    elif rule.get("status") == "active":
                         container_changed = rule.get("container_id") != running_details["container_id"]
                         service_changed = rule.get("service") != running_details["service"]
                         if container_changed:
                             logging.info(f"[Reconcile] Updating container ID for active rule {hostname}.")
                             rule["container_id"] = running_details["container_id"]; state_changed_locally = True
                         if service_changed:
                              logging.info(f"[Reconcile] Updating service for active rule {hostname}.")
                              rule["service"] = running_details["service"]; state_changed_locally = True; needs_cf_update = True
                else:
                    logging.info(f"[Reconcile] Found running container for {hostname} but no managed rule. Adding new rule.")
                    managed_rules[hostname] = {"service": running_details["service"], "container_id": running_details["container_id"], "status": "active", "delete_at": None}
                    state_changed_locally = True; needs_cf_update = True
                    hostnames_requiring_dns_check_on_reactivate.append(hostname)

            for hostname in list(managed_hostnames):
                if hostname not in running_hostnames:
                     if hostname in managed_rules:
                         rule = managed_rules[hostname]
                         if rule.get("status") == "active":
                              logging.info(f"[Reconcile] Managed rule {hostname} is active but no container found running. Scheduling deletion.")
                              rule["status"] = "pending_deletion"; rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS); state_changed_locally = True

            logging.debug("[Reconcile] Fetching current CF config for final comparison...")
            current_cf_config = get_current_cf_config()
            if current_cf_config is not None:
                cf_ingress_hostnames = {r.get("hostname") for r in current_cf_config.get("ingress", []) if r.get("hostname") and r.get("service") != "http_status:404"}
                active_managed_hostnames = {hn for hn, d in managed_rules.items() if d.get("status") == "active"}
                if cf_ingress_hostnames != active_managed_hostnames:
                     logging.warning(f"[Reconcile] Mismatch detected between active managed rules ({len(active_managed_hostnames)}) and Cloudflare tunnel config ({len(cf_ingress_hostnames)})!")
                     logging.info(f"[Reconcile] Active Managed State: {sorted(list(active_managed_hostnames))}")
                     logging.info(f"[Reconcile] Found in Cloudflare Tunnel Config: {sorted(list(cf_ingress_hostnames))}")
                     logging.info("[Reconcile] Marking for Cloudflare tunnel config update to enforce local state.")
                     needs_cf_update = True
            else:
                logging.error("[Reconcile] Could not fetch Cloudflare config during reconciliation. Skipping final tunnel config comparison.")

            if state_changed_locally:
                logging.info("[Reconcile] Local state changed during reconciliation. Saving state file.")
                save_state()
            logging.debug("[Reconcile] Releasing state lock.")

        if needs_cf_update:
            logging.info("[Reconcile] Triggering Cloudflare tunnel config update based on reconciliation results.")
            if update_cloudflare_config():
                 if hostnames_requiring_dns_check_on_reactivate:
                      logging.info(f"[Reconcile] Checking/Creating DNS records for newly active rules: {hostnames_requiring_dns_check_on_reactivate}")
                      for hostname in hostnames_requiring_dns_check_on_reactivate:
                           if tunnel_state.get("id") and CF_ZONE_ID:
                                if not create_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"]):
                                     logging.error(f"[Reconcile] Failed to ensure DNS record exists for reactivated/new rule {hostname} after successful tunnel config update.")
                           else:
                                logging.error(f"[Reconcile] Cannot check/create DNS for {hostname}: Missing Tunnel ID or Zone ID.")
            else:
                logging.error("[Reconcile] Failed to update Cloudflare tunnel config during reconciliation. DNS checks for reactivated rules skipped.")
        elif state_changed_locally:
            logging.info("[Reconcile] Reconciliation resulted in local state changes only (no CF tunnel config update needed).")
        else:
            logging.info("[Reconcile] No changes required by reconciliation.")
    except Exception as e:
        logging.error(f"Unexpected error during state reconciliation: {e}", exc_info=True)
    finally:
        logging.info("Reconciliation complete.")


# --- get_cloudflared_container ---
def get_cloudflared_container():
    if not docker_client:
        logging.warning("Docker client not available when trying to get cloudflared container.")
        return None
    try:
        return docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
    except NotFound:
        logging.debug(f"Cloudflared container '{CLOUDFLARED_CONTAINER_NAME}' not found.")
        return None
    except APIError as e:
        logging.error(f"Docker API error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker API error getting agent: {e}"
        return None
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Failed to connect to Docker daemon while getting container: {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed getting agent: {e}"
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected error getting agent: {e}"
        return None


# --- update_cloudflared_container_status ---
def update_cloudflared_container_status():
    global docker_client
    if not docker_client:
        logging.warning("Docker client unavailable, attempting to reconnect...")
        try:
            docker_client = docker.from_env(timeout=5)
            docker_client.ping()
            logging.info("Successfully reconnected to Docker daemon.")
            if cloudflared_agent_state["container_status"] == "docker_unavailable":
                 cloudflared_agent_state["container_status"] = "unknown"
        except Exception as e:
             logging.error(f"Failed to reconnect to Docker daemon: {e}")
             if cloudflared_agent_state["container_status"] != "docker_unavailable":
                 logging.warning("Setting agent status to docker_unavailable.")
                 cloudflared_agent_state["container_status"] = "docker_unavailable"
             docker_client = None
             return

    container = get_cloudflared_container()
    if container:
        try:
            container.reload()
            new_status = container.status
            if cloudflared_agent_state["container_status"] != new_status:
                 logging.info(f"Cloudflared agent container status changed to: {new_status}")
                 cloudflared_agent_state["container_status"] = new_status
                 if new_status == 'running': cloudflared_agent_state["last_action_status"] = None
        except (NotFound, APIError) as e:
            if cloudflared_agent_state["container_status"] != "not_found":
                 logging.warning(f"Error reloading cloudflared container status (container likely removed): {e}")
                 cloudflared_agent_state["container_status"] = "not_found"
                 cloudflared_agent_state["last_action_status"] = "Agent container disappeared."
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Failed to connect to Docker daemon during status update: {e}")
            cloudflared_agent_state["container_status"] = "docker_unavailable"
            docker_client = None
            return
    else:
        current_status = cloudflared_agent_state.get("container_status", "unknown")
        if current_status not in ["not_found", "docker_unavailable"]:
            logging.info("Cloudflared agent container not found.")
            cloudflared_agent_state["container_status"] = "not_found"


# --- ensure_docker_network_exists ---
def ensure_docker_network_exists(network_name):
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
                 logging.warning(f"Docker network '{network_name}' already exists (created concurrently?).")
                 return True
            logging.error(f"Failed to create Docker network '{network_name}': {e}", exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error creating network: {e}"
            return False
    except APIError as e:
        logging.error(f"Error checking for Docker network '{network_name}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error checking network: {e}"
        return False
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Failed to connect to Docker daemon checking network '{network_name}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed checking network."
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking/creating Docker network '{network_name}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected error checking network: {e}"
        return False


# --- start_cloudflared_container ---
def start_cloudflared_container():
    logging.info(f"Attempting to start cloudflared agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Starting..."
    success_flag = False
    try:
        if not docker_client:
             msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
        if not tunnel_state.get("token"):
             msg = "Tunnel token not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        if not ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME):
             msg = f"Failed to ensure Docker network '{CLOUDFLARED_NETWORK_NAME}' exists. Cannot start agent."
             logging.error(msg); return False

        token = tunnel_state["token"]
        container = get_cloudflared_container()

        needs_recreate = False
        if container:
             try:
                 container.reload()
                 logging.info(f"Found existing container '{CLOUDFLARED_CONTAINER_NAME}' with status: {container.status}")
                 if container.status == 'running':
                      msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is already running."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True

                 current_networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                 network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', 'default')
                 if network_mode == 'host':
                      logging.warning(f"Existing container '{CLOUDFLARED_CONTAINER_NAME}' is incorrectly in 'host' network mode. Needs recreation.")
                      needs_recreate = True
                 elif CLOUDFLARED_NETWORK_NAME not in current_networks:
                      logging.warning(f"Existing container '{CLOUDFLARED_CONTAINER_NAME}' is not connected to the desired network '{CLOUDFLARED_NETWORK_NAME}'. Needs recreation.")
                      needs_recreate = True

                 if needs_recreate:
                      logging.info(f"Removing misconfigured container '{CLOUDFLARED_CONTAINER_NAME}' before creating a new one.")
                      try: container.remove(force=True)
                      except APIError as rm_err:
                           logging.error(f"Failed to remove misconfigured container: {rm_err}. Proceeding to create might fail.")
                      container = None
                 else:
                      logging.info(f"Starting existing correctly configured container '{CLOUDFLARED_CONTAINER_NAME}'..."); container.start(); msg = f"Started existing container '{CLOUDFLARED_CONTAINER_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True
             except (NotFound, APIError) as e:
                  logging.warning(f"Error checking existing container '{CLOUDFLARED_CONTAINER_NAME}': {e}. Assuming it needs creation.")
                  container = None
             except requests.exceptions.ConnectionError as e:
                  logging.error(f"Failed to connect to Docker daemon checking existing container: {e}")
                  cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed checking agent."
                  return False

        if not container and not success_flag:
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found or needs creation. Creating...")
            try:
                try:
                    logging.info(f"Pulling image {CLOUDFLARED_IMAGE}...");
                    docker_client.images.pull(CLOUDFLARED_IMAGE)
                except APIError as img_err:
                    logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Docker run will attempt to pull.")
                except requests.exceptions.ConnectionError as e:
                    logging.error(f"Failed to connect to Docker daemon during image pull: {e}")
                    cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed pulling image."
                    return False

                new_container = docker_client.containers.run(
                    image=CLOUDFLARED_IMAGE,
                    command=f"tunnel --no-autoupdate run --token {token}",
                    name=CLOUDFLARED_CONTAINER_NAME,
                    network=CLOUDFLARED_NETWORK_NAME,
                    restart_policy={"Name": "unless-stopped"},
                    detach=True,
                    remove=False,
                    labels={"managed-by": "cloudflare-tunnel-ingress-controller"}
                )
                msg = f"Created and started container '{new_container.name}' on network '{CLOUDFLARED_NETWORK_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True
            except APIError as create_err:
                if "is already in use" in str(create_err):
                     logging.error(f"Container name '{CLOUDFLARED_CONTAINER_NAME}' is already in use. Attempting to remove existing...")
                     try:
                          stale_container = docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
                          stale_container.remove(force=True)
                          logging.info("Removed stale container. Please try starting the agent again.")
                          msg = f"Error: Container name conflict, removed stale container. Please retry start."
                     except (NotFound, APIError, requests.exceptions.ConnectionError) as rm_err:
                          logging.error(f"Failed to remove stale container '{CLOUDFLARED_CONTAINER_NAME}': {rm_err}")
                          msg = f"Error: Docker API error creating container: {create_err} (and failed to remove stale)"
                else:
                     msg = f"Docker API error creating container: {create_err}"; logging.error(msg, exc_info=True)
                cloudflared_agent_state["last_action_status"] = msg; success_flag = False
            except requests.exceptions.ConnectionError as e:
                 logging.error(f"Failed to connect to Docker daemon during container run: {e}")
                 cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed running agent."
                 success_flag = False
    except APIError as e:
        msg = f"Docker API error during start sequence: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except requests.exceptions.ConnectionError as e:
        msg = f"Failed to connect to Docker daemon during start sequence: {e}"; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        msg = f"Unexpected error starting container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        if docker_client:
             logging.debug("Updating container status after start attempt...")
             time.sleep(2)
             update_cloudflared_container_status()
        logging.info(f"Exiting start_cloudflared_container function (Success: {success_flag}).")
        return success_flag


# --- stop_cloudflared_container ---
def stop_cloudflared_container():
    logging.info(f"Attempting to stop cloudflared agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Stopping..."
    success_flag = False
    try:
        if not docker_client:
            msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
        container = get_cloudflared_container()
        if not container:
            msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found, cannot stop."; logging.warning(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True
        container.reload()
        if container.status != 'running':
             msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is not running (status: {container.status}). No action needed."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True
        logging.info(f"Stopping running container '{CLOUDFLARED_CONTAINER_NAME}'..."); container.stop(timeout=30); msg = f"Successfully stopped container '{CLOUDFLARED_CONTAINER_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True
    except APIError as e:
        msg = f"Docker API error stopping container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except requests.exceptions.ConnectionError as e:
        msg = f"Failed to connect to Docker daemon stopping container: {e}"; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        msg = f"Unexpected error stopping container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        if docker_client:
             logging.debug("Updating container status after stop attempt..."); time.sleep(2); update_cloudflared_container_status()
        logging.info(f"Exiting stop_cloudflared_container function (Success: {success_flag}).")
        return success_flag

# Flask App Setup
app = Flask(__name__)
app.secret_key = os.urandom(24)


# --- get_display_token ---
def get_display_token(token):
    if not token: return "Not available"
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token retrieved (short)"


# --- status_page ---
@app.route('/')
def status_page():
    update_cloudflared_container_status()
    with state_lock:
        template_rules = json.loads(json.dumps(managed_rules, default=str))
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()
    display_token = get_display_token(template_tunnel_state.get("token"))
    docker_available = docker_client is not None
    html_template = """<!DOCTYPE html><html><head><title>Cloudflare Tunnel Manager</title><meta http-equiv="refresh" content="30"><style>body{font-family:sans-serif;padding:20px;background-color:#f4f4f4;color:#333}h1,h2,h3{color:#555}.container{background-color:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);margin-bottom:20px}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}th{background-color:#f2f2f2}td pre{margin:0;background-color:transparent;padding:0;white-space:pre-wrap;word-break:break-all; font-family: monospace; font-size: 0.9em;}.status-box{padding:10px;border:1px solid #ccc;border-radius:5px;margin-top:10px;word-wrap:break-word}.error{background-color:#ffebeb;border-color:#ffc2c2;color:#a00}.success{background-color:#e6ffed;border-color:#c3e6cb;color:#155724}.info{background-color:#e7f3fe;border-color:#b8daff;color:#004085}.warning{background-color:#fff3cd;border-color:#ffeeba;color:#856404}.status-active{color:green}.status-pending{color:orange}.button{padding:10px 15px;border:none;border-radius:4px;color:#fff;cursor:pointer;font-size:1em;margin-right:10px}.small-button{padding:5px 10px;font-size:.9em}.start-button{background-color:#28a745}.stop-button{background-color:#dc3545}.delete-button{background-color:#dc3545}.button:disabled{background-color:#ccc;cursor:not-allowed;opacity:.6}form{display:inline-block;margin:0}</style></head><body><h1>Cloudflare Tunnel Manager</h1><div class="container"><h2>Initialization Status</h2><div class="status-box {{'error' if tunnel_state.get('error') else ('success' if tunnel_state.get('token') else 'info')}}"><p><strong>Message:</strong> {{tunnel_state.status_message}}</p>{% if tunnel_state.get('error') %}<p><strong>Error Details:</strong> <pre>{{tunnel_state.error}}</pre></p>{% endif %}</div><h3>Tunnel Details</h3><p><strong>Desired Tunnel Name:</strong> <pre>{{tunnel_state.name}}</pre></p><p><strong>Tunnel ID:</strong> <pre>{{tunnel_state.id if tunnel_state.id else 'Not available'}}</pre></p><p><strong>Tunnel Token:</strong> <pre>{{display_token}}</pre></p></div><div class="container"><h2>Tunnel Agent Control (<pre>{{cloudflared_container_name}}</pre>)</h2><p><strong>Agent Container Status:</strong> <strong style="text-transform:capitalize" class="{{'success' if agent_state.container_status=='running' else ('error' if 'error' in agent_state.container_status or agent_state.container_status=='docker_unavailable' or agent_state.container_status=='dead' else ('warning' if agent_state.container_status=='exited' or agent_state.container_status=='not_found' else 'info'))}}">{{agent_state.container_status.replace('_',' ')}}</strong></p>{% if agent_state.last_action_status %}<div class="status-box {{'error' if 'Error:' in agent_state.last_action_status else ('warning' if 'Warning:' in agent_state.last_action_status else 'info')}}"><strong>Last Action Result:</strong> {{agent_state.last_action_status}}</div>{% endif %}<form action="{{url_for('start_tunnel')}}" method="post" style="margin-right:10px"><button type="submit" class="button start-button" {{'disabled' if not tunnel_state.get('token') or agent_state.container_status=='running' or not docker_available }}>Start Tunnel Agent</button></form><form action="{{url_for('stop_tunnel')}}" method="post"><button type="submit" class="button stop-button" {{'disabled' if agent_state.container_status!='running' or not docker_available }}>Stop Tunnel Agent</button></form></div><div class="container"><h2>Managed Ingress Rules</h2>{% if rules %}<table><thead><tr><th>Hostname</th><th>Service Target</th><th>Status</th><th>Managing Container ID</th><th>Delete Scheduled At (UTC)</th><th>Actions</th></tr></thead><tbody>{% for hostname, details in rules.items() %}<tr><td><pre>{{hostname}}</pre></td><td><pre>{{details.service}}</pre></td><td><strong class="{{'status-active' if details.status=='active' else 'status-pending'}}">{{details.status}}</strong></td><td><pre>{{details.container_id[:12] if details.container_id else 'N/A'}}</pre></td><td>{{details.delete_at if details.status=='pending_deletion' else 'N/A'}}</td><td><form action="{{url_for('force_delete_rule', hostname=hostname)}}" method="post" onsubmit="return confirm('Are you sure you want to force delete the rule and DNS record for {{hostname}} immediately?');"><button type="submit" class="button delete-button small-button" {{ 'disabled' if not docker_available }}>Force Delete</button></form></td></tr>{% endfor %}</tbody></table>{% else %}<p>No ingress rules are currently being managed.</p>{% endif %}</div></body></html>"""
    return render_template_string(html_template,
                                tunnel_state=template_tunnel_state,
                                agent_state=template_agent_state,
                                display_token=display_token,
                                cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                                docker_available=docker_available,
                                rules=template_rules)


# --- start_tunnel ---
@app.route('/start', methods=['POST'])
def start_tunnel():
    logging.info("Received request to start tunnel agent via UI.")
    start_cloudflared_container()
    time.sleep(1)
    return redirect(url_for('status_page'))


# --- stop_tunnel ---
@app.route('/stop', methods=['POST'])
def stop_tunnel():
    logging.info("Received request to stop tunnel agent via UI.")
    stop_cloudflared_container()
    time.sleep(1)
    return redirect(url_for('status_page'))


# --- force_delete_rule ---
@app.route('/force_delete/<hostname>', methods=['POST'])
def force_delete_rule(hostname):
    logging.info(f"Received request to force delete rule for hostname: {hostname}")
    rule_removed_from_state = False
    dns_delete_success = False

    if tunnel_state.get("id") and CF_ZONE_ID:
        logging.info(f"Attempting DNS record deletion for force-deleted rule: {hostname}")
        dns_delete_success = delete_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"])
        if not dns_delete_success:
             logging.error(f"Failed to delete DNS record for {hostname} during force delete. Tunnel config update will proceed, but DNS record may remain stale.")
             cloudflared_agent_state["last_action_status"] = f"Warning: Failed deleting DNS record for {hostname}. Tunnel update proceeding."
    else:
        logging.error(f"Cannot delete DNS for {hostname}: Missing Tunnel ID or Zone ID.")
        cloudflared_agent_state["last_action_status"] = f"Error: Cannot delete DNS for {hostname} (missing config)."

    with state_lock:
        if hostname in managed_rules:
            logging.info(f"Force deleting rule for {hostname} from local state.")
            del managed_rules[hostname]
            rule_removed_from_state = True
            save_state()
        else:
            logging.warning(f"Attempted force delete for hostname '{hostname}', but it was not found in managed rules (perhaps already deleted or cleaned up).")
            rule_removed_from_state = True

    if rule_removed_from_state:
        logging.info(f"Triggering Cloudflare tunnel config update after force deleting {hostname} (or ensuring removal).")
        if update_cloudflare_config():
            logging.info(f"Cloudflare tunnel config update successful after force deleting {hostname}.")
            if dns_delete_success:
                 cloudflared_agent_state["last_action_status"] = f"Successfully force deleted rule and DNS record for {hostname} and updated Cloudflare."
            else:
                 cloudflared_agent_state["last_action_status"] = f"Force deleted rule for {hostname} (DNS delete failed earlier, but tunnel config updated)."
        else:
            logging.error(f"CRITICAL: State saved after force delete of {hostname}, DNS delete status: {dns_delete_success}, but subsequent Cloudflare tunnel config update FAILED!")
            cloudflared_agent_state["last_action_status"] = f"Error: Removed {hostname} locally, DNS delete status: {dns_delete_success}, but FAILED pushing tunnel config update! Reconciliation needed."

    time.sleep(1)
    return redirect(url_for('status_page'))


# --- run_background_tasks ---
def run_background_tasks():
    if not docker_client or not tunnel_state.get("id"):
        logging.warning("Docker client or Tunnel not ready. Background tasks will not start.")
        return None, None
    logging.info("Starting background threads for Docker events and rule cleanup.")
    event_thread = threading.Thread(target=docker_event_listener, name="DockerEventListener", daemon=True)
    cleanup_thread = threading.Thread(target=cleanup_expired_rules, name="CleanupTask", daemon=True)
    event_thread.start()
    cleanup_thread.start()
    logging.info("Background threads started.")
    return event_thread, cleanup_thread


# --- Main Execution ---
if __name__ == '__main__':
    logging.info("----------------------------------------------------")
    logging.info("--- Cloudflare Tunnel Ingress Manager Starting ---")
    logging.info("----------------------------------------------------")
    load_state()
    logging.info("Initial state loading complete.")
    event_thread = None
    cleanup_thread = None

    if not CF_ZONE_ID:
        logging.error("FATAL: CF_ZONE_ID environment variable is missing. DNS management will fail.")
        tunnel_state["status_message"] = "Error: CF_ZONE_ID missing."
        tunnel_state["error"] = "CF_ZONE_ID environment variable must be set."
        sys.exit(1)

    if not docker_client:
         logging.error("Docker client is unavailable at startup. Limited functionality.")
         tunnel_state["status_message"] = "Error: Docker client unavailable."
         tunnel_state["error"] = "Failed to connect to Docker daemon. Check socket mount and permissions."
         cloudflared_agent_state["container_status"] = "docker_unavailable"
         logging.warning("Skipping tunnel initialization, reconciliation, agent management, and background tasks.")
    else:
         logging.info("Docker client available.")
         logging.info(f"Ensuring Docker network '{CLOUDFLARED_NETWORK_NAME}' exists...")
         ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME)
         initialize_tunnel()
         logging.info(f"Tunnel initialization process complete. Status: {tunnel_state.get('status_message')}")
         logging.debug(f"Tunnel State after init: ID={tunnel_state.get('id')}, Token Present={bool(tunnel_state.get('token'))}, Error={tunnel_state.get('error')}")
         if tunnel_state.get("id") and tunnel_state.get("token"):
             logging.info("Tunnel initialized successfully. Proceeding with reconciliation and agent checks.")
             reconcile_state()
             logging.info("Initial state reconciliation complete.")
             logging.info("Checking and attempting to automatically start tunnel agent container if needed...")
             update_cloudflared_container_status()
             if cloudflared_agent_state.get("container_status") != 'running':
                 logging.info("Agent container not running, attempting start...")
                 start_cloudflared_container()
             else:
                 logging.info("Agent container already running.")
             event_thread, cleanup_thread = run_background_tasks()
         else:
             logging.warning("Tunnel not fully initialized (missing ID or Token). Skipping reconciliation, agent start, and background tasks.")
             if not tunnel_state.get("error"):
                 tunnel_state["status_message"] = "Tunnel setup incomplete (ID/Token missing)."

    logging.info("Starting Flask application web server on 0.0.0.0:5000...")
    flask_thread = None
    try:
        from waitress import serve
        flask_thread = threading.Thread(target=serve, args=(app,), kwargs={'host':'0.0.0.0','port':5000}, daemon=True, name="FlaskWaitressServer")
        flask_thread.start()
        logging.info("Flask server started using waitress in a background thread.")
        while True:
             all_threads_alive = True
             if flask_thread and not flask_thread.is_alive():
                  logging.error("Flask server thread terminated unexpectedly.")
                  all_threads_alive = False
             if event_thread and not event_thread.is_alive():
                  logging.warning("Docker event listener thread terminated unexpectedly.")
             if cleanup_thread and not cleanup_thread.is_alive():
                  logging.warning("Cleanup thread terminated unexpectedly.")
             if not all_threads_alive:
                  stop_event.set()
                  break
             if stop_event.is_set():
                  logging.info("Stop event detected in main loop.")
                  break
             time.sleep(10)
    except KeyboardInterrupt:
         logging.info("KeyboardInterrupt received.")
    except Exception as server_err:
        logging.error(f"Web server encountered a fatal error: {server_err}", exc_info=True)
    finally:
        logging.info("Shutdown sequence initiated...")
        stop_event.set()
        logging.info("Stop event set for background threads.")
        logging.info("Exiting Cloudflare Tunnel Ingress Manager application.")
        exit_code = 0
        if tunnel_state.get("error") or cloudflared_agent_state.get("container_status") == "docker_unavailable":
             exit_code = 1
        sys.exit(exit_code)