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
# Updated import: Added render_template
from flask import Flask, jsonify, render_template, redirect, url_for, request
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
# ADDED DEBUG LOGGING HERE
logging.info(f"[DEBUG] CF_HEADERS created: Authorization Header starts with 'Bearer {str(CF_API_TOKEN)[:5]}...'")

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
             # Ensure delete_at is converted back to datetime object
             if rule.get("delete_at") and isinstance(rule.get("delete_at"), str):
                 try:
                     # Handle both ISO 8601 formats (with Z and without)
                     if rule["delete_at"].endswith('Z'):
                        rule["delete_at"] = datetime.fromisoformat(rule["delete_at"].replace('Z', '+00:00'))
                     else:
                         # Attempt parsing potentially offset-naive string, assume UTC if naive
                         dt = datetime.fromisoformat(rule["delete_at"])
                         rule["delete_at"] = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                 except ValueError as date_err:
                     logging.warning(f"Could not parse delete_at for {hostname}: {rule['delete_at']} Error: {date_err}. Setting to None.")
                     rule["delete_at"] = None
             elif not isinstance(rule.get("delete_at"), datetime):
                 rule["delete_at"] = None # Ensure it's None if not a valid string or already None
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
        # Ensure datetime is converted to ISO 8601 string with Z for UTC
        if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
            dt_utc = rule_copy["delete_at"].astimezone(timezone.utc)
            # Format to ISO 8601 with Z, remove microseconds for cleaner output
            rule_copy["delete_at"] = dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
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
        # Use a copy of headers to avoid potential modification issues if needed elsewhere
        # Although in this case, CF_HEADERS is constant after init
        request_headers = CF_HEADERS.copy()
        logging.info(f"API Request: {method} {url} Params: {params} Data: {json_data}")
        # Log the start of the auth header for verification, avoiding full token log
        # logging.debug(f"Auth Header starts with: {request_headers.get('Authorization', 'N/A')[:15]}")

        response = requests.request(method, url, headers=request_headers, json=json_data, params=params, timeout=30)
        response.raise_for_status()
        logging.info(f"API Response Status: {response.status_code}")

        # Handle 204 No Content
        if response.status_code == 204 or not response.content:
            return {"success": True, "result": None}

        try:
            response_data = response.json()
            logging.debug(f"API Response Body (first 500 chars): {str(response_data)[:500]}")
            if isinstance(response_data, dict) and 'success' in response_data:
                 if response_data['success']:
                      return response_data
                 else:
                      # Extract more specific error message if available
                      cf_errors = response_data.get('errors', [])
                      if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                           error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                           logging.error(f"API Request Failed ({method} {url}): {error_msg} - Full Errors: {cf_errors}")
                      else:
                           error_msg = f"API reported failure but no error details provided. Response: {response_data}"
                           logging.error(f"API Request Failed ({method} {url}): {error_msg}")
                      raise requests.exceptions.RequestException(error_msg, response=response)
            else:
                 # Handle cases where response is valid JSON but not the expected Cloudflare format
                 logging.warning(f"API response for {method} {url} was valid JSON but missing 'success' field. Status: {response.status_code}. Body: {str(response_data)[:200]}")
                 # Treat as an unexpected response, raise an exception
                 raise requests.exceptions.RequestException(f"Unexpected JSON response format from API. Status: {response.status_code}", response=response)
        except json.JSONDecodeError:
            # Handle cases where response is not JSON
            logging.error(f"API response for {method} {url} was not valid JSON. Status: {response.status_code}. Body: {response.text[:200]}")
            raise requests.exceptions.RequestException(f"Invalid JSON response from API. Status: {response.status_code}", response=response)
    except requests.exceptions.RequestException as e:
        if error_msg is None: # If we didn't create a specific message above
            logging.error(f"API Request Failed: {method} {url}")
            error_msg = f"Request Exception: {e}"
            if e.response is not None:
                try:
                    # Try to get more details from the response body
                    error_data = e.response.json()
                    logging.error(f"Response Body: {error_data}")
                    cf_errors = error_data.get('errors', [])
                    if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                        error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                    else:
                        # Fallback if no structured errors
                        error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
                except (ValueError, AttributeError, json.JSONDecodeError):
                     # If response body isn't JSON or lacks expected structure
                     error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
            else:
                # Error happened before getting a response (e.g., DNS lookup failure, connection refused)
                logging.error(f"Error details (no response received): {e}")

        # Update global tunnel state error if relevant
        if "cfd_tunnel" in endpoint and tunnel_state.get("id") is None and "token" not in endpoint:
             tunnel_state["error"] = error_msg
        # Re-raise the exception with the best error message we constructed
        raise requests.exceptions.RequestException(error_msg, response=e.response)


# --- find_tunnel_via_api ---
def find_tunnel_via_api(name):
    logging.info(f"[DEBUG] Entering find_tunnel_via_api for '{name}'")
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
                logging.info(f"[DEBUG] Exiting find_tunnel_via_api for '{name}' - Found ID and got Token: {bool(token)}")
                return tunnel_id, token
            else:
                 logging.warning(f"Found tunnel entry for '{name}' but it has no ID in API response: {tunnel}")
                 logging.info(f"[DEBUG] Exiting find_tunnel_via_api for '{name}' - Found but no ID")
                 return None, None
        else:
            logging.info(f"Tunnel '{name}' not found via API.")
            logging.info(f"[DEBUG] Exiting find_tunnel_via_api for '{name}' - Not found")
            return None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding tunnel '{name}': {e}")
        logging.info(f"[DEBUG] Exiting find_tunnel_via_api for '{name}' - RequestException: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error finding tunnel '{name}': {e}", exc_info=True)
        tunnel_state["error"] = f"Unexpected error finding tunnel: {e}"
        logging.info(f"[DEBUG] Exiting find_tunnel_via_api for '{name}' - Unexpected Exception: {e}")
        return None, None


