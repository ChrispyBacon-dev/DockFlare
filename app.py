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
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_ZONE_ID = os.getenv('CF_ZONE_ID')
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}

# External cloudflared container configuration
USE_EXTERNAL_CLOUDFLARED = os.getenv('USE_EXTERNAL_CLOUDFLARED', 'false').lower() in ['true', '1', 't', 'yes']
EXTERNAL_TUNNEL_ID = os.getenv('EXTERNAL_TUNNEL_ID')

# Network scanning configuration
SCAN_ALL_NETWORKS = os.getenv('SCAN_ALL_NETWORKS', 'false').lower() in ['true', '1', 't', 'yes']

# Settings that are only required when NOT using external cloudflared
TUNNEL_NAME = os.getenv("TUNNEL_NAME", "dockflared-tunnel")
CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net') if not USE_EXTERNAL_CLOUDFLARED else None
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}") if not USE_EXTERNAL_CLOUDFLARED else None
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"

# Settings used in both modes
LABEL_PREFIX = os.getenv('LABEL_PREFIX', 'cloudflare.tunnel')
GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 28800))
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 300))
AGENT_STATUS_UPDATE_INTERVAL_SECONDS = int(os.getenv('AGENT_STATUS_UPDATE_INTERVAL_SECONDS', 10))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')
MAX_LOG_QUEUE_SIZE = 200

# Performance settings
MAX_CONCURRENT_DNS_OPS = int(os.getenv('MAX_CONCURRENT_DNS_OPS', 3))
RECONCILIATION_BATCH_SIZE = int(os.getenv('RECONCILIATION_BATCH_SIZE', 3))
dns_semaphore = threading.Semaphore(MAX_CONCURRENT_DNS_OPS)

# Validate required configuration
required_vars = ["CF_API_TOKEN", "CF_ACCOUNT_ID"]
missing_vars = [var for var in required_vars if not globals().get(var)]

if not USE_EXTERNAL_CLOUDFLARED:
    if not TUNNEL_NAME:
        missing_vars.append("TUNNEL_NAME")
else:
    if not EXTERNAL_TUNNEL_ID:
        missing_vars.append("EXTERNAL_TUNNEL_ID")

if missing_vars:
    logging.error(f"FATAL: Missing required environment variables ({', '.join(missing_vars)})")
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
    """Retrieves the Zone ID for a given zone name, using cache with timeout."""
    global zone_id_cache
    if not zone_name:
        logging.warning("get_zone_id_from_name called with empty zone_name.")
        return None

    # Add cache expiration check (24 hours)
    cache_ttl = 86400  # 24 hours in seconds
    current_time = time.time()

    with state_lock:
        # Check if we have a cached entry that's not expired
        cached_data = zone_id_cache.get(zone_name)
        if cached_data:
            zone_id, timestamp = cached_data
            if current_time - timestamp < cache_ttl:
                logging.debug(f"Zone ID for '{zone_name}' found in cache: {zone_id}")
                return zone_id
            else:
                logging.debug(f"Cached Zone ID for '{zone_name}' expired, refreshing")

    logging.info(f"Zone ID for '{zone_name}' not in cache or expired. Querying Cloudflare API...")
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
                    # Store with timestamp
                    zone_id_cache[zone_name] = (zone_id, current_time)
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
    
    # Add detailed logging to help diagnose issues
    logging.info(f"Using Cloudflare Account ID: {CF_ACCOUNT_ID}")
    logging.info(f"API Token available: {'Yes (Token masked for security)' if CF_API_TOKEN else 'No (Missing API token)'}")
    logging.info(f"Zone ID available: {'Yes: ' + CF_ZONE_ID if CF_ZONE_ID else 'No (Missing Zone ID)'}")
    logging.info(f"External mode: {USE_EXTERNAL_CLOUDFLARED}")
    logging.info(f"External tunnel ID: {EXTERNAL_TUNNEL_ID}")
    
    tunnel_state["status_message"] = "Checking tunnel configuration..."
    tunnel_state["error"] = None
    
    # If external cloudflared is configured, use its tunnel ID only
    if USE_EXTERNAL_CLOUDFLARED:
        logging.info("External cloudflared configuration detected")
        if EXTERNAL_TUNNEL_ID:
            tunnel_id = EXTERNAL_TUNNEL_ID
            logging.info(f"Using external tunnel ID: {tunnel_id}")
            tunnel_state["id"] = tunnel_id
            # We don't need the token since we don't manage the container
            tunnel_state["token"] = None
            tunnel_state["status_message"] = "Using external tunnel to manage DNS and inbound routes."
            
            # Add containers with DockFlare labels to managed rules
            logging.info("Scanning for containers with DockFlare labels in external mode...")
            try:
                containers = docker_client.containers.list(all=SCAN_ALL_NETWORKS)
                for container in containers:
                    process_container_start(container)
            except Exception as e:
                logging.error(f"Error scanning containers in external mode: {e}", exc_info=True)
                
            logging.info(f"External tunnel (ID: {tunnel_id}) initialized for DNS and inbound routes management.")
            return
        else:
            logging.warning("USE_EXTERNAL_CLOUDFLARED is enabled but EXTERNAL_TUNNEL_ID is not provided.")
            tunnel_state["status_message"] = "Error: External tunnel config missing tunnel ID."
            tunnel_state["error"] = "External cloudflared enabled but missing tunnel ID"
            return
    
    # Regular tunnel initialization code - only runs when not in external mode
    # Check if TUNNEL_NAME is provided
    if not TUNNEL_NAME:
        logging.error("TUNNEL_NAME not provided. Required when not using external cloudflared.")
        tunnel_state["status_message"] = "Error: Missing required TUNNEL_NAME parameter"
        tunnel_state["error"] = "TUNNEL_NAME not provided"
        return

    # Regular tunnel initialization code
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

def is_valid_hostname(hostname):
    """
    Validates a hostname, including support for wildcards.
    Accepts standard hostnames and wildcard domains like *.example.com
    """
    if not hostname:
        return False
        
    # Handle wildcard domains (*.example.com)
    if hostname.startswith('*.'):
        # Remove the wildcard part and validate the rest as a normal domain
        domain_part = hostname[2:]  # Skip the *. prefix
        
        # Domain validation for the rest
        if not domain_part or len(domain_part) > 253:
            return False
            
        for label in domain_part.split('.'):
            if not label or len(label) > 63:
                return False
            if not all(c.isalnum() or c == '-' for c in label):
                return False
            if label.startswith('-') or label.endswith('-'):
                return False
                
        return True
        
    # Standard hostname validation (unchanged)
    if len(hostname) > 253:
        return False
    
    labels = hostname.split('.')
    
    # Check each label
    for label in labels:
        if not label or len(label) > 63:
            return False
        if not all(c.isalnum() or c == '-' for c in label):
            return False
        if label.startswith('-') or label.endswith('-'):
            return False
    
    return True