# --- get_tunnel_token_via_api ---
def get_tunnel_token_via_api(tunnel_id):
    logging.info(f"[DEBUG] Entering get_tunnel_token_via_api for ID '{tunnel_id}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    url = f"{CF_API_BASE_URL}{endpoint}"
    try:
        request_headers = {"Authorization": f"Bearer {CF_API_TOKEN}"} # Ensure correct header is used
        logging.info(f"API Request: GET {url} (for token)")
        # logging.debug(f"Auth Header starts with: {request_headers.get('Authorization', 'N/A')[:15]}")
        response = requests.request("GET", url, headers=request_headers, timeout=30)
        response.raise_for_status()
        token = response.text.strip()
        if not token or len(token) < 50:
            logging.error(f"Retrieved token for tunnel {tunnel_id} appears invalid (too short or empty).")
            logging.info(f"[DEBUG] Exiting get_tunnel_token_via_api for ID '{tunnel_id}' - Invalid Token Format")
            raise ValueError("Invalid token format received from API")
        logging.info(f"Successfully retrieved token via API for tunnel {tunnel_id}")
        logging.info(f"[DEBUG] Exiting get_tunnel_token_via_api for ID '{tunnel_id}' - Success")
        return token
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error getting token for tunnel {tunnel_id}: {e}"
        if e.response is not None:
             error_msg += f" Status: {e.response.status_code} Body: {e.response.text[:100]}"
        logging.error(error_msg)
        tunnel_state["error"] = error_msg
        logging.info(f"[DEBUG] Exiting get_tunnel_token_via_api for ID '{tunnel_id}' - RequestException: {e}")
        raise
    except Exception as e:
         logging.error(f"Unexpected error getting tunnel token for {tunnel_id}: {e}", exc_info=True)
         tunnel_state["error"] = f"Unexpected error getting token: {e}"
         logging.info(f"[DEBUG] Exiting get_tunnel_token_via_api for ID '{tunnel_id}' - Unexpected Exception: {e}")
         raise


# --- create_tunnel_via_api ---
def create_tunnel_via_api(name):
    logging.info(f"[DEBUG] Entering create_tunnel_via_api for '{name}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    payload = {"name": name, "config_src": "cloudflare"}
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        token = result.get("token")
        if not tunnel_id or not token:
            logging.error(f"API response for tunnel creation missing ID or Token: {result}")
            logging.info(f"[DEBUG] Exiting create_tunnel_via_api for '{name}' - Missing ID/Token in response")
            raise ValueError("Missing ID or Token in API response for tunnel creation")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id} via API.")
        logging.info(f"[DEBUG] Exiting create_tunnel_via_api for '{name}' - Success")
        return tunnel_id, token
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating tunnel '{name}': {e}")
        logging.info(f"[DEBUG] Exiting create_tunnel_via_api for '{name}' - RequestException: {e}")
        return None, None
    except Exception as e:
        logging.error(f"Unexpected error creating tunnel '{name}': {e}", exc_info=True)
        tunnel_state["error"] = f"Unexpected error creating tunnel: {e}"
        logging.info(f"[DEBUG] Exiting create_tunnel_via_api for '{name}' - Unexpected Exception: {e}")
        return None, None


# --- initialize_tunnel ---
def initialize_tunnel():
    logging.info("[DEBUG] Entering initialize_tunnel")
    tunnel_state["status_message"] = f"Checking for tunnel '{TUNNEL_NAME}' via API..."
    tunnel_state["error"] = None
    tunnel_id = None
    token = None
    try:
        logging.info("[DEBUG] Calling find_tunnel_via_api...")
        tunnel_id, token = find_tunnel_via_api(TUNNEL_NAME)
        logging.info(f"[DEBUG] find_tunnel_via_api returned: ID={tunnel_id}, Token Present={bool(token)}")

        if not tunnel_id and not tunnel_state.get("error"):
            tunnel_state["status_message"] = f"Tunnel '{TUNNEL_NAME}' not found. Creating via API..."
            logging.info("[DEBUG] Calling create_tunnel_via_api...")
            tunnel_id, token = create_tunnel_via_api(TUNNEL_NAME)
            logging.info(f"[DEBUG] create_tunnel_via_api returned: ID={tunnel_id}, Token Present={bool(token)}")

        # Final check
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
        logging.info(f"[DEBUG] Exiting initialize_tunnel - Final State: ID={tunnel_state.get('id')}, Token Present={bool(tunnel_state.get('token'))}, Error={tunnel_state.get('error')}")

    except Exception as e:
        logging.error(f"Unhandled exception during tunnel initialization: {e}", exc_info=True)
        if not tunnel_state.get("error"):
            tunnel_state["error"] = f"Initialization failed unexpectedly: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (unexpected error)."
        logging.info(f"[DEBUG] Exiting initialize_tunnel - Unhandled Exception: {e}")


# --- get_current_cf_config ---
def get_current_cf_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot get CF config, tunnel ID not available.")
        return None # Indicate failure to get config

    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
    try:
        response_data = cf_api_request("GET", endpoint)
        # Check for success and presence of 'result' which contains the config
        if response_data and response_data.get("success"):
            result_data = response_data.get("result")
            # The result should be a dict containing 'config'
            if isinstance(result_data, dict):
                 config_data = result_data.get("config")
                 # 'config' itself should be a dict (can be empty) or null
                 if isinstance(config_data, dict):
                     logging.debug(f"Successfully fetched and parsed config: {config_data}")
                     return config_data # Return the actual config dict
                 elif config_data is None:
                     logging.info("Fetched config is null (no configuration set yet). Returning empty config.")
                     return {} # Return an empty dict representing no config
                 else:
                     logging.warning(f"Unexpected type for 'config' field in API response. Expected dict or null, got {type(config_data)}. Response: {response_data}")
                     return {} # Treat unexpected format as empty
            # Handle case where result is present but null (e.g., tunnel exists but never configured)
            elif result_data is None and response_data.get("success"):
                 logging.info("Fetched config result is null (no configuration set yet). Returning empty config.")
                 return {}
            else:
                # If 'result' key exists but isn't a dict or null
                logging.warning(f"API response success but 'result' has unexpected format or is missing. Response: {response_data}")
                return {} # Treat unexpected format as empty
        else:
            # API request failed or didn't return success
            logging.error(f"get_current_cf_config: cf_api_request did not return success or expected data. Response: {response_data}")
            return None # Indicate failure
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching config for tunnel {tunnel_state['id']}: {e}")
        # Update global error state only if it's not already set to a more specific API error
        if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
             tunnel_state["error"] = f"Failed get tunnel config: {e}"
        return None # Indicate failure
    except Exception as e:
        logging.error(f"Unexpected exception in get_current_cf_config: {e}", exc_info=True)
        if not tunnel_state.get("error"): tunnel_state["error"] = f"Unexpected error getting tunnel config: {e}"
        return None


# --- find_dns_record_id ---
def find_dns_record_id(zone_id, hostname, tunnel_id):
    if not zone_id or not hostname or not tunnel_id:
        logging.error("find_dns_record_id: Missing required arguments.")
        return None

    # Construct the expected CNAME content
    expected_content = f"{tunnel_id}.cfargotunnel.com"
    endpoint = f"/zones/{zone_id}/dns_records"
    params = {
        "type": "CNAME",
        "name": hostname, # The public hostname
        "content": expected_content, # The target the CNAME should point to
        "match": "all" # Ensure all parameters match
    }
    try:
        logging.info(f"Searching for DNS record: Type=CNAME, Name={hostname}, Content={expected_content}")
        response_data = cf_api_request("GET", endpoint, params=params)
        results = response_data.get("result", [])
        if results and isinstance(results, list):
            # Found at least one matching record
            record_id = results[0].get("id")
            if record_id:
                 logging.info(f"Found DNS record for {hostname} with ID: {record_id}")
                 return record_id
            else:
                 # Log if record found but lacks ID (unlikely but possible)
                 logging.warning(f"Found matching DNS record entry for {hostname}, but it lacks an ID: {results[0]}")
                 return None
        else:
            # No matching record found
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
        return None # Return None to indicate failure

    record_name = hostname # The public FQDN
    record_content = f"{tunnel_id}.cfargotunnel.com" # The tunnel CNAME target
    endpoint = f"/zones/{zone_id}/dns_records"
    payload = {
        "type": "CNAME",
        "name": record_name,
        "content": record_content,
        "ttl": 1,  # 1 means 'Automatic' TTL
        "proxied": True # Ensure traffic goes through Cloudflare proxy
    }

    try:
        # First, check if the exact record already exists
        existing_id = find_dns_record_id(zone_id, hostname, tunnel_id)
        if existing_id:
             logging.info(f"DNS CNAME record for {hostname} pointing to {record_content} already exists (ID: {existing_id}). No action needed.")
             return existing_id # Return the existing ID

        # If not found, proceed to create it
        logging.info(f"Creating DNS CNAME record: Name={record_name}, Content={record_content}, Proxied=True")
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        new_record_id = result.get("id")
        if new_record_id:
             logging.info(f"Successfully created DNS record for {hostname}. New ID: {new_record_id}")
             return new_record_id # Return the newly created ID
        else:
             # Log error if API reports success but no ID is returned
             logging.error(f"DNS record creation for {hostname} succeeded according to API status, but no ID was returned in result: {result}")
             return None # Indicate failure
    except requests.exceptions.RequestException as e:
        # Handle specific API errors during creation
        logging.error(f"API error creating DNS record for {hostname}: {e}")
        return None # Indicate failure
    except Exception as e:
        # Handle unexpected errors
        logging.error(f"Unexpected error creating DNS record for {hostname}: {e}", exc_info=True)
        return None # Indicate failure


# --- delete_cloudflare_dns_record ---
def delete_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    if not zone_id or not hostname or not tunnel_id:
        logging.error("delete_cloudflare_dns_record: Missing required arguments.")
        return False # Return False for failure

    # First, find the specific record ID to delete
    # We need tunnel_id to ensure we delete the CNAME pointing to *our* tunnel
    dns_record_id = find_dns_record_id(zone_id, hostname, tunnel_id)

    if not dns_record_id:
        # If the record doesn't exist (or doesn't point to our tunnel), consider it success
        logging.warning(f"Could not find DNS record for {hostname} pointing to tunnel {tunnel_id} to delete. Assuming already deleted or never created.")
        return True # Return True as the desired state (no record) is achieved

    # If found, proceed with deletion
    logging.info(f"Attempting to delete DNS record for {hostname} (ID: {dns_record_id})")
    endpoint = f"/zones/{zone_id}/dns_records/{dns_record_id}"
    try:
        cf_api_request("DELETE", endpoint)
        logging.info(f"Successfully deleted DNS record for {hostname} (ID: {dns_record_id}).")
        return True # Return True for success
    except requests.exceptions.RequestException as e:
        # Handle 404 specifically - means it was already gone
        if e.response is not None and e.response.status_code == 404:
             logging.warning(f"Attempted to delete DNS record {dns_record_id} for {hostname}, but API returned 404 (already deleted?). Treating as success.")
             return True
        # Log other API errors
        logging.error(f"API error deleting DNS record {dns_record_id} for {hostname}: {e}")
        return False # Return False for failure
    except Exception as e:
        # Handle unexpected errors
        logging.error(f"Unexpected error deleting DNS record {dns_record_id} for {hostname}: {e}", exc_info=True)
        return False # Return False for failure


# --- update_cloudflare_config ---
def update_cloudflare_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot update Cloudflare config, tunnel ID not available.")
        return False

    final_ingress_rules = None
    needs_api_update = False # Flag to determine if PUT request is necessary

    # Lock state while determining desired config and comparing
    with state_lock:
        logging.info("Preparing potential Cloudflare tunnel configuration update...")
        # Build the list of desired ingress rules from current active state
        desired_ingress_rules = []
        # Define the mandatory catch-all rule
        catch_all_rule = {"service": "http_status:404"}

        for hostname, rule_details in managed_rules.items():
            # Only include rules marked as 'active'
            if rule_details.get("status") == "active":
                service = rule_details.get("service")
                if service: # Ensure service detail exists
                    desired_rule = {"hostname": hostname, "service": service}
                    # Optional: Add path filtering here if needed in the future
                    # if rule_details.get("path"):
                    #    desired_rule["path"] = rule_details["path"]
                    desired_ingress_rules.append(desired_rule)
                else:
                    logging.warning(f"Managed rule for '{hostname}' is active but missing 'service' detail. Skipping.")

        # Sort desired rules by hostname for consistent comparison and ordering
        # (Optional, but good practice)
        desired_ingress_rules.sort(key=lambda x: x.get("hostname", ""))

        # Fetch the current configuration from Cloudflare for comparison
        logging.debug("Fetching current Cloudflare config for comparison...")
        current_config = get_current_cf_config()
        if current_config is None: # Check if fetching failed
            logging.error("Failed to fetch current Cloudflare config within lock, aborting update.")
            return False # Cannot proceed without current config

        # Extract the current ingress rules from the fetched config, excluding the 404 rule
        current_cf_ingress = [rule for rule in current_config.get("ingress", [])
                              if rule.get("service") != catch_all_rule["service"]]

        # --- Comparison Logic ---
        # Convert rule lists to a comparable format (e.g., sets of tuples)
        # Ensures order doesn't matter and focuses on content.
        def rule_to_canonical(rule):
            # Include hostname and service; add path if/when implemented
            items = sorted([(k, v) for k, v in rule.items() if k in ["hostname", "service"]])
            return tuple(items)

        try:
             # Create sets of canonical rule representations
             current_cf_set = {rule_to_canonical(rule) for rule in current_cf_ingress if rule.get("hostname") and rule.get("service")}
             desired_set = {rule_to_canonical(rule) for rule in desired_ingress_rules if rule.get("hostname") and rule.get("service")}
        except Exception as e:
             # Catch potential errors during set creation (e.g., unexpected data types)
             logging.error(f"Error creating canonical rule sets for comparison: {e}", exc_info=True)
             return False

        # Compare the sets
        if current_cf_set == desired_set:
            logging.info("No changes detected between managed state and Cloudflare config. Skipping API update.")
            needs_api_update = False
        else:
            logging.info("Change detected. Desired ingress rules differ from current Cloudflare config.")
            logging.debug(f"Current CF rules (non-404, canonical): {current_cf_set}")
            logging.debug(f"Desired rules (from state, canonical): {desired_set}")
            needs_api_update = True
            # Prepare the final list: desired rules + catch-all
            final_ingress_rules = desired_ingress_rules + [catch_all_rule]
            # Optional: Add originRequest config here if needed
            # final_config_payload = {"ingress": final_ingress_rules, "originRequest": { ... }}

    # --- API Update Logic (outside the lock) ---
    if needs_api_update and final_ingress_rules is not None:
        endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        # The payload requires the full config structure
        payload = {"config": {"ingress": final_ingress_rules}}
        # Optional: If including originRequest, use final_config_payload here
        # payload = {"config": final_config_payload}

        last_exception = None # Store the last error for reporting

        # Retry Loop
        for attempt in range(MAX_CF_UPDATE_RETRIES + 1):
            try:
                logging.info(f"Attempting to push config to Cloudflare (Attempt {attempt + 1}/{MAX_CF_UPDATE_RETRIES + 1})...")
                cf_api_request("PUT", endpoint, json_data=payload)

                # Success
                logging.info("Successfully updated Cloudflare tunnel configuration via API.")
                cloudflared_agent_state["last_action_status"] = f"Cloudflare config updated successfully at {datetime.now(timezone.utc).isoformat()}"
                # Clear stale errors related to config updates from global state
                if tunnel_state.get("error") and ("Failed update tunnel config" in tunnel_state["error"] or "API Error" in tunnel_state["error"]):
                     logging.info(f"Clearing previous API error after successful update: {tunnel_state['error']}")
                     tunnel_state["error"] = None
                return True # Exit function on success

            except requests.exceptions.RequestException as e:
                last_exception = e # Store the exception
                status_code = e.response.status_code if e.response is not None else None
                logging.warning(f"Cloudflare API update attempt {attempt + 1} failed: {e} (Status Code: {status_code})")

                # Determine if the error is likely retryable
                is_retryable = False
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                    is_retryable = True # Network issues are often transient
                elif status_code in [429, 500, 502, 503, 504]: # Rate limits, server errors
                    is_retryable = True

                if is_retryable and attempt < MAX_CF_UPDATE_RETRIES:
                    # Calculate backoff delay
                    wait_time = CF_UPDATE_RETRY_DELAY * (CF_UPDATE_BACKOFF_FACTOR ** attempt)
                    # Add random jitter (e.g., +/- 20%) to avoid thundering herd
                    wait_time *= (1 + random.uniform(-0.2, 0.2))
                    wait_time = max(1, wait_time) # Ensure at least 1 sec wait

                    # Check for Retry-After header on 429s
                    if status_code == 429 and e.response is not None:
                         retry_after = e.response.headers.get("Retry-After")
                         if retry_after:
                              try:
                                  retry_after_seconds = int(retry_after)
                                  logging.info(f"Cloudflare API rate limit hit. Respecting Retry-After header: {retry_after_seconds}s")
                                  # Use the *longer* of the calculated backoff or Retry-After
                                  wait_time = max(wait_time, retry_after_seconds)
                              except ValueError:
                                  logging.warning(f"Could not parse Retry-After header value '{retry_after}'. Using calculated backoff ({wait_time:.1f}s).")

                    logging.info(f"Retrying Cloudflare update in {wait_time:.1f} seconds...")
                    # Wait for the calculated time, but allow interruption by stop_event
                    interrupted = stop_event.wait(wait_time)
                    if interrupted:
                         logging.warning("Shutdown requested during Cloudflare update retry wait. Aborting.")
                         cloudflared_agent_state["last_action_status"] = f"Error: CF update aborted during retry (shutdown)."
                         # Set global error state
                         if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
                              tunnel_state["error"] = f"Failed update tunnel config: aborted during retry"
                         return False # Stop retrying and signal failure
                    continue # Continue to the next retry attempt
                else:
                    # Not retryable or retries exhausted
                    logging.error(f"Cloudflare API update failed and will not be retried (Retryable: {is_retryable}, Attempt: {attempt + 1}).")
                    break # Exit the retry loop

            except Exception as e: # Catch unexpected errors during the PUT request
                 last_exception = e
                 logging.error(f"Unexpected error during Cloudflare API update attempt {attempt + 1}: {e}", exc_info=True)
                 break # Exit the retry loop

        # If loop finished without returning True, it means all attempts failed
        logging.error(f"Failed to update Cloudflare tunnel configuration after {MAX_CF_UPDATE_RETRIES + 1} attempts.")
        error_message = f"Failed update tunnel config after retries: {last_exception}"
        cloudflared_agent_state["last_action_status"] = f"Error: {error_message}"
        # Update global error state
        if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
             tunnel_state["error"] = error_message
        return False # Signal failure

    elif needs_api_update and final_ingress_rules is None:
         # This case should ideally not happen if logic is correct
         logging.error("Internal error: Needs API update but final_ingress_rules not set.")
         return False
    else:
         # No update was needed
         return True # Signal success (as in, no update required)


# --- process_container_start ---
def process_container_start(container):
    if not container: return
    try:
        container_id = container.id
        # Reload container info to ensure labels are fresh
        try:
             container.reload()
        except NotFound:
             # Container might have been removed very quickly after starting
             logging.warning(f"Container {container_id[:12]} not found when processing start event (likely stopped quickly).")
             return

        labels = container.labels
        container_name = container.name

        # Define the labels we look for
        enabled_label = f"{LABEL_PREFIX}.enable"
        hostname_label = f"{LABEL_PREFIX}.hostname"
        service_label = f"{LABEL_PREFIX}.service"
        # path_label = f"{LABEL_PREFIX}.path" # Example for future path support

        # Extract and validate labels
        is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
        hostname = labels.get(hostname_label)
        service = labels.get(service_label)
        # path = labels.get(path_label) # Example for future path support

        # Check if this container should be managed
        if not is_enabled:
            logging.debug(f"Ignoring start event for container {container_name} ({container_id[:12]}): '{enabled_label}' is not 'true'.")
            return
        # Check for mandatory labels
        if not hostname or not service:
            logging.warning(f"Ignoring start event for container {container_name} ({container_id[:12]}): Missing required labels '{hostname_label}' or '{service_label}'.")
            return
        # Basic hostname validation (adjust regex if needed for specific TLDs/IDNs)
        if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$", hostname):
             logging.warning(f"Ignoring start event for container {container_name} ({container_id[:12]}): Invalid hostname format '{hostname}'. Must be a valid FQDN.")
             return
        # Basic service validation (allow common schemes or host:port)
        # Allows http/https/tcp/unix schemes OR simple host:port (e.g., myapp:8080)
        if not (re.match(r"^(https?|tcp|unix)://", service) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)):
             logging.warning(f"Ignoring start event for {container_name} ({container_id[:12]}): Invalid service format '{service}'. Needs scheme (http/https/tcp/unix)://... or be host_or_container_name:port.")
             return
        # Optional: Add path validation here if path label is used

        logging.info(f"Detected start for managed container: {container_name} ({container_id[:12]}) - Hostname: {hostname}, Service: {service}")
        needs_cf_update = False # Flag if Cloudflare config needs API update
        state_changed_locally = False # Flag if local state.json needs saving

        # --- State Update Logic (within lock) ---
        with state_lock:
            existing_rule = managed_rules.get(hostname)

            if existing_rule:
                # Rule for this hostname already exists
                if existing_rule.get("status") == "pending_deletion":
                    # Container restarted while rule was pending deletion - reactivate it
                    logging.info(f"Rule for {hostname} was pending deletion. Reactivating.")
                    existing_rule["status"] = "active"
                    existing_rule["delete_at"] = None
                    existing_rule["service"] = service # Update service in case it changed
                    existing_rule["container_id"] = container_id # Update container ID
                    # existing_rule["path"] = path # Update path if implemented
                    state_changed_locally = True
                    needs_cf_update = True # Need to push the reactivated rule to CF
                elif existing_rule.get("status") == "active":
                    # Rule already active, check if details changed
                    service_changed = existing_rule.get("service") != service
                    # path_changed = existing_rule.get("path") != path # Check path if implemented
                    container_changed = existing_rule.get("container_id") != container_id

                    if container_changed:
                        # Update the container ID if a different container now serves this hostname
                        logging.info(f"Updating container ID for active rule {hostname}: '{existing_rule.get('container_id', 'N/A')[:12]}' -> '{container_id[:12]}'.")
                        existing_rule["container_id"] = container_id
                        state_changed_locally = True
                        # No CF update needed just for container ID change

                    if service_changed: # Or path_changed if implemented
                         logging.info(f"Updating service for active rule {hostname}: '{existing_rule.get('service')}' -> '{service}'.")
                         existing_rule["service"] = service
                         # existing_rule["path"] = path # Update path if implemented
                         state_changed_locally = True
                         needs_cf_update = True # Service/path change requires CF config update
                    # elif path_changed: ... # Handle path change if service didn't change

                    elif not state_changed_locally:
                         # Container started, rule active, nothing changed
                         logging.info(f"Container start event for {hostname}, but rule is already active with same details.")
            else:
                # New hostname being managed
                logging.info(f"Adding new active rule for hostname: {hostname}")
                managed_rules[hostname] = {
                    "service": service,
                    "container_id": container_id,
                    "status": "active",
                    "delete_at": None
                    # "path": path # Add path if implemented
                }
                state_changed_locally = True
                needs_cf_update = True # Adding a rule requires CF update

            # Save state if any local changes were made
            if state_changed_locally:
                logging.debug(f"Local state changed for {hostname}, saving state file...")
                save_state()

        # --- Cloudflare Update Logic (outside lock) ---
        if needs_cf_update:
            logging.info(f"Triggering Cloudflare config update due to change for {hostname}.")
            # Attempt to update the Cloudflare tunnel configuration
            if update_cloudflare_config():
                logging.info(f"Tunnel config update successful for {hostname}.")
                # After successful config update, ensure DNS record exists
                if tunnel_state.get("id") and CF_ZONE_ID:
                    dns_record_id = create_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"])
                    if dns_record_id:
                         logging.info(f"DNS record management successful for {hostname}.")
                    else:
                         # This is a potential problem state - config updated but DNS failed
                         logging.error(f"CRITICAL: Tunnel config updated for {hostname} but failed to create/verify DNS record!")
                         # Update status for UI
                         cloudflared_agent_state["last_action_status"] = f"Error: Failed creating DNS record for {hostname} after tunnel update."
                else:
                     logging.error("Missing Tunnel ID or Zone ID - cannot manage DNS record.")
            else:
                # Config update failed (retries exhausted)
                logging.error(f"Failed to update Cloudflare tunnel config after processing start for {hostname}. DNS record not managed.")
                # State was potentially saved locally, but CF is out of sync. Reconciliation should fix later.
        elif state_changed_locally:
             # Only local state changed (e.g., container ID update), no CF push needed
             logging.debug(f"Local state updated for {hostname} (e.g., container ID), no Cloudflare config change needed.")

    except NotFound:
        # Handle case where container disappears during processing
        logging.warning(f"Container {container_id[:12] if 'container_id' in locals() else 'Unknown'} not found during start processing.")
    except APIError as e:
        # Handle Docker API errors
        logging.error(f"Docker API error processing container start ({container_id[:12] if 'container_id' in locals() else 'Unknown'}): {e}", exc_info=True)
    except Exception as e:
        # Handle any other unexpected errors
        logging.error(f"Unexpected error processing container start ({container_id[:12] if 'container_id' in locals() else 'Unknown'}): {e}", exc_info=True)