def is_valid_service(service):
    if not service: return False
    return (re.match(r"^(https?|tcp|unix)://", service) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", service)) is not None

def create_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    """Creates a CNAME DNS record pointing to the tunnel, handling existing records correctly."""
    # Acquire semaphore in a try-finally block to ensure it's always released
    try:
        acquired = dns_semaphore.acquire(timeout=30)  # Add timeout to prevent deadlocks
        if not acquired:
            logging.error(f"Timed out waiting for DNS semaphore - too many concurrent operations. Skipping DNS creation for {hostname}")
            return "semaphore_timeout"  # Return a special code so caller knows what happened
            
        if not zone_id or not hostname or not tunnel_id:
            logging.error("create_cloudflare_dns_record: Missing required arguments.")
            return None

        # First check if a record already exists with tunnel content
        existing_record_id, correct_tunnel = find_dns_record_id(zone_id, hostname, tunnel_id)
        
        if existing_record_id:
            if correct_tunnel:
                logging.info(f"DNS record for {hostname} already exists with ID {existing_record_id} and correct tunnel. Using existing record.")
                return existing_record_id
            else:
                # Record exists but points to wrong tunnel - update it
                logging.warning(f"DNS record for {hostname} exists (ID: {existing_record_id}) but points to wrong tunnel. Updating...")
                
                update_payload = {
                    "type": "CNAME",
                    "name": hostname,
                    "content": f"{tunnel_id}.cfargotunnel.com",
                    "ttl": 1,
                    "proxied": True
                }
                
                update_endpoint = f"/zones/{zone_id}/dns_records/{existing_record_id}"
                try:
                    logging.info(f"Updating existing DNS record for {hostname} to point to correct tunnel {tunnel_id}")
                    update_response = cf_api_request("PUT", update_endpoint, json_data=update_payload)
                    updated_record = update_response.get("result", {})
                    updated_id = updated_record.get("id")
                    if updated_id:
                        logging.info(f"Successfully updated DNS record for {hostname} to point to correct tunnel. ID: {updated_id}")
                        return updated_id
                    else:
                        logging.error(f"DNS record update API call for {hostname} reported success but response missing ID")
                        return existing_record_id  # Return existing ID as fallback
                except Exception as update_err:
                    logging.error(f"Error updating existing DNS record for {hostname}: {update_err}")
                    return existing_record_id  # Return existing ID as best effort
        
        # If no records found, continue with creation
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
            # Special handling for errors about duplicate records
            if (cf_error_code == 81057 or 
                (e.response is not None and (
                    "record already exists" in e.response.text.lower() or 
                    "a, aaaa, or cname record with that host already exists" in e.response.text.lower()
                ))
            ):
                logging.warning(f"DNS record for {hostname} already exists in zone {zone_id}. Treating as success.")
                # Try to locate the record again after creation failure
                time.sleep(1)  # Brief pause before retrying lookup
                existing_id, _ = find_dns_record_id(zone_id, hostname, tunnel_id)
                if existing_id:
                    logging.info(f"Found existing record ID for {hostname}: {existing_id}")
                    return existing_id
                    
                # Fallback - return placeholder to indicate record exists
                return "existing_record" 
            else:
                logging.error(f"API error creating DNS record for {hostname}: {e}")
                return None
        except Exception as e:
            logging.error(f"Unexpected error creating DNS record for {hostname}: {e}", exc_info=True)
            return None
    finally:
        # Always release the semaphore if we acquired it
        if 'acquired' in locals() and acquired:
            dns_semaphore.release()
            logging.debug(f"Released DNS semaphore after processing {hostname}")

def find_dns_record_id(zone_id, hostname, tunnel_id):
    """Finds the ID of a specific CNAME DNS record pointing to the tunnel."""
    # Use semaphore with a timeout to prevent deadlocks
    try:
        acquired = dns_semaphore.acquire(timeout=15)
        if not acquired:
            logging.error(f"Timed out waiting for DNS semaphore in find_dns_record_id for {hostname}")
            return None, False

        if not zone_id or not hostname or not tunnel_id:
            logging.error("find_dns_record_id: Missing required arguments.")
            return None, False

        expected_content = f"{tunnel_id}.cfargotunnel.com"
        endpoint = f"/zones/{zone_id}/dns_records"
        
        # First search for exact match (correct hostname and tunnel)
        params = {"type": "CNAME", "name": hostname, "content": expected_content, "match": "all"}

        try:
            logging.info(f"Searching DNS: Zone={zone_id}, Type=CNAME, Name={hostname}, Content={expected_content}")
            response_data = cf_api_request("GET", endpoint, params=params)
            results = response_data.get("result", [])

            if results and isinstance(results, list):
                record_id = results[0].get("id")
                if record_id:
                    logging.info(f"Found DNS record for {hostname} in zone {zone_id} with ID: {record_id}")
                    return record_id, True  # Return True as second value to indicate correct tunnel
                else:
                    logging.warning(f"DNS record found for {hostname} but it lacks an ID field: {results[0]}")
                    return None, False
            
            # If no exact match found, search for any record with this hostname (may point to wrong tunnel)
            params = {"type": "CNAME", "name": hostname}
            response_data = cf_api_request("GET", endpoint, params=params)
            results = response_data.get("result", [])
            
            if results and isinstance(results, list):
                record_id = results[0].get("id")
                record_content = results[0].get("content", "")
                if record_id:
                    logging.warning(f"Found DNS record for {hostname} but it points to {record_content} instead of {expected_content}")
                    return record_id, False  # Return False as second value to indicate wrong tunnel
                
            logging.info(f"No matching DNS record found for {hostname} in zone {zone_id}")
            return None, False
        except requests.exceptions.RequestException as e:
            logging.error(f"API error finding DNS record for {hostname}: {e}")
            return None, False
        except Exception as e:
            logging.error(f"Unexpected error finding DNS record for {hostname}: {e}", exc_info=True)
            return None, False
    finally:
        if 'acquired' in locals() and acquired:
            dns_semaphore.release()
            logging.debug(f"Released DNS semaphore after find_dns_record_id for {hostname}")

def delete_cloudflare_dns_record(zone_id, hostname, tunnel_id):
    """Deletes the specific CNAME DNS record pointing to the tunnel."""
    with dns_semaphore:  # Use semaphore to limit concurrent DNS operations
        if not zone_id or not hostname or not tunnel_id:
            logging.error("delete_cloudflare_dns_record: Missing required arguments.")
            return False

        record_id, is_correct_tunnel = find_dns_record_id(zone_id, hostname, tunnel_id)
        if not record_id:
            logging.warning(f"DNS record for {hostname} in zone {zone_id} (pointing to tunnel {tunnel_id}) not found to delete. Assuming success.")
            return True

        logging.info(f"Attempting to delete DNS record for {hostname} in zone {zone_id} (ID: {record_id})")
        endpoint = f"/zones/{zone_id}/dns_records/{record_id}"
        try:
            cf_api_request("DELETE", endpoint)
            logging.info(f"Successfully deleted DNS record for {hostname} (ID: {record_id}) in zone {zone_id}.")
            return True
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 404:
                 logging.warning(f"DNS record {record_id} for {hostname} in zone {zone_id} not found during delete attempt (404). Treating as success.")
                 return True
            logging.error(f"API error deleting DNS record {record_id} for {hostname} in zone {zone_id}: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error deleting DNS record {record_id} for {hostname} in zone {zone_id}: {e}", exc_info=True)
            return False

def process_container_start(container):
    """Processes a container start event based on labels."""
    if not container:
        return

    container_id = None
    container_name = "Unknown"
    try:
        container_id = container.id
        container.reload()
        container_name = container.name

        labels = container.labels
        enabled_label = f"{LABEL_PREFIX}.enable"

        is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
        if not is_enabled:
            logging.debug(f"Ignoring start: {container_name} ({container_id[:12]}): '{enabled_label}' not true.")
            return

        # Look for both indexed and non-indexed hostname patterns
        hostnames_to_process = []
        
        # First, check for any direct labels (non-indexed format)
        hostname = labels.get(f"{LABEL_PREFIX}.hostname")
        service = labels.get(f"{LABEL_PREFIX}.service") 
        zone_name = labels.get(f"{LABEL_PREFIX}.zonename")
        no_tls_verify = labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]
        
        if hostname and service:
            if is_valid_hostname(hostname) and is_valid_service(service):
                hostnames_to_process.append({
                    "hostname": hostname,
                    "service": service,
                    "zone_name": zone_name,
                    "no_tls_verify": no_tls_verify
                })
            else:
                logging.warning(f"Ignoring invalid direct label pair for {container_name}: Invalid hostname '{hostname}' or service '{service}'")
        
        # Then check for indexed labels (cloudflare.tunnel.0.hostname, etc.)
        index = 0
        while True:
            prefix = f"{LABEL_PREFIX}.{index}"
            hostname = labels.get(f"{prefix}.hostname")
            if not hostname:
                # No more indexed hostnames found
                break
                
            service = labels.get(f"{prefix}.service")
            if not service:
                # Use the default service if available, otherwise warning and skip
                service = labels.get(f"{LABEL_PREFIX}.service")
                if not service:
                    logging.warning(f"Ignoring indexed hostname {hostname} for {container_name}: Missing service for index {index}")
                    index += 1
                    continue
            
            zone_name = labels.get(f"{prefix}.zonename", labels.get(f"{LABEL_PREFIX}.zonename"))
            no_tls_verify_value = labels.get(f"{prefix}.no_tls_verify", labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false"))
            no_tls_verify = no_tls_verify_value.lower() in ["true", "1", "t", "yes"]
            
            if is_valid_hostname(hostname) and is_valid_service(service):
                hostnames_to_process.append({
                    "hostname": hostname,
                    "service": service,
                    "zone_name": zone_name,
                    "no_tls_verify": no_tls_verify
                })
            else:
                logging.warning(f"Ignoring invalid indexed label pair for {container_name}: Invalid hostname '{hostname}' or service '{service}'")
            
            index += 1
        
        if not hostnames_to_process:
            logging.warning(f"No valid hostname configurations found for {container_name} ({container_id[:12]})")
            return
            
        logging.info(f"Found {len(hostnames_to_process)} hostname configurations for container {container_name}")
        
        # Process each hostname configuration
        state_changed_locally = False
        needs_cf_update = False
        
        for config in hostnames_to_process:
            hostname = config["hostname"]
            service = config["service"]
            zone_name = config["zone_name"]
            no_tls_verify = config["no_tls_verify"]
            
            target_zone_id = None
            if zone_name:
                logging.info(f"Hostname {hostname} specified zone name: '{zone_name}'. Looking up ID.")
                target_zone_id = get_zone_id_from_name(zone_name)
                if not target_zone_id:
                    logging.error(f"Failed to find Zone ID for specified name '{zone_name}' for hostname {hostname}. Skipping.")
                    continue
            else:
                logging.debug(f"Hostname {hostname} did not specify zone name. Using default Zone ID if available.")
                target_zone_id = CF_ZONE_ID

            if not target_zone_id:
                logging.error(f"Cannot manage DNS for {hostname}: No valid Zone ID found (label lookup failed and no default CF_ZONE_ID set?). Skipping.")
                continue
                
            logging.info(f"Managing {hostname} (from {container_name}) in Zone ID: {target_zone_id}")
            
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
            logging.debug(f"Saving state after processing start for container {container_name}.")
            save_state()

        if needs_cf_update:
            logging.info(f"Triggering Cloudflare config update due to changes for container {container_name}.")
            if update_cloudflare_config():
                logging.info(f"Tunnel config update successful for container {container_name}.")
                if tunnel_state.get("id"):
                    # Set up DNS records for each hostname
                    for config in hostnames_to_process:
                        hostname = config["hostname"]
                        zone_name = config["zone_name"]
                        
                        # Find the zone ID (either from zone_name or default)
                        target_zone_id = get_zone_id_from_name(zone_name) if zone_name else CF_ZONE_ID
                        
                        if target_zone_id:
                            dns_record_id = create_cloudflare_dns_record(target_zone_id, hostname, tunnel_state["id"])
                            if dns_record_id:
                                logging.info(f"DNS record management in zone {target_zone_id} successful for {hostname}.")
                            else:
                                logging.error(f"CRITICAL: Tunnel config updated for {hostname} but failed to create/verify DNS record in zone {target_zone_id}!")
                                cloudflared_agent_state["last_action_status"] = f"Error: Failed creating DNS for {hostname} in zone {target_zone_id}."
                        else:
                            logging.error(f"Missing Zone ID - cannot manage DNS record for {hostname}.")
                else:
                    logging.error(f"Missing Tunnel ID - cannot manage DNS records for container {container_name}.")
            else:
                logging.error(f"Failed to update Cloudflare tunnel config after processing start for container {container_name}. DNS records not managed.")

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
    """Initiates state reconciliation in a background thread to avoid stalling the WebUI."""
    if not docker_client:
        logging.warning("Docker client unavailable, skipping reconciliation.")
        return
    if not tunnel_state.get("id"):
        logging.warning("Tunnel not initialized, skipping reconciliation.")
        return

    # Set reconciliation status to in progress
    app.reconciliation_info = {
        "in_progress": True,
        "progress": 0,
        "total_items": 0,
        "processed_items": 0,
        "start_time": time.time(),
        "status": "Starting reconciliation..."
    }

    # Start the reconciliation in a separate thread to prevent webUI stalls
    reconcile_thread = threading.Thread(
        target=_run_reconciliation,
        name="ReconciliationThread",
        daemon=True
    )
    reconcile_thread.start()
    
    logging.info(f"Started reconciliation in background thread {reconcile_thread.name}")
    return

def _run_reconciliation():
    """Does the actual reconciliation work in a separate thread."""
    logging.info("[Reconcile Thread] Starting state reconciliation...")
    needs_cf_update = False
    state_changed_locally = False
    
    # Create a watchdog timer that will force-complete reconciliation if it takes too long
    max_total_time = 180  # 3 minutes absolute maximum
    reconciliation_start = time.time()
    
    def watchdog_timer():
        """Force-completes reconciliation if it's taking too long"""
        elapsed = time.time() - reconciliation_start
        if elapsed > max_total_time and getattr(app, 'reconciliation_info', {}).get('in_progress', False):
            logging.error(f"[Reconcile] WATCHDOG: Reconciliation taking too long ({elapsed:.1f}s)! Forcing completion.")
            app.reconciliation_info["in_progress"] = False
            app.reconciliation_info["progress"] = 100
            app.reconciliation_info["status"] = "Forced completion by watchdog timer"
            app.reconciliation_info["completed_at"] = time.time()
    
    # Start the watchdog timer
    watchdog = threading.Timer(max_total_time + 10, watchdog_timer)
    watchdog.daemon = True
    watchdog.start()
    
    try:
        # First phase: Get running container data
        running_labeled_containers = {}
        try:
            # Update UI status
            app.reconciliation_info["status"] = "Scanning containers..."
            logging.debug("[Reconcile] Starting container scan phase")
            
            try:
                # Use lower batch size for scanning in external mode
                containers = docker_client.containers.list(sparse=False, all=SCAN_ALL_NETWORKS)
                container_count = len(containers)
                logging.debug(f"[Reconcile] Found {container_count} total containers.")
            except Exception as e:
                logging.error(f"[Reconcile] Error listing containers: {e}")
                app.reconciliation_info["status"] = f"Error listing containers: {e}"
                containers = []
                container_count = 0
                
            # Process containers in smaller batches if in external mode to reduce API load
            batch_size = 5 if not USE_EXTERNAL_CLOUDFLARED else 3
            for i in range(0, container_count, batch_size):
                # Check timeout
                if time.time() - reconciliation_start > 60:  # 1 minute max for container scanning
                    logging.warning("[Reconcile] Timeout during container scanning phase. Moving to next phase with partial data.")
                    app.reconciliation_info["status"] = "Partial scan - timeout reached"
                    break
                
                batch = containers[i:i+batch_size]
                logging.debug(f"[Reconcile] Processing container batch {i//batch_size + 1} with {len(batch)} containers")
                app.reconciliation_info["status"] = f"Scanning containers: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                
                # Process each container with individual timeouts
                for c in batch:
                    container_start_time = time.time()
                    try:
                        if time.time() - container_start_time > 5:  # 5 seconds max per container
                            logging.warning(f"[Reconcile] Container {c.id[:12]} processing taking too long, skipping")
                            continue
                            
                        labels = c.labels
                        container_id = c.id
                        container_name = c.name
                        enabled = labels.get(f"{LABEL_PREFIX}.enable", "false").lower() in ["true", "1", "t", "yes"]
                        
                        if not enabled:
                            continue
                            
                        # Process hostname configurations
                        hostname_configs = []
                        
                        # Direct hostname labels
                        hostname = labels.get(f"{LABEL_PREFIX}.hostname")
                        service = labels.get(f"{LABEL_PREFIX}.service")
                        zone_name = labels.get(f"{LABEL_PREFIX}.zonename")
                        no_tls_verify = labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]
                        
                        if hostname and service:
                            if is_valid_hostname(hostname) and is_valid_service(service):
                                hostname_configs.append({
                                    "hostname": hostname,
                                    "service": service,
                                    "zone_name": zone_name,
                                    "no_tls_verify": no_tls_verify
                                })
                        
                        # Process indexed labels with individual timeout
                        index = 0
                        index_start_time = time.time()
                        while time.time() - index_start_time < 3:  # 3 seconds max for all indexed labels
                            prefix = f"{LABEL_PREFIX}.{index}"
                            indexed_hostname = labels.get(f"{prefix}.hostname")
                            if not indexed_hostname:
                                break
                                
                            indexed_service = labels.get(f"{prefix}.service", service)
                            if not indexed_service:
                                index += 1
                                continue
                                
                            indexed_zone_name = labels.get(f"{prefix}.zonename", zone_name)
                            indexed_no_tls_verify = labels.get(f"{prefix}.no_tls_verify", 
                                                              labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false")).lower() in ["true", "1", "t", "yes"]
                            
                            if is_valid_hostname(indexed_hostname) and is_valid_service(indexed_service):
                                hostname_configs.append({
                                    "hostname": indexed_hostname,
                                    "service": indexed_service,
                                    "zone_name": indexed_zone_name,
                                    "no_tls_verify": indexed_no_tls_verify
                                })
                            
                            index += 1
                            
                        # Add to running containers map
                        for config in hostname_configs:
                            hostname = config["hostname"]
                            if hostname in running_labeled_containers:
                                logging.warning(f"[Reconcile] Duplicate hostname '{hostname}' found. Using latest.")
                            
                            running_labeled_containers[hostname] = {
                                "service": config["service"],
                                "container_id": container_id,
                                "container_name": container_name,
                                "zone_name": config["zone_name"],
                                "no_tls_verify": config["no_tls_verify"]
                            }
                            
                    except Exception as e:
                        logging.error(f"[Reconcile] Error processing container {c.id[:12]}: {e}")
                        continue
                
                # Add delay between batches
                if USE_EXTERNAL_CLOUDFLARED and i + batch_size < container_count:
                    time.sleep(0.5)
            
            logging.info(f"[Reconcile] Found {len(running_labeled_containers)} running hostnames with valid DockFlare labels.")
            
        except Exception as e:
            logging.error(f"[Reconcile] Error in container scanning phase: {e}", exc_info=True)
            app.reconciliation_info["status"] = f"Container scan error: {str(e)}"

        # Second phase: State comparison with timeout protection
        hostnames_requiring_dns_check = []
        app.reconciliation_info["status"] = "Comparing state..."
        
        # Use a timeout for acquiring the state lock
        state_lock_timeout = 10  # 10 seconds max to acquire lock
        state_lock_acquired = False
        
        try:
            state_lock_acquired = state_lock.acquire(timeout=state_lock_timeout)
            if not state_lock_acquired:
                logging.error("[Reconcile] Could not acquire state lock after timeout. Continuing with limited functionality.")
                app.reconciliation_info["status"] = "Error: Could not acquire state lock"
            else:
                logging.debug("[Reconcile] Acquired state lock for comparison.")
                
                # Check overall timeout
                if time.time() - reconciliation_start > 120:  # 2 minutes max
                    logging.warning("[Reconcile] Overall timeout reached before completing state comparison.")
                    app.reconciliation_info["status"] = "Timeout reached during state comparison"
                    needs_cf_update = False  # Skip remaining operations
                else:
                    # Process state comparison with timeout protection
                    comparison_start = time.time()
                    comparison_timeout = 30  # 30 seconds max for comparison
                    
                    try:
                        # Your state comparison code with timeout checks
                        now_utc = datetime.now(timezone.utc)
                        managed_hostnames = set(managed_rules.keys())
                        running_hostnames = set(running_labeled_containers.keys())

                        # Process running containers with timeout protection
                        for hostname, running_details in running_labeled_containers.items():
                            # Check timeout periodically
                            if time.time() - comparison_start > comparison_timeout:
                                logging.warning("[Reconcile] State comparison taking too long, stopping early")
                                app.reconciliation_info["status"] = "State comparison timeout - partial results"
                                break
                                
                            # Zone ID lookup with strict timeout
                            target_zone_id = None
                            zone_name = running_details.get("zone_name")
                            
                            if zone_name:
                                logging.debug(f"[Reconcile] Looking up zone ID for {zone_name}")
                                app.reconciliation_info["status"] = f"Looking up zone for {zone_name}"
                                
                                # Use a timeout wrapper for zone ID lookup
                                zone_start = time.time()
                                zone_timeout = 5  # 5 seconds max per zone lookup
                                
                                try:
                                    # First check cache without API call
                                    cached_data = zone_id_cache.get(zone_name)
                                    if cached_data:
                                        zone_id, timestamp = cached_data
                                        target_zone_id = zone_id
                                        logging.debug(f"[Reconcile] Using cached zone ID for {zone_name}: {zone_id}")
                                    else:
                                        # Only make API call if not in cache and within timeout
                                        if time.time() - zone_start < zone_timeout:
                                            target_zone_id = get_zone_id_from_name(zone_name)
                                            logging.debug(f"[Reconcile] Zone lookup for {zone_name} result: {target_zone_id}")
                                except Exception as zone_err:
                                    logging.error(f"[Reconcile] Error in zone lookup for {zone_name}: {zone_err}")
                            
                            if not target_zone_id:
                                target_zone_id = CF_ZONE_ID
                                
                            if not target_zone_id:
                                logging.error(f"[Reconcile] No zone ID for {hostname}, skipping")
                                continue
                                
                            # Update state rules with timeouts
                            if time.time() - comparison_start > comparison_timeout:
                                break
                                
                            # Process rule
                            if hostname in managed_rules:
                                rule = managed_rules[hostname]
                                zone_id_changed = rule.get("zone_id") != target_zone_id

                                if rule.get("status") == "pending_deletion":
                                    logging.info(f"[Reconcile] Reactivating {hostname}")
                                    rule["status"] = "active"
                                    rule["delete_at"] = None
                                    rule["service"] = running_details["service"]
                                    rule["container_id"] = running_details["container_id"]
                                    rule["zone_id"] = target_zone_id
                                    rule["no_tls_verify"] = running_details["no_tls_verify"]
                                    state_changed_locally = True
                                    needs_cf_update = True
                                    hostnames_requiring_dns_check.append((hostname, target_zone_id))
                                    
                                elif rule.get("status") == "active":
                                    container_changed = rule.get("container_id") != running_details["container_id"]
                                    service_changed = rule.get("service") != running_details["service"]
                                    no_tls_verify_changed = rule.get("no_tls_verify") != running_details["no_tls_verify"]
                                    
                                    if container_changed or service_changed or no_tls_verify_changed or zone_id_changed:
                                        if container_changed:
                                            rule["container_id"] = running_details["container_id"]
                                        if service_changed:
                                            rule["service"] = running_details["service"]
                                            needs_cf_update = True
                                        if no_tls_verify_changed:
                                            rule["no_tls_verify"] = running_details["no_tls_verify"]
                                            needs_cf_update = True
                                        if zone_id_changed:
                                            rule["zone_id"] = target_zone_id
                                            hostnames_requiring_dns_check.append((hostname, target_zone_id))
                                            needs_cf_update = True
                                            
                                        state_changed_locally = True
                            else:
                                logging.info(f"[Reconcile] Adding new rule for {hostname}")
                                managed_rules[hostname] = {
                                    "service": running_details["service"],
                                    "container_id": running_details["container_id"],
                                    "status": "active",
                                    "delete_at": None,
                                    "zone_id": target_zone_id,
                                    "no_tls_verify": running_details["no_tls_verify"]
                                }
                                state_changed_locally = True
                                needs_cf_update = True
                                hostnames_requiring_dns_check.append((hostname, target_zone_id))

                        # Mark non-running rules for deletion (with timeout check)
                        if time.time() - comparison_start < comparison_timeout:
                            for hostname in list(managed_hostnames):
                                if hostname not in running_hostnames:
                                    if hostname in managed_rules and managed_rules[hostname].get("status") == "active":
                                        logging.info(f"[Reconcile] Marking {hostname} for deletion")
                                        rule = managed_rules[hostname]
                                        rule["status"] = "pending_deletion"
                                        rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS)
                                        state_changed_locally = True
                        
                        # Save state if changed
                        if state_changed_locally:
                            logging.info("[Reconcile] Saving state changes")
                            app.reconciliation_info["status"] = "Saving state..."
                            save_state()
                            
                    except Exception as state_err:
                        logging.error(f"[Reconcile] Error during state comparison: {state_err}", exc_info=True)
                        app.reconciliation_info["status"] = f"State comparison error: {str(state_err)}"
                        
        except Exception as lock_err:
            logging.error(f"[Reconcile] Error acquiring state lock: {lock_err}", exc_info=True)
            app.reconciliation_info["status"] = f"Error acquiring state lock: {str(lock_err)}"
        finally:
            if state_lock_acquired:
                state_lock.release()
                logging.debug("[Reconcile] Released state lock after comparison")

        # Third phase: DNS operations with aggressive timeouts
        if needs_cf_update and time.time() - reconciliation_start < 150:  # Leave 30s for DNS work
            # Update CF config (external mode skip)
            try:
                app.reconciliation_info["status"] = "Updating configuration..."
                
                if USE_EXTERNAL_CLOUDFLARED:
                    logging.info("[Reconcile] Using external mode, skipping CF config update")
                    config_updated = True
                else:
                    logging.info("[Reconcile] Updating CF config")
                    config_updated = update_cloudflare_config()
            except Exception as cf_err:
                logging.error(f"[Reconcile] Error updating CF config: {cf_err}", exc_info=True)
                config_updated = False
                
            # Process DNS records
            dns_records_total = len(hostnames_requiring_dns_check)
            app.reconciliation_info["total_items"] = dns_records_total
            
            if dns_records_total > 0:
                logging.info(f"[Reconcile] Processing {dns_records_total} DNS records")
                processed_count = 0
                
                # Group by zone with timeout protection
                try:
                    zone_grouped = {}
                    for hostname, zone_id in hostnames_requiring_dns_check:
                        if zone_id not in zone_grouped:
                            zone_grouped[zone_id] = []
                        zone_grouped[zone_id].append(hostname)
                        
                    app.reconciliation_info["status"] = f"Processing DNS across {len(zone_grouped)} zones..."
                    
                    # Process each zone with smaller batches for external mode
                    batch_size = 1 if USE_EXTERNAL_CLOUDFLARED else 2
                    
                    for zone_id, hostnames in zone_grouped.items():
                        logging.info(f"[Reconcile] Processing zone {zone_id}: {len(hostnames)} hostnames")
                        
                        # Process in small batches with timeouts
                        for i in range(0, len(hostnames), batch_size):
                            # Overall timeout check
                            if time.time() - reconciliation_start > 170:  # Leave 10s for cleanup
                                logging.warning("[Reconcile] Timeout reached during DNS operations")
                                app.reconciliation_info["status"] = f"DNS timeout - processed {processed_count}/{dns_records_total}"
                                break
                                
                            batch = hostnames[i:i+batch_size]
                            app.reconciliation_info["status"] = f"DNS batch {i//batch_size + 1} in zone {zone_id}"
                            
                            # Process each hostname with individual timeout
                            for hostname in batch:
                                dns_start = time.time()
                                dns_timeout = 10  # 10s max per hostname
                                
                                try:
                                    app.reconciliation_info["status"] = f"Processing DNS for {hostname}"
                                    
                                    # Check rule still exists
                                    rule = None
                                    try:
                                        state_lock_acq = state_lock.acquire(timeout=5)
                                        if state_lock_acq:
                                            try:
                                                if hostname in managed_rules:
                                                    rule = managed_rules[hostname]
                                            finally:
                                                state_lock.release()
                                        else:
                                            logging.warning(f"[Reconcile] Could not acquire lock for DNS check of {hostname}")
                                    except Exception as lock_err:
                                        logging.error(f"[Reconcile] Lock error for DNS: {lock_err}")
                                    
                                    if rule and tunnel_state.get("id"):
                                        # Timeout wrapper for DNS operation
                                        try:
                                            if time.time() - dns_start > dns_timeout:
                                                logging.warning(f"[Reconcile] Timeout before DNS operation for {hostname}")
                                            else:
                                                dns_record_id = create_cloudflare_dns_record(zone_id, hostname, tunnel_state["id"])
                                                if dns_record_id == "semaphore_timeout":
                                                    logging.warning(f"[Reconcile] DNS semaphore timeout for {hostname}")
                                                    app.reconciliation_info["status"] = f"DNS timeout for {hostname}"
                                                elif dns_record_id:
                                                    logging.info(f"[Reconcile] DNS successful for {hostname}")
                                                else:
                                                    logging.error(f"[Reconcile] DNS failed for {hostname}")
                                        except Exception as dns_err:
                                            logging.error(f"[Reconcile] DNS error for {hostname}: {dns_err}")
                                    else:
                                        logging.warning(f"[Reconcile] Skipping DNS for {hostname}: rule or tunnel ID missing")
                                    
                                    # Always update progress
                                    processed_count += 1
                                    app.reconciliation_info["processed_items"] = processed_count
                                    app.reconciliation_info["progress"] = min(100, int((processed_count / dns_records_total) * 100))
                                    
                                    # Add small delay in external mode
                                    if USE_EXTERNAL_CLOUDFLARED:
                                        time.sleep(1)
                                        
                                except Exception as e:
                                    logging.error(f"[Reconcile] Error processing DNS for {hostname}: {e}")
                                    processed_count += 1  # Count as processed
                                    app.reconciliation_info["processed_items"] = processed_count
                                    app.reconciliation_info["progress"] = min(100, int((processed_count / dns_records_total) * 100))
                            
                            # Delay between batches in external mode
                            if USE_EXTERNAL_CLOUDFLARED and i + batch_size < len(hostnames):
                                time.sleep(2)
                except Exception as zone_err:
                    logging.error(f"[Reconcile] Error in zone processing: {zone_err}", exc_info=True)
            else:
                logging.info("[Reconcile] No DNS records to process")
                app.reconciliation_info["progress"] = 100
        else:
            if not needs_cf_update:
                logging.info("[Reconcile] No config changes needed")
            else:
                logging.warning("[Reconcile] Timeout reached before DNS operations")
            app.reconciliation_info["progress"] = 100
            
    except Exception as e:
        logging.error(f"[Reconcile] Unhandled error: {e}", exc_info=True)
        app.reconciliation_info["status"] = f"Error: {str(e)}"
    
    finally:
        # Always mark as complete, even on error
        if not hasattr(app, 'reconciliation_info'):
            app.reconciliation_info = {}
        
        app.reconciliation_info["in_progress"] = False
        app.reconciliation_info["progress"] = 100
        app.reconciliation_info["status"] = app.reconciliation_info.get("status", "Completed")
        
        if "start_time" not in app.reconciliation_info:
            app.reconciliation_info["start_time"] = reconciliation_start
            
        app.reconciliation_info["completed_at"] = time.time()
        duration = app.reconciliation_info["completed_at"] - reconciliation_start
        
        # Cancel the watchdog timer
        watchdog.cancel()
        
        logging.info(f"Reconciliation complete. Duration: {duration:.2f} seconds")

def get_cloudflared_container():
    """Gets the cloudflared agent container object."""
    if not docker_client:
        logging.warning("Docker client unavailable.")
        return None
        
    # Skip container checks in external mode
    if USE_EXTERNAL_CLOUDFLARED:
        return None
        
    # Ensure we have a container name to check
    if not CLOUDFLARED_CONTAINER_NAME:
        logging.debug("CLOUDFLARED_CONTAINER_NAME is None or empty, skipping container check.")
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

def update_cloudflare_config():
    """Updates the Cloudflare tunnel ingress configuration if needed, preserving external rules and existing order."""
    if not tunnel_state.get("id"):
        logging.warning("Cannot update CF config, tunnel ID missing.")
        return False

    final_ingress_rules = None
    needs_api_update = False

    with state_lock:
        logging.info("Checking for Cloudflare tunnel config updates...")
        catch_all_rule = {"service": "http_status:404"}
        wildcard_rules = []  # For storing wildcard (*) rules
        
        # Fetch current config first to maintain order
        logging.debug("Fetching current CF config for comparison...")
        current_config = get_current_cf_config()
        if current_config is None:
            logging.error("Failed to fetch current CF config, aborting update check.")
            return False
            
        current_cf_ingress = current_config.get("ingress", [])
        current_cf_all_hostnames = {r.get("hostname") for r in current_cf_ingress if r.get("hostname")}
        current_managed_hostnames = {hostname for hostname in managed_rules}
        
        # Identify external rules (rules that aren't managed by this instance)
        external_rules = [
            r for r in current_cf_ingress 
            if r.get("hostname") and r.get("hostname") not in current_managed_hostnames
            and r.get("service") != catch_all_rule.get("service")
        ]
        
        # Identify wildcard rules (containing '*') and store them separately
        for rule in external_rules[:]:
            hostname = rule.get("hostname", "")
            if hostname and '*' in hostname:
                wildcard_rules.append(rule)
                external_rules.remove(rule)
                logging.debug(f"Identified wildcard rule: {hostname}")
        
        # Keep track of the catch-all rule if it exists in the current config
        existing_catch_all = next((r for r in current_cf_ingress if r.get("service") == catch_all_rule["service"]), None)
        
        # Create desired ingress rules from current managed rules
        desired_ingress_rules = []
        
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
        
        # For comparison purposes
        current_cf_managed_ingress = [
            r for r in current_cf_ingress 
            if r.get("hostname") in current_managed_hostnames
        ]

        def rule_to_canonical(rule):
            items = sorted([(k, v) for k, v in rule.items() if k in ["hostname", "service"]])
            return tuple(items)

        try:
            current_cf_set = {rule_to_canonical(r) for r in current_cf_managed_ingress if r.get("hostname") and r.get("service")}
            desired_set = {rule_to_canonical(r) for r in desired_ingress_rules if r.get("hostname") and r.get("service")}
        except Exception as e:
            logging.error(f"Error creating canonical rule sets for comparison: {e}", exc_info=True)
            return False

        # Determine if update is needed
        if current_cf_set == desired_set and len(external_rules) == 0 and len(wildcard_rules) == 0:
            logging.info("No changes detected in CF tunnel config. Skipping API update.")
            needs_api_update = False
        else:
            logging.info("Change detected. Rules need to be updated.")
            
            # Combine in the order: normal host rules first, then wildcard rules, then catch-all
            # Normal external rules
            if len(external_rules) > 0:
                logging.info(f"Preserving {len(external_rules)} external rules found in the current configuration")
            
            # Our standard hostname rules
            final_ingress_rules = desired_ingress_rules + external_rules
            
            # Then add wildcard rules before the catch-all rule
            if len(wildcard_rules) > 0:
                logging.info(f"Preserving {len(wildcard_rules)} wildcard rules at the end (before catch-all)")
                final_ingress_rules.extend(wildcard_rules)
            
            # Always add the catch-all rule at the very end
            final_ingress_rules.append(catch_all_rule if existing_catch_all is None else existing_catch_all)
            
            needs_api_update = True

    # Proceed with API update if needed
    if needs_api_update and final_ingress_rules is not None:
        logging.info(f"Updating Cloudflare tunnel config with {len(final_ingress_rules) - 1} rules (+1 catch-all)")
        logging.debug(f"Rules to update: {[r.get('hostname') for r in final_ingress_rules if r.get('hostname')]}")
        
        endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        
        # Build the complete config object
        config = {
            "config": {
                "ingress": final_ingress_rules,
                "originRequest": {"connectTimeout": 30, "noTLSVerify": False},
                "warp-routing": {"enabled": False}
            }
        }
        
        try:
            # Use the retry mechanism for Cloudflare updates
            for attempt in range(MAX_CF_UPDATE_RETRIES):
                try:
                    cf_api_request("PUT", endpoint, json_data=config)
                    logging.info(f"Successfully updated Cloudflare tunnel configuration (attempt {attempt + 1})")
                    if tunnel_state.get("error") and "config" in tunnel_state.get("error", "").lower():
                        tunnel_state["error"] = None  # Clear any previous update errors
                    return True
                except requests.exceptions.RequestException as e:
                    if attempt < MAX_CF_UPDATE_RETRIES - 1:
                        retry_delay = CF_UPDATE_RETRY_DELAY * (CF_UPDATE_BACKOFF_FACTOR ** attempt)
                        logging.warning(f"CF config update failed (attempt {attempt + 1}/{MAX_CF_UPDATE_RETRIES}), retrying in {retry_delay}s: {e}")
                        time.sleep(retry_delay)
                    else:
                        raise
            
            # We shouldn't normally reach here due to the exception in the last iteration
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"All {MAX_CF_UPDATE_RETRIES} attempts to update CF tunnel config failed: {e}", exc_info=True)
            tunnel_state["error"] = f"Failed to update tunnel configuration after {MAX_CF_UPDATE_RETRIES} attempts"
            return False
        except Exception as e:
            logging.error(f"Unexpected error updating CF tunnel config: {e}", exc_info=True)
            tunnel_state["error"] = f"Unexpected error updating tunnel configuration: {e}"
            return False
    
    # If we reached here, either there were no changes or the update was successful
    return True

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PREFERRED_URL_SCHEME'] = 'https'  # Default for url_for, but client-side JS will fix