# --- schedule_container_stop ---
def schedule_container_stop(container_id):
    if not container_id: return
    logging.info(f"Processing stop event for container {container_id[:12]}. Checking for managed rules.")
    hostname_to_schedule = None
    state_changed = False

    # Lock state while modifying rule status
    with state_lock:
        # Find if this container manages an *active* rule
        for hn, details in managed_rules.items():
            if details.get("container_id") == container_id and details.get("status") == "active":
                hostname_to_schedule = hn
                break # Assume one container manages one hostname for now

        if hostname_to_schedule:
            logging.info(f"Container {container_id[:12]} managed active rule for {hostname_to_schedule}. Marking for deletion.")
            rule = managed_rules[hostname_to_schedule]
            # Check if it's not already pending (e.g., multiple stop events)
            if rule.get("status") != "pending_deletion":
                 rule["status"] = "pending_deletion"
                 # Calculate deletion time based on grace period
                 rule["delete_at"] = datetime.now(timezone.utc) + timedelta(seconds=GRACE_PERIOD_SECONDS)
                 logging.info(f"Rule for {hostname_to_schedule} scheduled for deletion at {rule['delete_at'].isoformat()}")
                 state_changed = True
            else:
                 # Already pending, maybe adjust delete_at? For now, just log.
                 logging.info(f"Rule for {hostname_to_schedule} was already pending deletion.")
        else:
            # Container stopped, but it wasn't managing an active rule in our state
            logging.info(f"Stop event for container {container_id[:12]}, but it didn't manage any active rule in the current state.")

        # Save state if a rule was marked for deletion
        if state_changed:
            save_state()
    # Note: We don't update Cloudflare config here. Cleanup task handles actual removal.