@app.before_request
def detect_protocol():
    """Detect the protocol to use for internal redirects."""
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    app.config['PREFERRED_URL_SCHEME'] = 'https' if forwarded_proto == 'https' or request.is_secure else 'http'

@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers that work in both HTTP and HTTPS environments."""
    # Basic security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Get protocol information from request
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    is_https = forwarded_proto == 'https' or request.is_secure
    
    # Set extremely permissive CSP that works in both environments
    csp = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
        "script-src * 'unsafe-inline' 'unsafe-eval'; "
        "style-src * 'unsafe-inline'; "
        "img-src * data: blob:; "
        "font-src * data:; "
        "connect-src *; "
        "frame-src *; "
    )
    
    # Only add upgrade-insecure-requests when using HTTPS
    if is_https:
        csp += "upgrade-insecure-requests; "
    
    response.headers['Content-Security-Policy'] = csp
    
    # Additional headers for reverse proxy and protocol awareness
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Only include HSTS for HTTPS
    if is_https:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # Cross-origin headers for API compatibility
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
    
    return response

def get_display_token(token):
    """Returns a truncated token for display."""
    if not token:
        return "Not available"
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token retrieved (short)"

@app.context_processor
def inject_protocol():
    """Inject protocol info into all templates with more reliable detection."""
    # First check X-Forwarded-Proto header (set by reverse proxies)
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    
    # Then check if request itself is secure
    is_https = forwarded_proto == 'https' or request.is_secure
    
    # Build URL prefix for template use
    base_url = f"{'https' if is_https else 'http'}://{request.host}"
    
    # Include the request scheme for debugging
    request_scheme = request.scheme
    
    return {
        'protocol': 'https' if is_https else 'http',
        'is_https': is_https,
        'base_url': base_url,
        'host': request.host,
        'request_scheme': request_scheme
    }

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
        
        # Add initialization state for UI display
        initialization_status = {
            "complete": tunnel_state.get("id") is not None,
            "in_progress": template_tunnel_state.get("status_message") == "Initializing (in progress)..."
        }

    display_token = get_display_token(template_tunnel_state.get("token"))
    docker_available = docker_client is not None
    external_cloudflared = USE_EXTERNAL_CLOUDFLARED
    external_tunnel_id = EXTERNAL_TUNNEL_ID

    return render_template('status_page.html',
                        tunnel_state=template_tunnel_state,
                        agent_state=template_agent_state,
                        initialization=initialization_status,
                        display_token=display_token,
                        cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                        docker_available=docker_available,
                        external_cloudflared=external_cloudflared,
                        external_tunnel_id=external_tunnel_id,
                        rules=rules_for_template)

@app.route('/ping')
def ping():
    """Simple ping endpoint to check server availability."""
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time()),
        "version": "1.0", 
        "protocol": request.environ.get('wsgi.url_scheme', 'unknown')
    })

@app.route('/debug')
def debug_info():
    """Return debugging information about the environment."""
    try:
        headers = {k: v for k, v in request.headers.items()}
        
        return jsonify({
            "request": {
                "scheme": request.scheme,
                "is_secure": request.is_secure,
                "host": request.host,
                "path": request.path,
                "url": request.url,
                "headers": headers
            },
            "environment": {
                "wsgi.url_scheme": request.environ.get('wsgi.url_scheme'),
                "HTTP_X_FORWARDED_PROTO": request.environ.get('HTTP_X_FORWARDED_PROTO'),
                "HTTP_X_FORWARDED_HOST": request.environ.get('HTTP_X_FORWARDED_HOST'),
                "SERVER_NAME": request.environ.get('SERVER_NAME'),
                "SERVER_PORT": request.environ.get('SERVER_PORT')
            },
            "timestamp": int(time.time())
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@app.route('/reconciliation-status')
def reconciliation_status():
    """Returns the current reconciliation status."""
    reconciliation_info = getattr(app, 'reconciliation_info', {})
    return jsonify({
        "in_progress": reconciliation_info.get("in_progress", False),
        "progress": reconciliation_info.get("progress", 0),
        "total_items": reconciliation_info.get("total_items", 0),
        "processed_items": reconciliation_info.get("processed_items", 0),
        "status": reconciliation_info.get("status", "")
    })

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

@app.route('/force_delete_rule/<hostname>', methods=['POST', 'GET'])
def force_delete_rule(hostname):
    """Force delete a rule with improved method handling."""
    # HTTP method validation with better error handling
    if request.method != 'POST':
        # Return a more helpful error for GET requests
        flash("Delete operations require a POST request. If you're seeing this message, there may be an issue with your browser's form submission.", "error")
        return redirect(url_for('status_page'))

    logging.info(f"UI request: Force delete rule for hostname: {hostname}")
    rule_removed_from_state = False
    dns_delete_success = False
    zone_id_for_delete = None

    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details:
            zone_id_for_delete = rule_details.get("zone_id")
            logging.info(f"Found rule for {hostname} with zone ID: {zone_id_for_delete}")
        else:
            logging.warning(f"Rule {hostname} not found in state during force delete. Attempting DNS delete in default zone ID ({CF_ZONE_ID}) if available.")
            zone_id_for_delete = CF_ZONE_ID

    # Handle both external and internal modes
    tunnel_id = tunnel_state.get("id") or EXTERNAL_TUNNEL_ID
    
    if zone_id_for_delete and tunnel_id:
        logging.info(f"Attempting immediate DNS record deletion for force-deleted rule: {hostname} in zone {zone_id_for_delete} using tunnel {tunnel_id}")
        dns_delete_success = delete_cloudflare_dns_record(zone_id_for_delete, hostname, tunnel_id)
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

    # Update Cloudflare tunnel config if not in external mode
    if rule_removed_from_state and not USE_EXTERNAL_CLOUDFLARED:
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
    elif rule_removed_from_state and USE_EXTERNAL_CLOUDFLARED:
        # For external mode, we only handle DNS and local state
        status_msg = f"Successfully removed rule for {hostname} from local state."
        if dns_delete_success:
            status_msg += " DNS record deleted."
        else:
            status_msg += " DNS deletion failed or skipped."
        logging.info(status_msg)
        cloudflared_agent_state["last_action_status"] = status_msg

    time.sleep(1)
    return redirect(url_for('status_page'))

@app.route('/stream-logs')
def stream_logs():
    """Streams log messages using Server-Sent Events with proper WSGI compatibility."""
    client_id = f"client-{random.randint(1000, 9999)}"
    logging.info(f"Log stream client {client_id} connected.")
    
    def event_stream():
        """Generate events without accessing Flask request context."""
        try:
            # Send initial connection message
            yield f"data: --- Log stream connected (client {client_id}) ---\n\n"
            yield f"data: heartbeat\n\n"
            
            # Track last heartbeat time
            last_heartbeat = time.time()
            heartbeat_interval = 2  # Send heartbeats every 2 seconds
            
            # Loop continuously to stream logs
            while True:
                try:
                    # Check if we need to send a heartbeat
                    current_time = time.time()
                    if current_time - last_heartbeat > heartbeat_interval:
                        yield f"data: heartbeat\n\n"
                        last_heartbeat = current_time
                        continue
                    
                    # Try to get a log entry with a short timeout
                    log_entry = log_queue.get(timeout=0.25)
                    yield f"data: {log_entry}\n\n"
                except queue.Empty:
                    # No log entries, send a keepalive comment
                    yield f": keepalive\n\n"
                    time.sleep(0.1)
        
        except GeneratorExit:
            logging.info(f"Log stream client {client_id} disconnected.")
        except Exception as e:
            logging.error(f"Error in log stream for {client_id}: {e}", exc_info=True)
        finally:
            logging.info(f"Log stream for client {client_id} ended.")
    
    # Create response with proper headers that are WSGI-compatible
    response = Response(event_stream(), mimetype='text/event-stream')
    
    # Set cache control headers that are WSGI-compatible
    # Note: 'Connection: keep-alive' is removed as it's a hop-by-hop header not allowed in WSGI
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'
    
    # CORS headers are fine (they're end-to-end)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    
    return response

@app.route('/cloudflare-ping')
def cloudflare_ping():
    """Specialized ping endpoint to diagnose Cloudflare tunnel connectivity."""
    try:
        # Extract Cloudflare-specific headers
        cf_headers = {k: v for k, v in request.headers.items() if k.lower().startswith('cf-')}
        cf_visitor = request.headers.get('Cf-Visitor', '')
        
        # Parse Cf-Visitor JSON if present
        visitor_data = {}
        if cf_visitor:
            try:
                visitor_data = json.loads(cf_visitor)
            except:
                visitor_data = {"parse_error": "Invalid JSON in Cf-Visitor header"}
                
        # Get connection information
        connecting_ip = request.headers.get('Cf-Connecting-Ip') or request.remote_addr
        
        return jsonify({
            "status": "ok",
            "timestamp": int(time.time()),
            "cloudflare": {
                "connecting_ip": connecting_ip,
                "visitor": visitor_data,
                "ray": request.headers.get('Cf-Ray'),
                "country": request.headers.get('Cf-Ipcountry'),
                "headers": cf_headers
            },
            "request": {
                "host": request.host,
                "path": request.path,
                "scheme": request.scheme
            },
            "server": {
                "wsgi_url_scheme": request.environ.get('wsgi.url_scheme'),
                "server_protocol": request.environ.get('SERVER_PROTOCOL')
            }
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "status": "error",
            "timestamp": int(time.time())
        }), 500

def run_background_tasks():
    """Starts the Docker event listener and cleanup threads."""
    threads = []
    if not docker_client:
        logging.warning("Docker client unavailable. Background tasks (Event Listener, Cleanup) cannot start.")
        return threads 
        
    # Handle both modes appropriately - external mode only needs tunnel ID
    if USE_EXTERNAL_CLOUDFLARED:
        if not tunnel_state.get("id"):
            logging.warning("External tunnel ID not available. Background tasks cannot start.")
            return threads
    else:
        # Regular mode needs both ID and token
        if not tunnel_state.get("id") or not tunnel_state.get("token"):
            logging.warning("Tunnel not fully initialized (missing ID or token). Background tasks cannot start.")
            return threads 

    logging.info("Starting background threads (Docker Listener, Cleanup Task)...")
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

    # Function to run initialization in background
    def initialization_process():
        # Add the global declaration at the top of the function
        global background_threads
        
        logging.info("Running initialization process in background thread")
        if not docker_client:
            logging.error("Docker client unavailable for initialization. Skipping initialization tasks.")
            return
            
        initialize_tunnel()
        logging.info(f"Tunnel initialization complete. Status: {tunnel_state.get('status_message')}")
        
        # Handle external tunnel mode differently than regular mode
        if USE_EXTERNAL_CLOUDFLARED and tunnel_state.get("id"):
            logging.info("External tunnel initialized. Proceeding with initial reconciliation.")
            
            # Run initial container scan directly, not through reconcile_state()
            try:
                logging.info("Running initial direct container scan (non-threaded)...")
                
                # Create a more conservative initial scanning approach
                max_reconciliation_time = 90  # 90 seconds max for initial scan
                reconciliation_start = time.time()
                
                # Set reconciliation status
                app.reconciliation_info = {
                    "in_progress": True,
                    "progress": 0,
                    "total_items": 0,
                    "processed_items": 0,
                    "start_time": time.time(),
                    "status": "Starting initial container scan..."
                }
                
                # Scan in much smaller batches with longer delays for initial setup
                try:
                    containers = docker_client.containers.list(all=SCAN_ALL_NETWORKS)
                    container_count = len(containers)
                    logging.info(f"[Init] Found {container_count} total containers to scan")
                    
                    # Process in small batches with significant delays
                    batch_size = 2
                    processed = 0
                    
                    for i in range(0, container_count, batch_size):
                        if time.time() - reconciliation_start > max_reconciliation_time:
                            logging.warning("[Init] Initial container scan timeout")
                            break
                            
                        batch = containers[i:i+batch_size]
                        
                        # Update status info
                        app.reconciliation_info["status"] = f"Initial scan: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                        app.reconciliation_info["total_items"] = container_count
                        processed += len(batch)
                        app.reconciliation_info["processed_items"] = processed
                        app.reconciliation_info["progress"] = min(100, int((processed / container_count) * 100))
                        
                        for container in batch:
                            # Use process_container_start which handles Zone ID safely
                            process_container_start(container)
                            
                        # Bigger delay between batches for initial setup
                        time.sleep(1.0)
                        
                except Exception as e:
                    logging.error(f"Error during initial container processing: {e}", exc_info=True)
                
                # Set initial reconciliation as complete
                app.reconciliation_info["in_progress"] = False
                app.reconciliation_info["progress"] = 100
                app.reconciliation_info["status"] = "Initial container scan complete"
                app.reconciliation_info["completed_at"] = time.time()
                
                # Now schedule a full background reconciliation for later
                logging.info("Initial container scan complete - scheduling full background reconciliation")
                threading.Timer(15, reconcile_state).start()
                
            except Exception as e:
                logging.error(f"Error during initial container scan: {e}", exc_info=True)
            
            logging.info("Initial state reconciliation complete.")
            # Start event listener and cleanup threads
            background_threads.extend(run_background_tasks())
            
        elif not USE_EXTERNAL_CLOUDFLARED and tunnel_state.get("id") and tunnel_state.get("token"):
            logging.info("Tunnel initialized with ID and Token. Proceeding with initial reconciliation & agent checks.")
            
            # Run direct container scan for managed mode too
            try:
                logging.info("Running initial direct container scan (non-threaded)...")
                
                # Create a more conservative initial scanning approach 
                max_reconciliation_time = 90  # 90 seconds max for initial scan
                reconciliation_start = time.time()
                
                # Set reconciliation status
                app.reconciliation_info = {
                    "in_progress": True,
                    "progress": 0,
                    "total_items": 0,
                    "processed_items": 0,
                    "start_time": time.time(),
                    "status": "Starting initial container scan..."
                }
                
                # Process containers directly
                try:
                    containers = docker_client.containers.list(all=SCAN_ALL_NETWORKS)
                    container_count = len(containers)
                    logging.info(f"[Init] Found {container_count} total containers to scan")
                    
                    # Use larger batch size for managed mode
                    batch_size = 3
                    processed = 0
                    
                    for i in range(0, container_count, batch_size):
                        if time.time() - reconciliation_start > max_reconciliation_time:
                            logging.warning("[Init] Initial container scan timeout")
                            break
                            
                        batch = containers[i:i+batch_size]
                        
                        # Update status info
                        app.reconciliation_info["status"] = f"Initial scan: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                        app.reconciliation_info["total_items"] = container_count
                        processed += len(batch)
                        app.reconciliation_info["processed_items"] = processed
                        app.reconciliation_info["progress"] = min(100, int((processed / container_count) * 100))
                        
                        for container in batch:
                            # Process each container
                            process_container_start(container)
                            
                        # Small delay between batches
                        time.sleep(0.5)
                        
                except Exception as e:
                    logging.error(f"Error during initial container processing: {e}", exc_info=True)
                
                # Set initial reconciliation as complete
                app.reconciliation_info["in_progress"] = False
                app.reconciliation_info["progress"] = 100
                app.reconciliation_info["status"] = "Initial container scan complete"
                app.reconciliation_info["completed_at"] = time.time()
                
                # Schedule full background reconciliation for later
                logging.info("Initial direct scan complete - scheduling full background reconciliation")
                threading.Timer(10, reconcile_state).start()
                
            except Exception as e:
                logging.error(f"Error during initial container scan: {e}", exc_info=True)
            
            logging.info("Initial state reconciliation complete.")
    
            logging.info("Checking cloudflared agent container status...")
            update_cloudflared_container_status()
            if cloudflared_agent_state.get("container_status") != 'running':
                logging.info("Agent container not running, attempting auto-start...")
                start_cloudflared_container()
            else:
                logging.info(f"Agent container '{CLOUDFLARED_CONTAINER_NAME}' is already running.")
            
            # Start event listener and cleanup threads
            background_threads.extend(run_background_tasks())
            
        else:
            logging.warning("Tunnel not fully initialized. Skipping reconciliation, agent start, and event/cleanup tasks.")
            if not tunnel_state.get("error"):
                tunnel_state["status_message"] = "Tunnel setup incomplete (missing ID/Token)."

    # Set initial UI states for immediate web UI display
    if not docker_client:
        logging.error("Docker client unavailable at startup. Dockflare will run with limited functionality.")
        tunnel_state["status_message"] = "Error: Docker client unavailable."
        tunnel_state["error"] = "Failed to connect to Docker daemon."
        cloudflared_agent_state["container_status"] = "docker_unavailable"
        logging.warning("Flagging initialization limitations due to Docker connection failure.")
    else:
        logging.info("Docker client available. Setting up initial UI states...")
        # Set initial UI state while initialization happens in background
        tunnel_state["status_message"] = "Initializing (in progress)..."
        cloudflared_agent_state["container_status"] = "initializing"
        
        # Start agent status updater thread
        logging.info("Starting periodic agent status updater thread...")
        agent_status_thread = threading.Thread(target=periodic_agent_status_updater, name="AgentStatusUpdater", daemon=True)
        agent_status_thread.start()
        
        # Start the initialization thread
        init_thread = threading.Thread(
            target=initialization_process,
            name="InitializationProcess",
            daemon=True
        )
        init_thread.start()

    # Start web server immediately
    logging.info("Starting Flask web server...")
    flask_thread = None
    try:
        from waitress import serve
        flask_thread = threading.Thread(
            target=serve,
            args=(app,),
            kwargs={'host': '0.0.0.0', 'port': 5000},
            daemon=True,
            name="FlaskWaitressServer"
        )
        flask_thread.start()
        logging.info("Flask server started using waitress on 0.0.0.0:5000.")
        
        # Main monitoring loop
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