# --- docker_event_listener ---
def docker_event_listener():
    if not docker_client:
        logging.error("Docker client unavailable, event listener cannot start.")
        return

    logging.info("Starting Docker event listener...")
    error_count = 0
    max_errors = 5 # Max consecutive errors before stopping

    while not stop_event.is_set() and error_count < max_errors:
        try:
            # Get events from now onwards
            # Use 'since' to avoid processing past events on reconnect
            logging.info("Connecting to Docker event stream...")
            events = docker_client.events(decode=True, since=int(time.time()))
            logging.info("Successfully connected to Docker event stream.")
            error_count = 0 # Reset error count on successful connection

            for event in events:
                if stop_event.is_set():
                    logging.info("Stop event received, exiting Docker event listener loop.")
                    break # Exit inner loop

                # Extract event details
                ev_type = event.get("Type")
                action = event.get("Action")
                actor = event.get("Actor", {})
                cont_id = actor.get("ID")

                logging.debug(f"Docker Event: Type={ev_type}, Action={action}, ActorID={cont_id[:12] if cont_id else 'N/A'}")

                # We only care about container events with an ID
                if ev_type == "container" and cont_id:
                    if action == "start":
                        try:
                            # Get container object to access labels
                            container = docker_client.containers.get(cont_id)
                            process_container_start(container)
                        except NotFound:
                            # Can happen if container is stopped/removed very quickly
                            logging.warning(f"Container {cont_id[:12]} not found shortly after 'start' event.")
                        except APIError as e:
                             logging.error(f"Docker API error getting container {cont_id[:12]} after start event: {e}")
                        except Exception as e:
                             # Catch any errors in process_container_start
                             logging.error(f"Error processing start event for {cont_id[:12]}: {e}", exc_info=True)
                    elif action in ["stop", "die", "destroy", "kill"]:
                         # Treat all these as signals that the container is no longer running
                         try:
                             schedule_container_stop(cont_id)
                         except Exception as e:
                             # Catch any errors in schedule_container_stop
                             logging.error(f"Error processing stop/die/destroy/kill event for {cont_id[:12]}: {e}", exc_info=True)

        # Handle errors related to the event stream connection
        except requests.exceptions.ConnectionError as e:
             error_count += 1
             logging.error(f"Connection error with Docker daemon in event listener: {e}. Attempting reconnect ({error_count}/{max_errors})...")
             stop_event.wait(min(30, 5 * error_count)) # Wait before retry, capped
        except APIError as e:
             # Handle API errors from the Docker daemon itself (e.g., permissions)
             error_count += 1
             logging.error(f"Docker API error in event listener stream: {e}. Attempting reconnect ({error_count}/{max_errors})...")
             stop_event.wait(min(30, 5 * error_count))
        except Exception as e:
             # Catch any other unexpected errors in the listener loop
             error_count += 1
             logging.error(f"Unexpected error in Docker event listener: {e}. Attempting reconnect ({error_count}/{max_errors})...", exc_info=True)
             stop_event.wait(min(30, 5 * error_count))

        if stop_event.is_set(): break # Exit outer loop if stopped

    # Loop exited
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
            state_changed_in_cleanup = False # Track if state file needs saving

            # --- Identify Expired Rules (within lock) ---
            with state_lock:
                for hostname, details in managed_rules.items():
                    # Only consider rules marked for deletion
                    if details.get("status") == "pending_deletion":
                        delete_at = details.get("delete_at")
                        is_expired = False
                        if isinstance(delete_at, datetime):
                             # Ensure comparison is timezone-aware (should be UTC)
                             delete_at_utc = delete_at.astimezone(timezone.utc)
                             if delete_at_utc <= now_utc:
                                 logging.info(f"Rule for {hostname} deletion grace period expired ({delete_at_utc.isoformat()}). Scheduling for full deletion.")
                                 is_expired = True
                        else:
                             # Handle invalid or missing delete_at time - delete immediately
                             logging.warning(f"Rule {hostname} is pending_deletion but delete_at is invalid or missing: {delete_at}. Scheduling for immediate full deletion.")
                             is_expired = True

                        if is_expired:
                             hostnames_to_process_for_deletion.append(hostname)

            # --- Process Deletions (outside lock) ---
            if hostnames_to_process_for_deletion:
                logging.info(f"Processing cleanup for: {hostnames_to_process_for_deletion}")
                processed_hostnames_for_cf_update = [] # Hostnames successfully processed for CF update
                dns_delete_success_all = True # Track if all DNS deletions worked

                # Step 1: Delete DNS records first
                for hostname in hostnames_to_process_for_deletion:
                    if tunnel_state.get("id") and CF_ZONE_ID:
                         logging.info(f"Attempting DNS record deletion for expired rule: {hostname}")
                         if delete_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"]):
                              # DNS delete successful (or record didn't exist)
                              processed_hostnames_for_cf_update.append(hostname)
                         else:
                              # DNS delete failed, log error but proceed with CF update attempt
                              logging.error(f"Failed to delete DNS record for {hostname}. Tunnel config update will proceed, but DNS record may remain stale.")
                              dns_delete_success_all = False
                              # Still add to processed list so we try to remove from CF config
                              processed_hostnames_for_cf_update.append(hostname)
                    else:
                         # Cannot delete DNS if tunnel/zone ID missing
                         logging.error(f"Cannot delete DNS for {hostname}: Missing Tunnel ID or Zone ID.")
                         dns_delete_success_all = False
                         # Don't add to processed_hostnames_for_cf_update? Or add and let CF update fail?
                         # Let's add it, update_cloudflare_config will try to remove it based on state.

                # Step 2: Update Cloudflare config (implicitly removes rules not in active state)
                if processed_hostnames_for_cf_update:
                    logging.info(f"Attempting Cloudflare tunnel config update to remove rules corresponding to: {processed_hostnames_for_cf_update}")
                    # update_cloudflare_config uses the current state (where these are 'pending_deletion')
                    # to build the desired config (which won't include them)
                    if update_cloudflare_config():
                        logging.info(f"Cloudflare tunnel config updated successfully. Removing rules from local state: {processed_hostnames_for_cf_update}")
                        # Step 3: Remove from local state only after successful CF update
                        with state_lock:
                            deleted_count = 0
                            for hostname in processed_hostnames_for_cf_update:
                                # Double-check rule exists and is still pending before deleting
                                if hostname in managed_rules and managed_rules[hostname].get("status") == "pending_deletion":
                                    del managed_rules[hostname]
                                    deleted_count += 1
                                    state_changed_in_cleanup = True
                                else:
                                    # Log if rule disappeared or status changed unexpectedly
                                    logging.warning(f"Rule {hostname} was scheduled for removal but not found or no longer 'pending_deletion' when removing from state.")
                            logging.info(f"Removed {deleted_count} rules from local state.")
                            if state_changed_in_cleanup:
                                save_state()
                    else:
                        # CF update failed - log error, state remains unchanged. Will retry next cycle.
                        logging.error("Failed to update Cloudflare tunnel config during rule cleanup. Rules remain in local state (pending_deletion) and potentially in Cloudflare. Will retry on next cleanup/reconcile cycle.")
                else:
                     logging.info("No hostnames ended up being processed for deletion (e.g., DNS prerequisites failed).")

            else:
                # No rules were found to be expired in this cycle
                logging.debug("No expired rules found requiring cleanup.")

        except Exception as e:
            # Catch unexpected errors in the cleanup loop itself
            logging.error(f"Error in cleanup task loop: {e}", exc_info=True)

        # Wait until the next scheduled check time, respecting the stop event
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
        # --- Get Current Docker State ---
        running_labeled_containers = {} # Dict: hostname -> {service, container_id, container_name}
        try:
             # List all running containers
             containers = docker_client.containers.list(sparse=False) # sparse=False gets more details like labels
             logging.debug(f"[Reconcile] Found {len(containers)} running containers.")
             for c in containers:
                 try:
                     # Extract labels and relevant info
                     labels = c.labels
                     container_id = c.id
                     container_name = c.name
                     enabled_label = f"{LABEL_PREFIX}.enable"
                     hostname_label = f"{LABEL_PREFIX}.hostname"
                     service_label = f"{LABEL_PREFIX}.service"
                     # path_label = f"{LABEL_PREFIX}.path" # If path support added

                     is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
                     hostname = labels.get(hostname_label)
                     service = labels.get(service_label)
                     # path = labels.get(path_label) # If path support added

                     # Process only if enabled and has required labels + valid format
                     if is_enabled and hostname and service:
                         # Apply same validation as in process_container_start
                         if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$", hostname): continue # Skip invalid hostname
                         if not (re.match(r"^(https?|tcp|unix)://", service) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)): continue # Skip invalid service

                         # Handle potential duplicate hostnames (warn and take the last one found)
                         if hostname in running_labeled_containers:
                              logging.warning(f"[Reconcile] Duplicate hostname label '{hostname}' found on container {container_name} ({container_id[:12]}) and container {running_labeled_containers[hostname]['container_name']} ({running_labeled_containers[hostname]['container_id'][:12]}). Using the latest one found ({container_name}).")

                         running_labeled_containers[hostname] = {
                             "service": service,
                             "container_id": container_id,
                             "container_name": container_name
                             # "path": path # If path support added
                         }
                 except NotFound:
                      # Container disappeared between list and get details
                      logging.warning(f"[Reconcile] Container {c.id[:12]} listed but then not found during processing. Skipping.")
                      continue
                 except APIError as e:
                      # Error getting details for a specific container
                      logging.error(f"[Reconcile] Docker API error processing container {c.id[:12]}: {e}. Skipping.")
                      continue
             logging.info(f"[Reconcile] Found {len(running_labeled_containers)} running containers with valid management labels.")
        except APIError as e:
             # Error listing containers
             logging.error(f"[Reconcile] Docker API error listing containers: {e}. Aborting reconciliation.")
             return
        except requests.exceptions.ConnectionError as e:
             # Error connecting to Docker daemon
             logging.error(f"[Reconcile] Failed to connect to Docker daemon while listing containers: {e}. Aborting reconciliation.")
             return

        # --- Compare Docker State with Local State (within lock) ---
        with state_lock:
            logging.debug("[Reconcile] Acquired state lock.")
            now_utc = datetime.now(timezone.utc)
            managed_hostnames = set(managed_rules.keys())
            running_hostnames = set(running_labeled_containers.keys())
            hostnames_requiring_dns_check = [] # Track hostnames added/reactivated

            # 1. Check running containers against managed rules
            for hostname, running_details in running_labeled_containers.items():
                if hostname in managed_rules:
                    # Existing rule, check status and details
                    rule = managed_rules[hostname]
                    if rule.get("status") == "pending_deletion":
                        # Container is running, but rule was pending delete -> Reactivate
                        logging.info(f"[Reconcile] Hostname {hostname} is running but rule was pending deletion. Reactivating.")
                        rule["status"] = "active"
                        rule["delete_at"] = None
                        rule["service"] = running_details["service"] # Update details
                        rule["container_id"] = running_details["container_id"]
                        # rule["path"] = running_details["path"] # If path added
                        state_changed_locally = True
                        needs_cf_update = True
                        hostnames_requiring_dns_check.append(hostname) # Ensure DNS exists
                    elif rule.get("status") == "active":
                        # Already active, check if details match running container
                        container_changed = rule.get("container_id") != running_details["container_id"]
                        service_changed = rule.get("service") != running_details["service"]
                        # path_changed = rule.get("path") != running_details["path"] # If path added

                        if container_changed:
                            logging.info(f"[Reconcile] Updating container ID for active rule {hostname}.")
                            rule["container_id"] = running_details["container_id"]
                            state_changed_locally = True
                            # No CF update needed just for container ID change

                        if service_changed: # or path_changed:
                             logging.info(f"[Reconcile] Updating service/path for active rule {hostname}.")
                             rule["service"] = running_details["service"]
                             # rule["path"] = running_details["path"] # If path added
                             state_changed_locally = True
                             needs_cf_update = True # Service/path change needs CF push
                        # elif path_changed: ... # if only path changed

                else:
                    # Running container has labels, but no managed rule exists -> Add new rule
                    logging.info(f"[Reconcile] Found running container for {hostname} but no managed rule. Adding new active rule.")
                    managed_rules[hostname] = {
                        "service": running_details["service"],
                        "container_id": running_details["container_id"],
                        "status": "active",
                        "delete_at": None
                        # "path": running_details["path"] # If path added
                    }
                    state_changed_locally = True
                    needs_cf_update = True
                    hostnames_requiring_dns_check.append(hostname) # Ensure DNS exists

            # 2. Check managed rules against running containers
            for hostname in list(managed_hostnames): # Iterate copy as we might modify dict
                if hostname not in running_hostnames:
                     # Rule exists locally, but no container running for it
                     if hostname in managed_rules: # Double check needed if deletion happens concurrently
                         rule = managed_rules[hostname]
                         if rule.get("status") == "active":
                              # Rule is active but container is gone -> Schedule deletion
                              logging.info(f"[Reconcile] Managed rule {hostname} is active but no container found running. Scheduling deletion.")
                              rule["status"] = "pending_deletion"
                              rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS)
                              state_changed_locally = True
                              # No CF update needed here, cleanup task handles removal later

            # 3. Compare Local State with Cloudflare State (Optional but recommended)
            # This ensures CF config matches our active rules, catching drift
            logging.debug("[Reconcile] Fetching current CF config for final comparison...")
            current_cf_config = get_current_cf_config()
            if current_cf_config is not None:
                # Extract active hostnames from CF config (excluding 404 rule)
                cf_ingress_hostnames = {r.get("hostname") for r in current_cf_config.get("ingress", [])
                                        if r.get("hostname") and r.get("service") != "http_status:404"}
                # Get active hostnames from our local state
                active_managed_hostnames = {hn for hn, d in managed_rules.items() if d.get("status") == "active"}

                # Compare the sets
                if cf_ingress_hostnames != active_managed_hostnames:
                     logging.warning(f"[Reconcile] Mismatch detected between active managed rules ({len(active_managed_hostnames)}) and Cloudflare tunnel config ({len(cf_ingress_hostnames)})!")
                     logging.info(f"[Reconcile] Active Managed State Hostnames: {sorted(list(active_managed_hostnames))}")
                     logging.info(f"[Reconcile] Found in Cloudflare Tunnel Config: {sorted(list(cf_ingress_hostnames))}")
                     logging.info("[Reconcile] Marking for Cloudflare tunnel config update to enforce local state.")
                     needs_cf_update = True # Trigger update to align CF with local state
            else:
                # Failed to get CF config, cannot perform this comparison
                logging.error("[Reconcile] Could not fetch Cloudflare config during reconciliation. Skipping final tunnel config comparison.")

            # Save state if anything changed locally
            if state_changed_locally:
                logging.info("[Reconcile] Local state changed during reconciliation. Saving state file.")
                save_state()

            logging.debug("[Reconcile] Releasing state lock.")
            # --- End Lock ---

        # --- Trigger Updates (outside lock) ---
        if needs_cf_update:
            logging.info("[Reconcile] Triggering Cloudflare tunnel config update based on reconciliation results.")
            if update_cloudflare_config():
                 # CF update successful, now check/create DNS for newly active rules
                 if hostnames_requiring_dns_check:
                      logging.info(f"[Reconcile] Checking/Creating DNS records for newly active/reactivated rules: {hostnames_requiring_dns_check}")
                      for hostname in hostnames_requiring_dns_check:
                           if tunnel_state.get("id") and CF_ZONE_ID:
                                if not create_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"]):
                                     # Log error if DNS fails after successful CF update
                                     logging.error(f"[Reconcile] CRITICAL: Failed to ensure DNS record exists for {hostname} after successful tunnel config update.")
                           else:
                                logging.error(f"[Reconcile] Cannot check/create DNS for {hostname}: Missing Tunnel ID or Zone ID.")
            else:
                # CF update failed
                logging.error("[Reconcile] Failed to update Cloudflare tunnel config during reconciliation. DNS checks for newly active rules skipped. CF may be out of sync.")
        elif state_changed_locally:
            # Only local state changed (e.g., container ID, rule marked pending)
            logging.info("[Reconcile] Reconciliation resulted in local state changes only (no CF tunnel config update needed).")
        else:
            # No changes needed at all
            logging.info("[Reconcile] No changes required by reconciliation.")

    except Exception as e:
        # Catch any unexpected errors during the entire reconciliation process
        logging.error(f"Unexpected error during state reconciliation: {e}", exc_info=True)
    finally:
        logging.info("Reconciliation complete.")


# --- get_cloudflared_container ---
def get_cloudflared_container():
    if not docker_client:
        logging.warning("Docker client not available when trying to get cloudflared container.")
        return None
    try:
        # Try to get the container by its defined name
        container = docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
        return container
    except NotFound:
        # Container simply doesn't exist
        logging.debug(f"Cloudflared container '{CLOUDFLARED_CONTAINER_NAME}' not found.")
        return None
    except APIError as e:
        # Error communicating with Docker API (permissions, daemon issue)
        logging.error(f"Docker API error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker API error getting agent: {e}"
        return None
    except requests.exceptions.ConnectionError as e:
        # Error connecting to the Docker daemon socket
        logging.error(f"Failed to connect to Docker daemon while getting container: {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed getting agent: {e}"
        return None
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"Unexpected error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected error getting agent: {e}"
        return None


# --- update_cloudflared_container_status ---
def update_cloudflared_container_status():
    global docker_client # Allow modification if reconnection occurs
    if not docker_client:
        logging.warning("Docker client unavailable, attempting to reconnect...")
        try:
            # Try to re-initialize the client
            docker_client = docker.from_env(timeout=5)
            docker_client.ping()
            logging.info("Successfully reconnected to Docker daemon.")
            # Reset status if it was previously unavailable
            if cloudflared_agent_state["container_status"] == "docker_unavailable":
                 cloudflared_agent_state["container_status"] = "unknown" # Re-assess status
        except Exception as e:
             # Reconnection failed
             logging.error(f"Failed to reconnect to Docker daemon: {e}")
             if cloudflared_agent_state["container_status"] != "docker_unavailable":
                 logging.warning("Setting agent status to docker_unavailable.")
                 cloudflared_agent_state["container_status"] = "docker_unavailable"
             docker_client = None # Ensure client is None if connection failed
             return # Cannot proceed without client

    # Try to get the container object
    container = get_cloudflared_container()

    if container:
        try:
            # Refresh container data from Docker daemon
            container.reload()
            new_status = container.status # e.g., 'running', 'exited', 'created'
            # Update global state only if status actually changed
            if cloudflared_agent_state["container_status"] != new_status:
                 logging.info(f"Cloudflared agent container status changed to: {new_status}")
                 cloudflared_agent_state["container_status"] = new_status
                 # Clear last action status if it becomes running
                 if new_status == 'running':
                     cloudflared_agent_state["last_action_status"] = None
        except (NotFound, APIError) as e:
            # Handle cases where container disappears or API error occurs during reload
            if cloudflared_agent_state["container_status"] != "not_found":
                 logging.warning(f"Error reloading cloudflared container status (container likely removed or API issue): {e}")
                 cloudflared_agent_state["container_status"] = "not_found" # Or maybe 'error'?
                 cloudflared_agent_state["last_action_status"] = "Agent container disappeared or API error during status check."
        except requests.exceptions.ConnectionError as e:
            # Handle connection error specifically during reload
            logging.error(f"Failed to connect to Docker daemon during status update: {e}")
            cloudflared_agent_state["container_status"] = "docker_unavailable"
            docker_client = None # Mark client as unusable
            return
    else:
        # Container object couldn't be retrieved (might be 'not_found' or due to API/connection error)
        current_status = cloudflared_agent_state.get("container_status", "unknown")
        # Update status to 'not_found' only if it wasn't already known to be unavailable/not found
        if current_status not in ["not_found", "docker_unavailable"]:
            logging.info("Cloudflared agent container not found.")
            cloudflared_agent_state["container_status"] = "not_found"


# --- ensure_docker_network_exists ---
def ensure_docker_network_exists(network_name):
    if not docker_client:
        logging.error("Docker client unavailable, cannot check/create network.")
        return False
    try:
        # Check if network already exists
        docker_client.networks.get(network_name)
        logging.info(f"Docker network '{network_name}' already exists.")
        return True
    except NotFound:
        # Network doesn't exist, try creating it
        logging.info(f"Docker network '{network_name}' not found. Creating...")
        try:
            # Create a bridge network, check_duplicate handles race condition
            docker_client.networks.create(network_name, driver="bridge", check_duplicate=True)
            logging.info(f"Successfully created Docker network '{network_name}'.")
            return True
        except APIError as e:
            # Handle specific API errors during creation
            if "already exists" in str(e): # Check if created concurrently
                 logging.warning(f"Docker network '{network_name}' already exists (created concurrently?).")
                 return True
            # Log other creation errors
            logging.error(f"Failed to create Docker network '{network_name}': {e}", exc_info=True)
            cloudflared_agent_state["last_action_status"] = f"Error creating network: {e}"
            return False
    except APIError as e:
        # Handle errors during the initial 'get' check
        logging.error(f"Error checking for Docker network '{network_name}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error checking network: {e}"
        return False
    except requests.exceptions.ConnectionError as e:
        # Handle connection errors
        logging.error(f"Failed to connect to Docker daemon checking network '{network_name}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed checking network."
        return False
    except Exception as e:
        # Handle any other unexpected errors
        logging.error(f"Unexpected error checking/creating Docker network '{network_name}': {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected error checking network: {e}"
        return False


# --- start_cloudflared_container ---
def start_cloudflared_container():
    logging.info(f"Attempting to start cloudflared agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Starting..." # Update UI status
    success_flag = False # Track overall success

    try:
        # --- Prerequisites ---
        if not docker_client:
             msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
        if not tunnel_state.get("token"):
             msg = "Tunnel token not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        # Ensure the target Docker network exists
        # Moved network check here, as it's essential before starting
        if not ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME):
             # Error message already set by ensure_docker_network_exists
             logging.error(f"Failed to ensure Docker network '{CLOUDFLARED_NETWORK_NAME}' exists. Cannot start agent.")
             return False

        token = tunnel_state["token"] # Get the tunnel token

        # --- Check Existing Container ---
        container = get_cloudflared_container()
        needs_recreate = False # Flag if existing container is misconfigured

        if container:
             try:
                 container.reload() # Refresh container state
                 logging.info(f"Found existing container '{CLOUDFLARED_CONTAINER_NAME}' with status: {container.status}")

                 # Check if already running
                 if container.status == 'running':
                      msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is already running."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True # Already running, success!

                 # --- Configuration Check ---
                 # Check if container is on the correct network
                 container_networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
                 is_on_correct_network = CLOUDFLARED_NETWORK_NAME in container_networks

                 # Check if using host network mode (which we don't want)
                 network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', 'default')
                 is_host_network = network_mode == CLOUDFLARED_NETWORK_NAME or network_mode == 'host'

                 if is_host_network:
                      logging.warning(f"Existing container '{CLOUDFLARED_CONTAINER_NAME}' is in 'host' network mode or network name matches host mode identifier. Needs recreation on bridge network '{CLOUDFLARED_NETWORK_NAME}'.")
                      needs_recreate = True
                 elif not is_on_correct_network:
                      logging.warning(f"Existing container '{CLOUDFLARED_CONTAINER_NAME}' is not connected to the desired network '{CLOUDFLARED_NETWORK_NAME}'. Current networks: {list(container_networks.keys())}. Needs recreation.")
                      needs_recreate = True
                 # Optional: Add checks for command, image, restart policy if desired

                 if needs_recreate:
                      # Remove the misconfigured container
                      logging.info(f"Removing misconfigured container '{CLOUDFLARED_CONTAINER_NAME}' before creating a new one.")
                      try:
                          container.remove(force=True) # Force remove even if stopped uncleanly
                          container = None # Mark as removed
                      except (APIError, requests.exceptions.ConnectionError) as rm_err:
                           logging.error(f"Failed to remove misconfigured container: {rm_err}. Proceeding to create might fail if name conflicts.")
                           # Keep container object to potentially avoid creating a new one if remove failed badly
                 else:
                      # Existing container is correctly configured but stopped, just start it
                      logging.info(f"Starting existing correctly configured container '{CLOUDFLARED_CONTAINER_NAME}'...");
                      container.start()
                      msg = f"Started existing container '{CLOUDFLARED_CONTAINER_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True
                      # Skip creation logic below

             except (NotFound, APIError) as e:
                  # Error checking existing container (e.g., disappeared between get and reload)
                  logging.warning(f"Error checking existing container '{CLOUDFLARED_CONTAINER_NAME}': {e}. Assuming it needs creation.")
                  container = None # Treat as if not found
             except requests.exceptions.ConnectionError as e:
                  logging.error(f"Failed to connect to Docker daemon checking existing container: {e}")
                  cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed checking agent."
                  return False

        # --- Create Container (if needed) ---
        if not container and not success_flag: # Only create if not found/removed and not already started
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found or needs recreation. Creating...")
            try:
                # Pull the latest image (optional, but good practice)
                try:
                    logging.info(f"Pulling image {CLOUDFLARED_IMAGE}...");
                    docker_client.images.pull(CLOUDFLARED_IMAGE)
                    logging.info(f"Successfully pulled {CLOUDFLARED_IMAGE} (or it was up-to-date).")
                except APIError as img_err:
                    # Log warning but proceed, Docker run will attempt pull anyway
                    logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Docker run will attempt to pull.")
                except requests.exceptions.ConnectionError as e:
                    # Fail fast if Docker connection lost during pull
                    logging.error(f"Failed to connect to Docker daemon during image pull: {e}")
                    cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed pulling image."
                    return False

                # Define container parameters
                container_params = {
                    "image": CLOUDFLARED_IMAGE,
                    "command": f"tunnel --no-autoupdate run --token {token}",
                    "name": CLOUDFLARED_CONTAINER_NAME,
                    "network": CLOUDFLARED_NETWORK_NAME, # Connect to our specific network
                    "restart_policy": {"Name": "unless-stopped"}, # Restart if crashes/host reboots
                    "detach": True, # Run in background
                    "remove": False, # Keep container filesystem after stop (for logs etc.)
                    "labels": {"managed-by": "cloudflare-tunnel-ingress-controller"} # Identify container
                    # Optional: Add volume mounts if needed for config files (though token is preferred)
                    # "volumes": { ... }
                }

                # Run the container
                new_container = docker_client.containers.run(**container_params)
                msg = f"Created and started container '{new_container.name}' ({new_container.id[:12]}) on network '{CLOUDFLARED_NETWORK_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

            except APIError as create_err:
                # Handle specific creation errors, especially name conflicts
                if "is already in use" in str(create_err):
                     logging.error(f"Container name '{CLOUDFLARED_CONTAINER_NAME}' is already in use by another container. This might happen if removal of a misconfigured container failed.")
                     # Attempt to find and log the conflicting container ID
                     try:
                          stale_container = docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
                          logging.error(f"Conflicting container ID: {stale_container.id[:12]}")
                          msg = f"Error: Container name conflict with existing container {stale_container.id[:12]}. Please remove it manually and retry."
                     except (NotFound, APIError, requests.exceptions.ConnectionError):
                          msg = f"Error: Container name conflict, but failed to get conflicting container details. {create_err}"
                else:
                     # Other API errors during creation
                     msg = f"Docker API error creating container: {create_err}"; logging.error(msg, exc_info=True)
                cloudflared_agent_state["last_action_status"] = msg; success_flag = False
            except requests.exceptions.ConnectionError as e:
                 # Handle connection error during run
                 logging.error(f"Failed to connect to Docker daemon during container run: {e}")
                 cloudflared_agent_state["last_action_status"] = f"Error: Docker connection failed running agent."
                 success_flag = False

    # --- Catch General Errors ---
    except APIError as e:
        # Catch API errors not caught in specific blocks above
        msg = f"Docker API error during start sequence: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except requests.exceptions.ConnectionError as e:
        # Catch connection errors not caught above
        msg = f"Failed to connect to Docker daemon during start sequence: {e}"; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        # Catch any other unexpected errors
        msg = f"Unexpected error starting container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False

    # --- Final Status Update ---
    finally:
        if docker_client:
             logging.debug("Updating container status after start attempt...")
             # Give agent a moment to potentially start/stabilize before checking status
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
        # Check Docker client
        if not docker_client:
            msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        # Get the container
        container = get_cloudflared_container()
        if not container:
            # Already stopped or never existed
            msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found, cannot stop (already stopped?)."; logging.warning(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True

        # Reload to get current status
        container.reload()
        if container.status != 'running':
             # Not running, nothing to do
             msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is not running (status: {container.status}). No action needed."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True

        # Stop the running container
        logging.info(f"Stopping running container '{CLOUDFLARED_CONTAINER_NAME}'...");
        container.stop(timeout=30) # Give it 30 seconds to stop gracefully
        msg = f"Successfully stopped container '{CLOUDFLARED_CONTAINER_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

    except (APIError, NotFound) as e: # Catch API errors or if container disappears during stop
        msg = f"Docker API error stopping container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except requests.exceptions.ConnectionError as e:
        msg = f"Failed to connect to Docker daemon stopping container: {e}"; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        msg = f"Unexpected error stopping container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        # Update status after attempting stop
        if docker_client:
             logging.debug("Updating container status after stop attempt..."); time.sleep(2); update_cloudflared_container_status()
        logging.info(f"Exiting stop_cloudflared_container function (Success: {success_flag}).")
        return success_flag

# --- Flask App Setup ---
app = Flask(__name__) # Flask will automatically look for templates in a 'templates' folder
app.secret_key = os.urandom(24) # Needed for flash messages or sessions if used later


# --- get_display_token ---
def get_display_token(token):
    """Masks the token for display purposes."""
    if not token: return "Not available"
    # Show first 5 and last 5 characters
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token retrieved (short)"


# --- status_page ---
@app.route('/')
def status_page():
    # Always update status before rendering
    update_cloudflared_container_status()

    # Prepare data for the template, ensuring thread safety
    with state_lock:
        # Create a deep copy or carefully structure data for the template
        # Pass datetime objects directly for Jinja formatting
        rules_for_template = {}
        for hn, rule in managed_rules.items():
            # Pass the rule dictionary; Jinja handles datetime formatting
            rules_for_template[hn] = rule.copy()

        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()

    display_token = get_display_token(template_tunnel_state.get("token"))
    docker_available = docker_client is not None

    # Use render_template to load and render the HTML file
    return render_template('status_page.html',  # Points to templates/status_page.html
                            tunnel_state=template_tunnel_state,
                            agent_state=template_agent_state,
                            display_token=display_token,
                            cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                            docker_available=docker_available,
                            rules=rules_for_template) # Pass the prepared rules


# --- start_tunnel ---
@app.route('/start', methods=['POST'])
def start_tunnel():
    logging.info("Received request to start tunnel agent via UI.")
    start_cloudflared_container()
    # Optional: Add flash message here for feedback
    time.sleep(1) # Give status update a moment
    return redirect(url_for('status_page'))


# --- stop_tunnel ---
@app.route('/stop', methods=['POST'])
def stop_tunnel():
    logging.info("Received request to stop tunnel agent via UI.")
    stop_cloudflared_container()
    # Optional: Add flash message here for feedback
    time.sleep(1) # Give status update a moment
    return redirect(url_for('status_page'))


# --- force_delete_rule ---
@app.route('/force_delete/<hostname>', methods=['POST'])
def force_delete_rule(hostname):
    logging.info(f"Received request to force delete rule for hostname: {hostname}")
    rule_removed_from_state = False
    dns_delete_success = False

    # Step 1: Delete DNS record immediately
    if tunnel_state.get("id") and CF_ZONE_ID:
        logging.info(f"Attempting DNS record deletion for force-deleted rule: {hostname}")
        dns_delete_success = delete_cloudflare_dns_record(CF_ZONE_ID, hostname, tunnel_state["id"])
        if not dns_delete_success:
             # Log error but continue, as user requested force delete
             logging.error(f"Failed to delete DNS record for {hostname} during force delete. Tunnel config update will proceed, but DNS record may remain stale.")
             # Update UI status (can be improved with flash messages)
             cloudflared_agent_state["last_action_status"] = f"Warning: Failed deleting DNS record for {hostname}. Tunnel update proceeding."
    else:
        logging.error(f"Cannot delete DNS for {hostname}: Missing Tunnel ID or Zone ID.")
        cloudflared_agent_state["last_action_status"] = f"Error: Cannot delete DNS for {hostname} (missing config)."
        # Proceed with state removal, but DNS couldn't be touched

    # Step 2: Remove rule from local state
    with state_lock:
        if hostname in managed_rules:
            logging.info(f"Force deleting rule for {hostname} from local state.")
            del managed_rules[hostname]
            rule_removed_from_state = True
            save_state() # Save state immediately after removal
        else:
            # Rule might have been deleted by cleanup task already
            logging.warning(f"Attempted force delete for hostname '{hostname}', but it was not found in managed rules (perhaps already deleted or cleaned up).")
            # Treat as success in terms of state removal
            rule_removed_from_state = True

    # Step 3: Trigger Cloudflare config update to remove the rule
    if rule_removed_from_state: # Only update CF if state was actually changed or rule confirmed gone
        logging.info(f"Triggering Cloudflare tunnel config update after force deleting {hostname} (or confirming removal).")
        if update_cloudflare_config():
            logging.info(f"Cloudflare tunnel config update successful after force deleting {hostname}.")
            # Set final status message based on DNS success
            if dns_delete_success:
                 cloudflared_agent_state["last_action_status"] = f"Successfully force deleted rule and DNS record for {hostname} and updated Cloudflare."
            else:
                 # DNS failed earlier, but state and CF updated
                 cloudflared_agent_state["last_action_status"] = f"Force deleted rule for {hostname} (DNS delete failed/skipped earlier, but tunnel config updated)."
        else:
            # This is a bad state: State removed, DNS maybe removed, CF update FAILED
            logging.error(f"CRITICAL: State saved after force delete of {hostname}, DNS delete status: {dns_delete_success}, but subsequent Cloudflare tunnel config update FAILED!")
            cloudflared_agent_state["last_action_status"] = f"Error: Removed {hostname} locally, DNS delete status: {dns_delete_success}, but FAILED pushing tunnel config update! Reconciliation needed."

    time.sleep(1) # Allow UI status to potentially update
    return redirect(url_for('status_page'))


# --- run_background_tasks ---
def run_background_tasks():
    """Starts the Docker event listener and cleanup threads."""
    if not docker_client:
        logging.warning("Docker client not available. Background tasks (event listener, cleanup) will not start.")
        return None, None
    if not tunnel_state.get("id"):
         logging.warning("Tunnel not initialized. Background tasks (event listener, cleanup) will not start.")
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

    # Load initial state from file
    load_state()
    logging.info("Initial state loading complete.")
    event_thread = None
    cleanup_thread = None

    # --- Critical Pre-checks ---
    if not CF_ZONE_ID:
        logging.error("FATAL: CF_ZONE_ID environment variable is missing. DNS management will fail.")
        # Update state for UI feedback before exiting
        tunnel_state["status_message"] = "Error: CF_ZONE_ID missing."
        tunnel_state["error"] = "CF_ZONE_ID environment variable must be set."
        # Render a minimal error page or just exit? Exiting seems appropriate.
        sys.exit(1) # Exit if critical config missing

    if not docker_client:
         # Docker client failed to connect at startup
         logging.error("Docker client is unavailable at startup. Limited functionality.")
         tunnel_state["status_message"] = "Error: Docker client unavailable."
         tunnel_state["error"] = "Failed to connect to Docker daemon. Check socket mount and permissions."
         cloudflared_agent_state["container_status"] = "docker_unavailable"
         logging.warning("Skipping tunnel initialization, reconciliation, agent management, and background tasks due to Docker connection failure.")
         # Continue to run Flask to show the error state? Yes.
    else:
         # --- Normal Startup Flow ---
         logging.info("Docker client available.")

         # Ensure network exists early - Temporarily Commented Out
         logging.info(f"Ensuring Docker network '{CLOUDFLARED_NETWORK_NAME}' exists... (Check deferred)")
         # ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME) # <-- Temporarily commented out

         # Initialize Cloudflare Tunnel (find or create, get token)
         # ADDED DEBUG LOGGING HERE (Keep this line for now)
         logging.info("[DEBUG] >>> About to call initialize_tunnel()...")
         initialize_tunnel()
         logging.info(f"Tunnel initialization process complete. Status: {tunnel_state.get('status_message')}")
         logging.debug(f"Tunnel State after init: ID={tunnel_state.get('id')}, Token Present={bool(tunnel_state.get('token'))}, Error={tunnel_state.get('error')}")

         # Proceed only if tunnel setup was successful
         if tunnel_state.get("id") and tunnel_state.get("token"):
             logging.info("Tunnel initialized successfully. Proceeding with reconciliation and agent checks.")

             # Run initial reconciliation to sync state
             reconcile_state()
             logging.info("Initial state reconciliation complete.")

             # Check agent status and start if needed
             logging.info("Checking and attempting to automatically start tunnel agent container if needed...")
             update_cloudflared_container_status() # Get current status
             if cloudflared_agent_state.get("container_status") != 'running':
                 logging.info("Agent container not running, attempting auto-start...")
                 start_cloudflared_container() # Try to start it
             else:
                 logging.info("Agent container already running.")

             # Start background tasks (event listener, cleanup)
             event_thread, cleanup_thread = run_background_tasks()
         else:
             # Tunnel setup failed, log warning and skip dependent steps
             logging.warning("Tunnel not fully initialized (missing ID or Token). Skipping reconciliation, agent start, and background tasks.")
             # Ensure status message reflects this if no specific error was set
             if not tunnel_state.get("error"):
                 tunnel_state["status_message"] = "Tunnel setup incomplete (ID/Token missing)."

    # --- Start Web Server ---
    logging.info("Starting Flask application web server...")
    flask_thread = None
    try:
        # Use Waitress for a more production-ready server than Flask's default
        from waitress import serve
        # Run Waitress in a separate thread so main thread can monitor
        flask_thread = threading.Thread(
            target=serve,
            args=(app,),
            kwargs={'host':'0.0.0.0','port':5000},
            daemon=True, # Allow main thread to exit even if this thread is running
            name="FlaskWaitressServer"
        )
        flask_thread.start()
        logging.info("Flask server started using waitress on 0.0.0.0:5000 in a background thread.")

        # Keep main thread alive to monitor background tasks and handle shutdown
        while True:
             all_threads_alive = True
             if flask_thread and not flask_thread.is_alive():
                  logging.error("Flask server thread terminated unexpectedly.")
                  all_threads_alive = False
             # Check background tasks only if they were expected to start
             if event_thread and not event_thread.is_alive():
                  logging.warning("Docker event listener thread terminated unexpectedly.")
                  # Optionally restart? For now, just log.
             if cleanup_thread and not cleanup_thread.is_alive():
                  logging.warning("Cleanup thread terminated unexpectedly.")
                  # Optionally restart? For now, just log.

             if not all_threads_alive:
                  logging.error("A critical thread terminated. Initiating shutdown.")
                  stop_event.set() # Signal other threads to stop
                  break # Exit main loop

             if stop_event.is_set(): # Check if shutdown was initiated elsewhere
                  logging.info("Stop event detected in main loop.")
                  break

             time.sleep(10) # Check thread status periodically

    except ImportError:
        logging.warning("Waitress not found. Falling back to Flask development server (use 'pip install waitress' for production).")
        # Run Flask's built-in server directly (blocks main thread)
        app.run(host='0.0.0.0', port=5000) # Note: Not suitable for production
    except KeyboardInterrupt:
         logging.info("KeyboardInterrupt received.")
    except Exception as server_err:
        logging.error(f"Web server encountered a fatal error: {server_err}", exc_info=True)
    finally:
        # --- Shutdown Sequence ---
        logging.info("Shutdown sequence initiated...")
        stop_event.set() # Signal background threads to stop gracefully
        logging.info("Stop event set for background threads.")

        # Optional: Wait briefly for threads to exit?
        # if event_thread: event_thread.join(timeout=5)
        # if cleanup_thread: cleanup_thread.join(timeout=5)

        logging.info("Exiting Cloudflare Tunnel Ingress Manager application.")
        # Determine exit code based on final state
        exit_code = 0
        if tunnel_state.get("error") or cloudflared_agent_state.get("container_status") == "docker_unavailable":
             exit_code = 1 # Exit with error if critical issues exist
        sys.exit(exit_code)