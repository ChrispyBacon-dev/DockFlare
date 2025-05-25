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
# reading upon best practices imports by Python's official style guide, PEP 8, in alphabetical order by group of standard lib. imports than thirdparty imports
# Standard library imports
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
import queue
import random
import re
import sys
import threading
import time
from urllib.parse import urlparse, urlunparse
# third-party imports
import docker
from docker.errors import NotFound, APIError
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, redirect, url_for, request, Response, stream_with_context
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

USE_EXTERNAL_CLOUDFLARED = os.getenv('USE_EXTERNAL_CLOUDFLARED', 'false').lower() in ['true', '1', 't', 'yes']
EXTERNAL_TUNNEL_ID = os.getenv('EXTERNAL_TUNNEL_ID')
SCAN_ALL_NETWORKS = os.getenv('SCAN_ALL_NETWORKS', 'false').lower() in ['true', '1', 't', 'yes']
TUNNEL_DNS_SCAN_ZONE_NAMES_STR = os.getenv('TUNNEL_DNS_SCAN_ZONE_NAMES', '')
TUNNEL_DNS_SCAN_ZONE_NAMES = [name.strip() for name in TUNNEL_DNS_SCAN_ZONE_NAMES_STR.split(',') if name.strip()]
TUNNEL_NAME = os.getenv("TUNNEL_NAME", "dockflared-tunnel")
CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net') if not USE_EXTERNAL_CLOUDFLARED else None
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}") if not USE_EXTERNAL_CLOUDFLARED else None
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"
LABEL_PREFIX = os.getenv('LABEL_PREFIX', 'cloudflare.tunnel')
GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 28800))
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 300))
AGENT_STATUS_UPDATE_INTERVAL_SECONDS = int(os.getenv('AGENT_STATUS_UPDATE_INTERVAL_SECONDS', 10))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')
MAX_LOG_QUEUE_SIZE = 200
MAX_CONCURRENT_DNS_OPS = int(os.getenv('MAX_CONCURRENT_DNS_OPS', 3))
RECONCILIATION_BATCH_SIZE = int(os.getenv('RECONCILIATION_BATCH_SIZE', 3))
dns_semaphore = threading.Semaphore(MAX_CONCURRENT_DNS_OPS)
required_vars = ["CF_API_TOKEN", "CF_ACCOUNT_ID"]
missing_vars = [var for var in required_vars if not globals().get(var)]
_cached_account_email = None
_cached_account_email_timestamp = 0
_ACCOUNT_EMAIL_CACHE_TTL = 3600 

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
            
             
             rule.setdefault("access_app_id", None)
             rule.setdefault("access_policy_type", None)
             rule.setdefault("access_app_config_hash", None)
             rule.setdefault("access_policy_ui_override", False)
             rule.setdefault("source", "docker") 

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
        
        rule_copy.setdefault("access_app_id", None)
        rule_copy.setdefault("access_policy_type", None)
        rule_copy.setdefault("access_app_config_hash", None)
        rule_copy.setdefault("access_policy_ui_override", False)
        rule_copy.setdefault("source", "docker")
            
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
    cache_ttl = 86400  
    current_time = time.time()
    with state_lock:
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
zone_details_by_id_cache = {} 

def get_zone_details_by_id(zone_id):
    global zone_details_by_id_cache
    if not zone_id:
        logging.warning("get_zone_details_by_id called with empty zone_id.")
        return None

    with state_lock: 
        if zone_id in zone_details_by_id_cache:          
            logging.debug(f"Zone details for ID '{zone_id}' found in cache.")
            return zone_details_by_id_cache[zone_id]

    logging.info(f"Zone details for ID '{zone_id}' not in cache. Querying Cloudflare API...")
    endpoint = f"/zones/{zone_id}"

    try:
        response_data = cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            zone_data = response_data.get("result")
            if zone_data and isinstance(zone_data, dict) and zone_data.get("name"):
                logging.info(f"Found zone details for ID '{zone_id}': Name '{zone_data['name']}'")
                with state_lock: 
                    zone_details_by_id_cache[zone_id] = zone_data 
                return zone_data
            else:
                logging.error(f"API returned success for zone ID '{zone_id}' but result is missing or malformed: {zone_data}")
                return None
        else:
            logging.error(f"API call failed or returned success=false for zone ID '{zone_id}': {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error looking up zone ID '{zone_id}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error looking up zone ID '{zone_id}': {e}", exc_info=True)
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
def _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    payload = {
        "name": name,
        "domain": hostname,
        "type": "self_hosted",
        "session_duration": session_duration,
        "app_launcher_visible": app_launcher_visible,
        "self_hosted_domains": self_hosted_domains,
        "allowed_idps": allowed_idps if allowed_idps else [],
        "auto_redirect_to_identity": auto_redirect_to_identity,
        "policies": access_policies
    }
    
    if allowed_idps is None:
        del payload["allowed_idps"]
    return payload

def check_for_tld_access_policy(zone_name):
    if not zone_name:
        logging.warning("check_for_tld_access_policy called with no zone_name.")
        return False
    
    tld_hostname = f"*.{zone_name}"
    logging.info(f"Checking for existing Access Policy for wildcard TLD: {tld_hostname}")
    
    try:

        existing_app = find_cloudflare_access_application_by_hostname(tld_hostname)
        if existing_app and existing_app.get("id"):
            logging.info(f"Found existing Access Application ID '{existing_app.get('id')}' for TLD '{tld_hostname}'.")
            return True
        else:
            logging.info(f"No specific Access Application found for TLD '{tld_hostname}'.")
            return False
    except Exception as e:
        logging.error(f"Error while checking for TLD access policy for '{tld_hostname}': {e}", exc_info=True)
        return False

def get_cloudflare_account_email():
    global _cached_account_email, _cached_account_email_timestamp
    
    current_time = time.time()
    if _cached_account_email and (current_time - _cached_account_email_timestamp < _ACCOUNT_EMAIL_CACHE_TTL):
        logging.debug(f"Returning cached Cloudflare account email: {_cached_account_email}")
        return _cached_account_email

    logging.info("Fetching Cloudflare account email from API.")
    try:
        response_data = cf_api_request("GET", "/user") 
        if response_data and response_data.get("success"):
            email = response_data.get("result", {}).get("email")
            if email:
                logging.info(f"Successfully fetched Cloudflare account email: {email}")
                _cached_account_email = email
                _cached_account_email_timestamp = current_time
                return email
            else:
                logging.warning("Cloudflare account email not found in API response.")
                return None
        else:
            logging.warning(f"Failed to fetch Cloudflare account email, API call unsuccessful or no success flag. Response: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching Cloudflare account email: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching Cloudflare account email: {e}", exc_info=True)
        return None
        
def find_cloudflare_access_application_by_hostname(hostname):
    logging.info(f"Finding Cloudflare Access Application for hostname '{hostname}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/access/apps"
    try:
        response_data = cf_api_request("GET", endpoint, params={"domain": hostname})
        apps = response_data.get("result", [])
        if apps and isinstance(apps, list):
            for app in apps:
                if app.get("domain") == hostname:
                    logging.info(f"Found Access Application ID '{app.get('id')}' for hostname '{hostname}'")
                    return app
            logging.info(f"No exact match Access Application found for hostname '{hostname}' via direct domain query.")
        
        logging.info(f"Falling back to listing all Access Applications to find '{hostname}'")
        all_apps_response = cf_api_request("GET", endpoint) 
        all_apps = all_apps_response.get("result", [])
        if all_apps and isinstance(all_apps, list):
            for app in all_apps:
                if app.get("domain") == hostname:
                    logging.info(f"Found Access Application ID '{app.get('id')}' for hostname '{hostname}' via full list scan.")
                    return app

                if hostname in app.get("self_hosted_domains", []):
                    logging.info(f"Found Access Application ID '{app.get('id')}' for hostname '{hostname}' (in self_hosted_domains) via full list scan.")
                    return app

        logging.info(f"Access Application for hostname '{hostname}' not found after extensive search.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding Cloudflare Access Application for '{hostname}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error finding Cloudflare Access Application for '{hostname}': {e}", exc_info=True)
        return None

def create_cloudflare_access_application(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    logging.info(f"Creating Cloudflare Access Application for hostname '{hostname}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/access/apps"
    payload = _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps, auto_redirect_to_identity)
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        app_data = response_data.get("result")
        if app_data and app_data.get("id"):
            logging.info(f"Successfully created Access Application '{app_data.get('id')}' for '{hostname}'")
            return app_data
        else:
            logging.error(f"Access Application creation for '{hostname}' reported success but no ID in response: {app_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating Access Application for '{hostname}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating Access Application for '{hostname}': {e}", exc_info=True)
        return None

def get_cloudflare_access_application(app_uuid):
    logging.info(f"Getting Cloudflare Access Application details for ID '{app_uuid}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/access/apps/{app_uuid}"
    try:
        response_data = cf_api_request("GET", endpoint)
        app_data = response_data.get("result")
        if app_data:
            logging.info(f"Successfully retrieved Access Application details for ID '{app_uuid}'")
            return app_data
        else:

            logging.warning(f"Successfully called API for Access App ID '{app_uuid}', but no result data found. Response: {response_data}")
            return None
    except requests.exceptions.RequestException as e:

        if e.response is not None and e.response.status_code == 404:
            logging.warning(f"Cloudflare Access Application with ID '{app_uuid}' not found (404).")
        else:
            logging.error(f"API error getting Access Application '{app_uuid}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting Access Application '{app_uuid}': {e}", exc_info=True)
        return None

def update_cloudflare_access_application(app_uuid, hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    logging.info(f"Updating Cloudflare Access Application ID '{app_uuid}' for hostname '{hostname}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/access/apps/{app_uuid}"
    payload = _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps, auto_redirect_to_identity)
    try:
        response_data = cf_api_request("PUT", endpoint, json_data=payload)
        app_data = response_data.get("result")
        if app_data and app_data.get("id"):
            logging.info(f"Successfully updated Access Application '{app_data.get('id')}' for '{hostname}'")
            return app_data
        else:
            logging.error(f"Access Application update for '{app_uuid}' reported success but no ID in response: {app_data}")
            return None 
    except requests.exceptions.RequestException as e:
        logging.error(f"API error updating Access Application '{app_uuid}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error updating Access Application '{app_uuid}': {e}", exc_info=True)
        return None

def delete_cloudflare_access_application(app_uuid):
    logging.info(f"Deleting Cloudflare Access Application ID '{app_uuid}'")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/access/apps/{app_uuid}"
    try:
        response_data = cf_api_request("DELETE", endpoint)

        if response_data and response_data.get("success"): 

            deleted_id = response_data.get("result", {}).get("id") if isinstance(response_data.get("result"), dict) else app_uuid
            logging.info(f"Successfully submitted deletion for Access Application ID '{deleted_id if deleted_id else app_uuid}'")
            return True

        elif response_data is None and "success" not in str(response_data): 
            logging.info(f"Access Application ID '{app_uuid}' deletion API call likely succeeded (no content/error).")
            return True

        logging.warning(f"Access Application deletion for '{app_uuid}' API call did not confirm success clearly. Response: {response_data}")
        return False 
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 404:
            logging.warning(f"Cloudflare Access Application with ID '{app_uuid}' not found during delete attempt (404). Treating as success.")
            return True
        logging.error(f"API error deleting Access Application '{app_uuid}': {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error deleting Access Application '{app_uuid}': {e}", exc_info=True)
        return False

def initialize_tunnel():
    """Finds or creates the tunnel and gets its token."""
    logging.info("Initializing tunnel...")
    logging.info(f"Using Cloudflare Account ID: {CF_ACCOUNT_ID}")
    logging.info(f"API Token available: {'Yes (Token masked for security)' if CF_API_TOKEN else 'No (Missing API token)'}")
    logging.info(f"Zone ID available: {'Yes: ' + CF_ZONE_ID if CF_ZONE_ID else 'No (Missing Zone ID)'}")
    logging.info(f"External mode: {USE_EXTERNAL_CLOUDFLARED}")
    logging.info(f"External tunnel ID: {EXTERNAL_TUNNEL_ID}")   
    tunnel_state["status_message"] = "Checking tunnel configuration..."
    tunnel_state["error"] = None
    
    if USE_EXTERNAL_CLOUDFLARED:
        logging.info("External cloudflared configuration detected")
        if EXTERNAL_TUNNEL_ID:
            tunnel_id = EXTERNAL_TUNNEL_ID
            logging.info(f"Using external tunnel ID: {tunnel_id}")
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = None
            tunnel_state["status_message"] = "Using external tunnel to manage DNS and inbound routes."       
    
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
    
    if not TUNNEL_NAME:
        logging.error("TUNNEL_NAME not provided. Required when not using external cloudflared.")
        tunnel_state["status_message"] = "Error: Missing required TUNNEL_NAME parameter"
        tunnel_state["error"] = "TUNNEL_NAME not provided"
        return

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

    if hostname.startswith('*.'):
        domain_part = hostname[2:]  
        
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
        
    if len(hostname) > 253:
        return False
    
    labels = hostname.split('.')
    
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
    try:
        acquired = dns_semaphore.acquire(timeout=30)  
        if not acquired:
            logging.error(f"Timed out waiting for DNS semaphore - too many concurrent operations. Skipping DNS creation for {hostname}")
            return "semaphore_timeout"  
            
        if not zone_id or not hostname or not tunnel_id:
            logging.error("create_cloudflare_dns_record: Missing required arguments.")
            return None

        existing_record_id, correct_tunnel = find_dns_record_id(zone_id, hostname, tunnel_id)
        
        if existing_record_id:
            if correct_tunnel:
                logging.info(f"DNS record for {hostname} already exists with ID {existing_record_id} and correct tunnel. Using existing record.")
                return existing_record_id
            else:

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
                        return existing_record_id  
                except Exception as update_err:
                    logging.error(f"Error updating existing DNS record for {hostname}: {update_err}")
                    return existing_record_id  
        
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
            
            if (cf_error_code == 81057 or 
                (e.response is not None and (
                    "record already exists" in e.response.text.lower() or 
                    "a, aaaa, or cname record with that host already exists" in e.response.text.lower()
                ))
            ):
                logging.warning(f"DNS record for {hostname} already exists in zone {zone_id}. Treating as success.")
            
                time.sleep(1)  
                existing_id, _ = find_dns_record_id(zone_id, hostname, tunnel_id)
                if existing_id:
                    logging.info(f"Found existing record ID for {hostname}: {existing_id}")
                    return existing_id
                  
            
                return "existing_record" 
            else:
                logging.error(f"API error creating DNS record for {hostname}: {e}")
                return None
        except Exception as e:
            logging.error(f"Unexpected error creating DNS record for {hostname}: {e}", exc_info=True)
            return None
    finally:
        
        if 'acquired' in locals() and acquired:
            dns_semaphore.release()
            logging.debug(f"Released DNS semaphore after processing {hostname}")

def find_dns_record_id(zone_id, hostname, tunnel_id):
    """Finds the ID of a specific CNAME DNS record pointing to the tunnel."""
    
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
        
        params = {"type": "CNAME", "name": hostname, "content": expected_content, "match": "all"}

        try:
            logging.info(f"Searching DNS: Zone={zone_id}, Type=CNAME, Name={hostname}, Content={expected_content}")
            response_data = cf_api_request("GET", endpoint, params=params)
            results = response_data.get("result", [])

            if results and isinstance(results, list):
                record_id = results[0].get("id")
                if record_id:
                    logging.info(f"Found DNS record for {hostname} in zone {zone_id} with ID: {record_id}")
                    return record_id, True  
                else:
                    logging.warning(f"DNS record found for {hostname} but it lacks an ID field: {results[0]}")
                    return None, False
            
        
            params = {"type": "CNAME", "name": hostname}
            response_data = cf_api_request("GET", endpoint, params=params)
            results = response_data.get("result", [])
            
            if results and isinstance(results, list):
                record_id = results[0].get("id")
                record_content = results[0].get("content", "")
                if record_id:
                    logging.warning(f"Found DNS record for {hostname} but it points to {record_content} instead of {expected_content}")
                    return record_id, False  
                
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
    with dns_semaphore:  
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
def generate_access_app_config_hash(policy_type, session_duration, app_launcher_visible, allowed_idps_str, auto_redirect_to_identity, custom_access_rules_str=None):

    config_items = {
        "policy_type": policy_type,
        "session_duration": session_duration,
        "app_launcher_visible": app_launcher_visible,
        "allowed_idps_str": allowed_idps_str, 
        "auto_redirect_to_identity": auto_redirect_to_identity,
        "custom_access_rules_str": custom_access_rules_str 
    }

    consistent_config_string = json.dumps(config_items, sort_keys=True)

    hasher = hashlib.sha256()
    hasher.update(consistent_config_string.encode('utf-8'))
    return hasher.hexdigest()

def _handle_access_policy_from_labels(hostname_config_item, current_rule_in_state):
    hostname = hostname_config_item["hostname"]
    
    desired_access_policy_type_from_label = hostname_config_item["access_policy_type"]
    desired_access_app_name_from_label = hostname_config_item["access_app_name"] if hostname_config_item["access_app_name"] else f"DockFlare-{hostname}"
    desired_session_duration_from_label = hostname_config_item["access_session_duration"]
    desired_app_launcher_visible_from_label = hostname_config_item["access_app_launcher_visible"]
    desired_allowed_idps_str_from_label = hostname_config_item["access_allowed_idps_str"]
    desired_auto_redirect_from_label = hostname_config_item["access_auto_redirect"]
    desired_custom_rules_str_from_label = hostname_config_item["access_custom_rules_str"]

    local_state_changed_by_access_policy = False
    current_access_app_id = current_rule_in_state.get("access_app_id")
    current_access_policy_type_in_state = current_rule_in_state.get("access_policy_type")
    current_access_app_config_hash_in_state = current_rule_in_state.get("access_app_config_hash")

    if desired_access_policy_type_from_label: 
        desired_access_app_config_hash_from_label = generate_access_app_config_hash(
            desired_access_policy_type_from_label,
            desired_session_duration_from_label,
            desired_app_launcher_visible_from_label,
            desired_allowed_idps_str_from_label,
            desired_auto_redirect_from_label,
            desired_custom_rules_str_from_label
        )

        if desired_access_policy_type_from_label == "default_tld":
            if current_access_app_id:
                logging.info(f"Label policy for {hostname} is 'default_tld'. Deleting existing Access App {current_access_app_id}.")
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule_in_state["access_app_id"] = None
                    current_rule_in_state["access_policy_type"] = "default_tld"
                    current_rule_in_state["access_app_config_hash"] = None
                    local_state_changed_by_access_policy = True
                else:
                    logging.error(f"Failed to delete Access App {current_access_app_id} for {hostname} as per label 'default_tld'.")
            elif current_access_policy_type_in_state != "default_tld":
                current_rule_in_state["access_app_id"] = None
                current_rule_in_state["access_policy_type"] = "default_tld"
                current_rule_in_state["access_app_config_hash"] = None
                local_state_changed_by_access_policy = True
                logging.info(f"Label policy for {hostname} set to 'default_tld'. No specific app managed.")

        elif desired_access_policy_type_from_label in ["bypass", "authenticate"]:
            cf_access_policies = []
            if desired_custom_rules_str_from_label:
                try:
                    cf_access_policies = json.loads(desired_custom_rules_str_from_label)
                    if not isinstance(cf_access_policies, list):
                        logging.error(f"Parsed 'custom_rules' label for {hostname} is not a list. Reverting to default for {desired_access_policy_type_from_label}.")
                        cf_access_policies = [] 
                except json.JSONDecodeError as json_err:
                    logging.error(f"Error parsing 'custom_rules' label JSON for {hostname}: {json_err}. Reverting to default for {desired_access_policy_type_from_label}.")
                    cf_access_policies = [] 
            
            if not cf_access_policies:
                if desired_access_policy_type_from_label == "bypass":
                    cf_access_policies = [{"name": "Label Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
                elif desired_access_policy_type_from_label == "authenticate":
                    policy_include_rules = []
                    if desired_allowed_idps_str_from_label:
                        idp_ids = [idp.strip() for idp in desired_allowed_idps_str_from_label.split(',') if idp.strip()]
                        if idp_ids:
                            policy_include_rules.append({"identity_provider": {"id": idp_ids}})
                    if not policy_include_rules:
                        policy_include_rules.append({"everyone": {}}) 
                    cf_access_policies = [{"name": "Label Default Authenticated Access", "decision": "allow", "include": policy_include_rules}]
            
            allowed_idps_list_for_app = [idp.strip() for idp in desired_allowed_idps_str_from_label.split(',') if idp.strip()] if desired_allowed_idps_str_from_label else None
            needs_action = False
            if current_access_app_id:
                if current_access_policy_type_in_state != desired_access_policy_type_from_label or \
                   current_access_app_config_hash_in_state != desired_access_app_config_hash_from_label:
                    needs_action = True
            else:
                needs_action = True

            if needs_action:
                if current_access_app_id:
                    logging.info(f"Updating Access App {current_access_app_id} for {hostname} based on labels (type: {desired_access_policy_type_from_label}).")
                    updated_app = update_cloudflare_access_application(
                        current_access_app_id, hostname, desired_access_app_name_from_label,
                        desired_session_duration_from_label, desired_app_launcher_visible_from_label,
                        [hostname], cf_access_policies, allowed_idps_list_for_app, desired_auto_redirect_from_label
                    )
                    if updated_app:
                        current_rule_in_state["access_policy_type"] = desired_access_policy_type_from_label
                        current_rule_in_state["access_app_config_hash"] = desired_access_app_config_hash_from_label
                        local_state_changed_by_access_policy = True
                    else:
                        logging.error(f"Failed to update Access App {current_access_app_id} for {hostname} based on labels.")
                else:
                    logging.info(f"Creating new Access App for {hostname} based on labels (type: '{desired_access_policy_type_from_label}').")
                    created_app = create_cloudflare_access_application(
                        hostname, desired_access_app_name_from_label,
                        desired_session_duration_from_label, desired_app_launcher_visible_from_label,
                        [hostname], cf_access_policies, allowed_idps_list_for_app, desired_auto_redirect_from_label
                    )
                    if created_app and created_app.get("id"):
                        current_rule_in_state["access_app_id"] = created_app.get("id")
                        current_rule_in_state["access_policy_type"] = desired_access_policy_type_from_label
                        current_rule_in_state["access_app_config_hash"] = desired_access_app_config_hash_from_label
                        local_state_changed_by_access_policy = True
                    else:
                        logging.error(f"Failed to create Access App for {hostname} based on labels.")
        else:
            logging.warning(f"Unknown access.policy type '{desired_access_policy_type_from_label}' from label for {hostname}. No Access App action taken based on this label.")
    else: 
        if current_access_app_id:
            logging.info(f"No access policy label for {hostname}, but found managed Access App {current_access_app_id}. Deleting it as per label configuration.")
            if delete_cloudflare_access_application(current_access_app_id):
                current_rule_in_state["access_app_id"] = None
                current_rule_in_state["access_policy_type"] = None
                current_rule_in_state["access_app_config_hash"] = None
                local_state_changed_by_access_policy = True
            else:
                logging.error(f"Failed to delete Access App {current_access_app_id} for {hostname} during label-based cleanup.")
        elif current_access_policy_type_in_state is not None : 
            current_rule_in_state["access_app_id"] = None
            current_rule_in_state["access_policy_type"] = None
            current_rule_in_state["access_app_config_hash"] = None
            local_state_changed_by_access_policy = True
            logging.debug(f"Ensuring policy type is None for {hostname} as no access labels are present.")
            
    return local_state_changed_by_access_policy

def process_container_start(container):
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

        hostnames_to_process = []
        
        default_access_policy_type_label = labels.get(f"{LABEL_PREFIX}.access.policy")
        default_access_app_name_label = labels.get(f"{LABEL_PREFIX}.access.name")
        default_access_session_duration_label = labels.get(f"{LABEL_PREFIX}.access.session_duration", "24h")
        default_access_app_launcher_visible_label = labels.get(f"{LABEL_PREFIX}.access.app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
        default_access_allowed_idps_label_str = labels.get(f"{LABEL_PREFIX}.access.allowed_idps")
        default_access_auto_redirect_label = labels.get(f"{LABEL_PREFIX}.access.auto_redirect_to_identity", "false").lower() in ["true", "1", "t", "yes"]
        default_access_custom_rules_label_str = labels.get(f"{LABEL_PREFIX}.access.custom_rules")

        hostname_label = labels.get(f"{LABEL_PREFIX}.hostname") 
        service_label = labels.get(f"{LABEL_PREFIX}.service") 
        zone_name_label = labels.get(f"{LABEL_PREFIX}.zonename") 
        no_tls_verify_label = labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]
        
        if hostname_label and service_label:
            if is_valid_hostname(hostname_label) and is_valid_service(service_label):
                hostnames_to_process.append({
                    "hostname": hostname_label,
                    "service": service_label,
                    "zone_name": zone_name_label,
                    "no_tls_verify": no_tls_verify_label,
                    "access_policy_type": default_access_policy_type_label,
                    "access_app_name": default_access_app_name_label,
                    "access_session_duration": default_access_session_duration_label,
                    "access_app_launcher_visible": default_access_app_launcher_visible_label,
                    "access_allowed_idps_str": default_access_allowed_idps_label_str,
                    "access_auto_redirect": default_access_auto_redirect_label,
                    "access_custom_rules_str": default_access_custom_rules_label_str
                })
            else:
                logging.warning(f"Ignoring invalid direct label pair for {container_name}: Invalid hostname '{hostname_label}' or service '{service_label}'")
        
        index = 0
        while True:
            prefix = f"{LABEL_PREFIX}.{index}"
            hostname_indexed = labels.get(f"{prefix}.hostname")
            if not hostname_indexed:
                break
                
            service_indexed = labels.get(f"{prefix}.service")
            if not service_indexed:
                service_indexed = labels.get(f"{LABEL_PREFIX}.service") 
                if not service_indexed:
                    logging.warning(f"Ignoring indexed hostname {hostname_indexed} for {container_name}: Missing service for index {index} and no default service label.")
                    index += 1
                    continue
            
            zone_name_indexed = labels.get(f"{prefix}.zonename", labels.get(f"{LABEL_PREFIX}.zonename"))
            no_tls_verify_indexed_value = labels.get(f"{prefix}.no_tls_verify", labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false"))
            no_tls_verify_indexed = no_tls_verify_indexed_value.lower() in ["true", "1", "t", "yes"]

            access_policy_type_indexed = labels.get(f"{prefix}.access.policy", default_access_policy_type_label)
            access_app_name_indexed = labels.get(f"{prefix}.access.name", default_access_app_name_label)
            access_session_duration_indexed = labels.get(f"{prefix}.access.session_duration", default_access_session_duration_label)
            access_app_launcher_visible_indexed_val = labels.get(f"{prefix}.access.app_launcher_visible", str(default_access_app_launcher_visible_label).lower())
            access_app_launcher_visible_indexed = access_app_launcher_visible_indexed_val.lower() in ["true", "1", "t", "yes"]
            access_allowed_idps_indexed_str = labels.get(f"{prefix}.access.allowed_idps", default_access_allowed_idps_label_str)
            access_auto_redirect_indexed_val = labels.get(f"{prefix}.access.auto_redirect_to_identity", str(default_access_auto_redirect_label).lower())
            access_auto_redirect_indexed = access_auto_redirect_indexed_val.lower() in ["true", "1", "t", "yes"]
            access_custom_rules_indexed_str = labels.get(f"{prefix}.access.custom_rules", default_access_custom_rules_label_str)

            if is_valid_hostname(hostname_indexed) and is_valid_service(service_indexed):
                hostnames_to_process.append({
                    "hostname": hostname_indexed,
                    "service": service_indexed,
                    "zone_name": zone_name_indexed,
                    "no_tls_verify": no_tls_verify_indexed,
                    "access_policy_type": access_policy_type_indexed,
                    "access_app_name": access_app_name_indexed,
                    "access_session_duration": access_session_duration_indexed,
                    "access_app_launcher_visible": access_app_launcher_visible_indexed,
                    "access_allowed_idps_str": access_allowed_idps_indexed_str,
                    "access_auto_redirect": access_auto_redirect_indexed,
                    "access_custom_rules_str": access_custom_rules_indexed_str
                })
            else:
                logging.warning(f"Ignoring invalid indexed label pair for {container_name} (index {index}): Invalid hostname '{hostname_indexed}' or service '{service_indexed}'")
            
            index += 1
        
        if not hostnames_to_process:
            logging.warning(f"No valid hostname configurations found for {container_name} ({container_id[:12]})")
            return
            
        logging.info(f"Found {len(hostnames_to_process)} hostname configurations for container {container_name}")
        
        state_changed_locally = False
        needs_tunnel_config_update = False
        
        for config_item in hostnames_to_process:
            hostname = config_item["hostname"]
            service = config_item["service"]
            zone_name_from_item = config_item["zone_name"] 
            no_tls_verify_from_item = config_item["no_tls_verify"] 
            
            target_zone_id = None
            if zone_name_from_item:
                logging.info(f"Hostname {hostname} specified zone name: '{zone_name_from_item}'. Looking up ID.")
                target_zone_id = get_zone_id_from_name(zone_name_from_item)
                if not target_zone_id:
                    logging.error(f"Failed to find Zone ID for specified name '{zone_name_from_item}' for hostname {hostname}. Skipping.")
                    continue
            else:
                logging.debug(f"Hostname {hostname} did not specify zone name. Using default Zone ID if available.")
                target_zone_id = CF_ZONE_ID

            if not target_zone_id:
                logging.error(f"Cannot manage DNS for {hostname}: No valid Zone ID found. Skipping.")
                continue
                
            logging.info(f"Managing {hostname} (from {container_name}) in Zone ID: {target_zone_id}")
            
            with state_lock:
                if hostname in managed_rules and managed_rules[hostname].get("source") == "manual":
                    logging.warning(f"Container {container_name} attempting to manage hostname '{hostname}', but it's already a manual entry. Skipping Docker label for this hostname.")
                    continue

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
                        existing_rule["no_tls_verify"] = no_tls_verify_from_item
                        existing_rule["source"] = "docker"
                        state_changed_locally = True
                        needs_tunnel_config_update = True
                        if zone_id_changed:
                            logging.info(f"Zone ID for reactivated rule {hostname} updated to {target_zone_id}.")
                    elif existing_rule.get("status") == "active":
                        service_changed = existing_rule.get("service") != service
                        container_changed = existing_rule.get("container_id") != container_id
                        no_tls_verify_changed = existing_rule.get("no_tls_verify") != no_tls_verify_from_item

                        if container_changed:
                            logging.info(f"Updating container ID for active rule {hostname}: '{existing_rule.get('container_id')[:12] if existing_rule.get('container_id') else 'N/A'}' -> '{container_id[:12]}'.")
                            existing_rule["container_id"] = container_id
                            state_changed_locally = True
                        if service_changed:
                            logging.info(f"Updating service for active rule {hostname}: '{existing_rule.get('service')}' -> '{service}'.")
                            existing_rule["service"] = service
                            state_changed_locally = True
                            needs_tunnel_config_update = True
                        if no_tls_verify_changed:
                            logging.info(f"Updating noTLSVerify for active rule {hostname}: '{existing_rule.get('no_tls_verify')}' -> '{no_tls_verify_from_item}'.")
                            existing_rule["no_tls_verify"] = no_tls_verify_from_item
                            state_changed_locally = True
                            needs_tunnel_config_update = True
                        if zone_id_changed:
                            logging.warning(f"Zone ID for active rule {hostname} changed ('{existing_rule.get('zone_id')}' -> '{target_zone_id}'). DNS in old zone may be stale.")
                            existing_rule["zone_id"] = target_zone_id
                            state_changed_locally = True
                            needs_tunnel_config_update = True
                        
                        existing_rule["source"] = "docker" 
                else:
                    logging.info(f"Adding new active rule for hostname: {hostname}")
                    managed_rules[hostname] = {
                        "service": service,
                        "container_id": container_id,
                        "status": "active",
                        "delete_at": None,
                        "zone_id": target_zone_id,
                        "no_tls_verify": no_tls_verify_from_item,
                        "access_app_id": None, 
                        "access_policy_type": None,
                        "access_app_config_hash": None,
                        "access_policy_ui_override": False,
                        "source": "docker"
                    }
                    existing_rule = managed_rules[hostname] 
                    state_changed_locally = True
                    needs_tunnel_config_update = True
                
                if existing_rule.get("access_policy_ui_override", False):
                    logging.info(f"Access policy for {hostname} (current type: {existing_rule.get('access_policy_type')}) is UI-managed. Skipping label-based Access Policy processing.")
                else:
                    logging.debug(f"Processing Access Policy from labels for {hostname} (not UI-managed).")
                    if _handle_access_policy_from_labels(config_item, existing_rule):
                        state_changed_locally = True
                        
        if state_changed_locally:
            logging.debug(f"Saving state after processing start for container {container_name}.")
            save_state()

        if needs_tunnel_config_update: 
            logging.info(f"Triggering Cloudflare tunnel config update due to changes for container {container_name}.")
            if update_cloudflare_config():
                logging.info(f"Tunnel config update successful for container {container_name}.")

                if tunnel_state.get("id") or USE_EXTERNAL_CLOUDFLARED:
                    effective_tunnel_id = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID
                    if effective_tunnel_id:
                        for config_item_dns in hostnames_to_process: 
                            hostname_dns = config_item_dns["hostname"]
                            
                            if managed_rules.get(hostname_dns, {}).get("source") == "manual":
                                continue

                            zone_name_dns = config_item_dns["zone_name"]
                            
                            target_zone_id_dns = get_zone_id_from_name(zone_name_dns) if zone_name_dns else CF_ZONE_ID
                            
                            if target_zone_id_dns:
                                dns_record_id = create_cloudflare_dns_record(target_zone_id_dns, hostname_dns, effective_tunnel_id)
                                if dns_record_id:
                                    logging.info(f"DNS record management in zone {target_zone_id_dns} successful for {hostname_dns}.")
                                else:
                                    logging.error(f"CRITICAL: Tunnel config or service for {hostname_dns} might be active but failed to create/verify DNS record in zone {target_zone_id_dns}!")
                                    cloudflared_agent_state["last_action_status"] = f"Error: Failed creating DNS for {hostname_dns} in zone {target_zone_id_dns}."
                            else:
                                logging.error(f"Missing Zone ID - cannot manage DNS record for {hostname_dns}.")
                    else:
                        logging.error(f"Missing effective Tunnel ID - cannot manage DNS records for container {container_name}.")
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
    logging.info("Starting cleanup task...")
    while not stop_event.is_set():
        next_check_time = time.time() + CLEANUP_INTERVAL_SECONDS
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
                             delete_at_utc = delete_at.astimezone(timezone.utc)
                             if delete_at_utc <= now_utc:
                                 is_expired = True
                        else:
                             logging.warning(f"Rule {hostname} pending delete but has invalid delete_at timestamp: {delete_at}. Marking for immediate deletion processing.")
                             is_expired = True

                        if is_expired:
                            zone_id_for_delete = details.get("zone_id", CF_ZONE_ID)
                            access_app_id_for_delete = details.get("access_app_id")
                            
                            if not zone_id_for_delete:
                                logging.error(f"Cannot schedule DNS deletion for expired rule {hostname}: Zone ID is missing in state and no default CF_ZONE_ID is set. Rule will be removed from state only.")
                            
                            rules_to_process_for_deletion[hostname] = {
                                "zone_id": zone_id_for_delete,
                                "access_app_id": access_app_id_for_delete
                            }
                            logging.info(f"Rule for {hostname} (Zone: {zone_id_for_delete}, Access App: {access_app_id_for_delete}) expired. Scheduling for full deletion.")
                    elif details.get("source") == "manual" and details.get("status") == "pending_deletion":
                        logging.warning(f"Manual rule {hostname} found in 'pending_deletion' state. This should not happen. Resetting to 'active'.")
                        details["status"] = "active"
                        details["delete_at"] = None
                        state_changed_in_cleanup = True


            if state_changed_in_cleanup and not rules_to_process_for_deletion:
                save_state()
                state_changed_in_cleanup = False

            if rules_to_process_for_deletion:
                logging.info(f"Processing cleanup for hostnames: {list(rules_to_process_for_deletion.keys())}")
                hostnames_fully_cleaned_for_state_removal = []
                
                effective_tunnel_id = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID

                for hostname, delete_info in rules_to_process_for_deletion.items():
                    dns_deleted_successfully = False
                    access_app_deleted_successfully = False
                    zone_id = delete_info["zone_id"]
                    access_app_id = delete_info["access_app_id"]

                    
                    if zone_id and effective_tunnel_id:
                         logging.info(f"Attempting DNS record deletion for expired rule: {hostname} in zone {zone_id}")
                         if delete_cloudflare_dns_record(zone_id, hostname, effective_tunnel_id):
                              dns_deleted_successfully = True
                         else:
                              logging.error(f"Failed to delete DNS record for {hostname} in zone {zone_id}. It may remain stale.")
                    elif not zone_id:
                        logging.warning(f"Skipping DNS deletion for {hostname} as Zone ID is unavailable.")
                    elif not effective_tunnel_id:
                        logging.warning(f"Skipping DNS deletion for {hostname} as Tunnel ID is unavailable.")
                    
                    
                    if access_app_id:
                        logging.info(f"Attempting Access Application deletion for expired rule: {hostname}, App ID: {access_app_id}")
                        if delete_cloudflare_access_application(access_app_id):
                            access_app_deleted_successfully = True
                        else:
                            logging.error(f"Failed to delete Access Application {access_app_id} for {hostname}. It may remain orphaned.")
                    else:
                        access_app_deleted_successfully = True 

                    
                    hostnames_fully_cleaned_for_state_removal.append(hostname)


                if hostnames_fully_cleaned_for_state_removal:
                   
                    logging.info(f"Attempting Cloudflare tunnel config update after processing deletions for: {hostnames_fully_cleaned_for_state_removal}")
                    if update_cloudflare_config() or USE_EXTERNAL_CLOUDFLARED: 
                        logging.info(f"Cloudflare tunnel config update successful (or skipped for external). Removing rules from local state: {hostnames_fully_cleaned_for_state_removal}")
                        with state_lock:
                            deleted_count = 0
                            for hostname in hostnames_fully_cleaned_for_state_removal:
                                if hostname in managed_rules and managed_rules[hostname].get("status") == "pending_deletion" and managed_rules[hostname].get("source", "docker") == "docker":
                                    del managed_rules[hostname]
                                    deleted_count += 1
                                    state_changed_in_cleanup = True
                                else:
                                    logging.warning(f"Rule {hostname} was scheduled for removal but not found or not pending/docker when removing from state.")
                            logging.info(f"Removed {deleted_count} rules from local state after cleanup.")
                            if state_changed_in_cleanup:
                                save_state()
                    else:
                        logging.error("Failed to update Cloudflare tunnel config during rule cleanup. Rules remain in local state but their cloud resources might have been deleted. Will retry on next cycle or reconciliation.")
                else:
                     logging.info("No hostnames processed for state removal during cleanup.")
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

    
    app.reconciliation_info = {
        "in_progress": True,
        "progress": 0,
        "total_items": 0,
        "processed_items": 0,
        "start_time": time.time(),
        "status": "Starting reconciliation..."
    }

    
    reconcile_thread = threading.Thread(
        target=_run_reconciliation,
        name="ReconciliationThread",
        daemon=True
    )
    reconcile_thread.start()
    
    logging.info(f"Started reconciliation in background thread {reconcile_thread.name}")
    return

def _run_reconciliation():
    logging.info("[Reconcile Thread] Starting state reconciliation...")
    needs_tunnel_config_update = False 
    state_changed_locally = False
    
    max_total_time = 480 
    reconciliation_start = time.time()
    
    app.reconciliation_info = {
        "in_progress": True, "progress": 0, "total_items": 0,
        "processed_items": 0, "start_time": reconciliation_start,
        "status": "Initializing reconciliation..."
    }

    def watchdog_timer():
        elapsed = time.time() - reconciliation_start
        if elapsed > max_total_time and getattr(app, 'reconciliation_info', {}).get('in_progress', False):
            logging.error(f"[Reconcile] WATCHDOG: Reconciliation taking too long ({elapsed:.1f}s)! Forcing completion.")
            app.reconciliation_info["in_progress"] = False
            app.reconciliation_info["progress"] = 100
            app.reconciliation_info["status"] = "Forced completion by watchdog timer"
            app.reconciliation_info["completed_at"] = time.time()
    
    watchdog = threading.Timer(max_total_time + 10, watchdog_timer)
    watchdog.daemon = True
    watchdog.start()
    
    try:
        running_labeled_hostnames_details = {} 
        try:
            app.reconciliation_info["status"] = "Scanning containers for services and access policies..."
            logging.debug("[Reconcile] Starting container scan phase")
            
            containers = docker_client.containers.list(sparse=False, all=SCAN_ALL_NETWORKS)
            container_count = len(containers)
            logging.debug(f"[Reconcile] Found {container_count} total containers.")
            app.reconciliation_info["total_items"] = container_count 

            batch_size = 3 if not USE_EXTERNAL_CLOUDFLARED else 2
            processed_container_count = 0

            for i in range(0, container_count, batch_size):
                if time.time() - reconciliation_start > 60: 
                    logging.warning("[Reconcile] Timeout during container scanning phase.")
                    app.reconciliation_info["status"] = "Container scan timeout (partial data)"
                    break
                
                batch = containers[i:i+batch_size]
                processed_container_count += len(batch)
                app.reconciliation_info["progress"] = min(100, int((processed_container_count / container_count) * 100)) if container_count > 0 else 0
                app.reconciliation_info["processed_items"] = processed_container_count
                app.reconciliation_info["status"] = f"Scanning containers: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                
                for c in batch:
                    container_scan_item_start_time = time.time()
                    try:
                        labels = c.labels
                        container_id_val = c.id 
                        container_name_val = c.name 
                        enabled = labels.get(f"{LABEL_PREFIX}.enable", "false").lower() in ["true", "1", "t", "yes"]
                        
                        if not enabled:
                            continue
                        
                        default_access_policy_type = labels.get(f"{LABEL_PREFIX}.access.policy")
                        default_access_app_name = labels.get(f"{LABEL_PREFIX}.access.name")
                        default_session_duration = labels.get(f"{LABEL_PREFIX}.access.session_duration", "24h")
                        default_app_launcher_visible = labels.get(f"{LABEL_PREFIX}.access.app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
                        default_allowed_idps_str = labels.get(f"{LABEL_PREFIX}.access.allowed_idps")
                        default_auto_redirect = labels.get(f"{LABEL_PREFIX}.access.auto_redirect_to_identity", "false").lower() in ["true", "1", "t", "yes"]
                        default_custom_rules_str = labels.get(f"{LABEL_PREFIX}.access.custom_rules")

                        hostname_configs_for_container = []
                        
                        h = labels.get(f"{LABEL_PREFIX}.hostname")
                        s = labels.get(f"{LABEL_PREFIX}.service")
                        zn = labels.get(f"{LABEL_PREFIX}.zonename")
                        ntv = labels.get(f"{LABEL_PREFIX}.no_tls_verify", "false").lower() in ["true", "1", "t", "yes"]
                        if h and s and is_valid_hostname(h) and is_valid_service(s):
                            hostname_configs_for_container.append({
                                "hostname": h, "service": s, "zone_name": zn, "no_tls_verify": ntv,
                                "access_policy_type": default_access_policy_type,
                                "access_app_name": default_access_app_name,
                                "access_session_duration": default_session_duration,
                                "access_app_launcher_visible": default_app_launcher_visible,
                                "access_allowed_idps_str": default_allowed_idps_str,
                                "access_auto_redirect": default_auto_redirect,
                                "access_custom_rules_str": default_custom_rules_str
                            })
                        
                        idx = 0
                        while time.time() - container_scan_item_start_time < 5 : 
                            pfx = f"{LABEL_PREFIX}.{idx}"
                            h_idx = labels.get(f"{pfx}.hostname")
                            if not h_idx: break
                            s_idx = labels.get(f"{pfx}.service", s) 
                            if not s_idx: idx += 1; continue
                            
                            zn_idx = labels.get(f"{pfx}.zonename", zn)
                            ntv_idx = labels.get(f"{pfx}.no_tls_verify", str(ntv).lower()).lower() in ["true", "1", "t", "yes"]

                            acc_pol_idx = labels.get(f"{pfx}.access.policy", default_access_policy_type)
                            acc_name_idx = labels.get(f"{pfx}.access.name", default_access_app_name)
                            acc_sess_idx = labels.get(f"{pfx}.access.session_duration", default_session_duration)
                            acc_vis_idx = labels.get(f"{pfx}.access.app_launcher_visible", str(default_app_launcher_visible).lower()).lower() in ["true", "1", "t", "yes"]
                            acc_idps_idx = labels.get(f"{pfx}.access.allowed_idps", default_allowed_idps_str)
                            acc_redir_idx = labels.get(f"{pfx}.access.auto_redirect_to_identity", str(default_auto_redirect).lower()).lower() in ["true", "1", "t", "yes"]
                            acc_custom_idx = labels.get(f"{pfx}.access.custom_rules", default_custom_rules_str)

                            if is_valid_hostname(h_idx) and is_valid_service(s_idx):
                                hostname_configs_for_container.append({
                                    "hostname": h_idx, "service": s_idx, "zone_name": zn_idx, "no_tls_verify": ntv_idx,
                                    "access_policy_type": acc_pol_idx, "access_app_name": acc_name_idx,
                                    "access_session_duration": acc_sess_idx, "access_app_launcher_visible": acc_vis_idx,
                                    "access_allowed_idps_str": acc_idps_idx, "access_auto_redirect": acc_redir_idx,
                                    "access_custom_rules_str": acc_custom_idx
                                })
                            idx += 1
                        
                        for config_item in hostname_configs_for_container:  
                            hostname_val = config_item["hostname"] 
                            if hostname_val in running_labeled_hostnames_details:
                                logging.warning(f"[Reconcile] Duplicate hostname '{hostname_val}' found from labels. Using latest encountered: {container_name_val}.")
                            running_labeled_hostnames_details[hostname_val] = {
                                "hostname": hostname_val,  
                                "service": config_item["service"], 
                                "container_id": container_id_val, 
                                "container_name": container_name_val,
                                "zone_name": config_item["zone_name"], 
                                "no_tls_verify": config_item["no_tls_verify"],
                                "access_policy_type": config_item["access_policy_type"],
                                "access_app_name": config_item["access_app_name"],
                                "access_session_duration": config_item["access_session_duration"],
                                "access_app_launcher_visible": config_item["access_app_launcher_visible"],
                                "access_allowed_idps_str": config_item["access_allowed_idps_str"],
                                "access_auto_redirect": config_item["access_auto_redirect"],
                                "access_custom_rules_str": config_item["access_custom_rules_str"]
                            }
                    except Exception as e_cont:
                        logging.error(f"[Reconcile] Error processing container {c.id[:12] if c and c.id else 'N/A'}: {e_cont}")
                        continue
                if USE_EXTERNAL_CLOUDFLARED and i + batch_size < container_count: time.sleep(0.05)
            
            logging.info(f"[Reconcile] Found {len(running_labeled_hostnames_details)} running hostnames with DockFlare labels.")
        except Exception as e_phase1:
            logging.error(f"[Reconcile] Error in container scanning phase: {e_phase1}", exc_info=True)
            app.reconciliation_info["status"] = f"Container scan error: {str(e_phase1)}"
        
        app.reconciliation_info["status"] = "Comparing state and reconciling cloud resources..."
        app.reconciliation_info["total_items"] = len(running_labeled_hostnames_details) + len(managed_rules) 
        app.reconciliation_info["processed_items"] = 0
        processed_reconcile_items = 0

        state_lock_timeout = 10 
        state_lock_acquired = False
        
        hostnames_requiring_dns_setup = [] 

        try: 
            state_lock_acquired = state_lock.acquire(timeout=state_lock_timeout)
            if not state_lock_acquired:
                logging.error("[Reconcile] Could not acquire state lock. Reconciliation incomplete.")
                app.reconciliation_info["status"] = "Error: Could not acquire state lock for reconciliation."
            else:
                logging.debug("[Reconcile] Acquired state lock for comparison.")
                now_utc = datetime.now(timezone.utc)
                current_managed_hostnames_in_state = set(managed_rules.keys())
                             
                for hostname, desired_details in running_labeled_hostnames_details.items():
                    processed_reconcile_items +=1
                    app.reconciliation_info["processed_items"] = processed_reconcile_items
                    app.reconciliation_info["progress"] = min(100, int((processed_reconcile_items / app.reconciliation_info["total_items"]) * 100)) if app.reconciliation_info["total_items"] > 0 else 0
                    app.reconciliation_info["status"] = f"Reconciling: {hostname}"

                    if time.time() - reconciliation_start > max_total_time - 30: 
                        logging.warning("[Reconcile] Timeout reached during active rule reconciliation.")
                        break

                    existing_rule_for_hostname = managed_rules.get(hostname)
                    if existing_rule_for_hostname and existing_rule_for_hostname.get("source") == "manual":
                        logging.debug(f"[Reconcile] Hostname {hostname} is manually managed. Skipping update from Docker labels for container {desired_details.get('container_name', 'N/A')}.")

                        continue 

                    target_zone_id = get_zone_id_from_name(desired_details["zone_name"]) if desired_details["zone_name"] else CF_ZONE_ID
                    if not target_zone_id:
                        logging.error(f"[Reconcile] No zone ID for {hostname}, skipping its reconciliation.")
                        continue

                    current_rule = managed_rules.get(hostname)
                    if not current_rule: 
                        logging.info(f"[Reconcile] Adding new rule for {hostname} to managed_rules.")
                        current_rule = {
                            "service": desired_details["service"], "container_id": desired_details["container_id"],
                            "status": "active", "delete_at": None, "zone_id": target_zone_id,
                            "no_tls_verify": desired_details["no_tls_verify"],
                            "access_app_id": None, "access_policy_type": None, "access_app_config_hash": None,
                            "access_policy_ui_override": False,
                            "source": "docker" 
                        }
                        managed_rules[hostname] = current_rule
                        state_changed_locally = True
                        needs_tunnel_config_update = True 
                        hostnames_requiring_dns_setup.append((hostname, target_zone_id))
                    else: 
                        if current_rule.get("status") == "pending_deletion":
                            logging.info(f"[Reconcile] Reactivating pending deletion rule for {hostname}.")
                            current_rule["status"] = "active"; current_rule["delete_at"] = None
                            state_changed_locally = True 
                        
                        service_changed_in_reconcile = current_rule.get("service") != desired_details["service"]
                        no_tls_verify_changed_in_reconcile = current_rule.get("no_tls_verify") != desired_details["no_tls_verify"]
                        zone_id_changed_in_reconcile = current_rule.get("zone_id") != target_zone_id
                        container_id_changed_in_reconcile = current_rule.get("container_id") != desired_details["container_id"]

                        if service_changed_in_reconcile or no_tls_verify_changed_in_reconcile or zone_id_changed_in_reconcile:
                            needs_tunnel_config_update = True 
                        
                        current_rule["service"] = desired_details["service"]
                        current_rule["container_id"] = desired_details["container_id"] 
                        current_rule["zone_id"] = target_zone_id
                        current_rule["no_tls_verify"] = desired_details["no_tls_verify"]
                        current_rule["source"] = "docker" 
                        
                        if service_changed_in_reconcile or no_tls_verify_changed_in_reconcile or zone_id_changed_in_reconcile or container_id_changed_in_reconcile:
                            state_changed_locally = True
                        
                        hostnames_requiring_dns_setup.append((hostname, target_zone_id))
                    
                    if current_rule.get("access_policy_ui_override", False):
                        logging.info(f"[Reconcile] Access policy for {hostname} (current type: {current_rule.get('access_policy_type')}) is UI-managed. Skipping label-based Access Policy processing during reconciliation.")
                    else:
                        logging.debug(f"[Reconcile] Processing Access Policy from labels for {hostname} (not UI-managed) during reconciliation.")
                        if _handle_access_policy_from_labels(desired_details, current_rule):
                            state_changed_locally = True
                
                hostnames_in_state_but_not_running = list(current_managed_hostnames_in_state - set(running_labeled_hostnames_details.keys()))
                
                for hostname_to_check in hostnames_in_state_but_not_running:
                    processed_reconcile_items +=1
                    app.reconciliation_info["processed_items"] = processed_reconcile_items
                    app.reconciliation_info["progress"] = min(100, int((processed_reconcile_items / app.reconciliation_info["total_items"]) * 100)) if app.reconciliation_info["total_items"] > 0 else 0
                    app.reconciliation_info["status"] = f"Reconciling (orphaned?): {hostname_to_check}"

                    if time.time() - reconciliation_start > max_total_time - 20: 
                        logging.warning("[Reconcile] Timeout reached during orphaned rule reconciliation.")
                        break

                    rule = managed_rules.get(hostname_to_check)
                    if rule and rule.get("status") == "active" and rule.get("source", "docker") == "docker": 
                        logging.info(f"[Reconcile] Docker-managed rule for {hostname_to_check} is active but container/labels missing. Marking for deletion.")
                        rule["status"] = "pending_deletion"
                        rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS)
                        state_changed_locally = True
                    elif rule and rule.get("source") == "manual":
                        logging.debug(f"[Reconcile] Manual rule {hostname_to_check} found and is active. Preserving.")
                        # If a manual rule exists, we should ensure its DNS is still set up.
                        # This logic might be redundant if DNS is only set on creation/update of manual rule.
                        # However, it's a safeguard.
                        if rule.get("zone_id"):
                             hostnames_requiring_dns_setup.append((hostname_to_check, rule.get("zone_id")))
                        
                if state_changed_locally:
                    logging.info("[Reconcile] Saving state changes after reconciliation phase.")
                    app.reconciliation_info["status"] = "Saving reconciled state..."
                    save_state()
        
        except Exception as e_lock:
            logging.error(f"[Reconcile] Error during state lock or main reconciliation logic: {e_lock}", exc_info=True)
            app.reconciliation_info["status"] = f"Reconciliation error: {str(e_lock)}"
        finally:
            if state_lock_acquired:
                state_lock.release()
                logging.debug("[Reconcile] Released state lock after reconciliation.")
        
        if time.time() - reconciliation_start > max_total_time - 15: 
             logging.warning("[Reconcile] Timeout reached before Tunnel/DNS operations.")
             needs_tunnel_config_update = False 

        if needs_tunnel_config_update:
            app.reconciliation_info["status"] = "Updating Cloudflare tunnel configuration..."
            logging.info("[Reconcile] Tunnel ingress rules require update.")
            if not USE_EXTERNAL_CLOUDFLARED:
                if not update_cloudflare_config():
                    logging.error("[Reconcile] Failed to update Cloudflare tunnel configuration.")
                    app.reconciliation_info["status"] = "Error: Failed tunnel config update."
                else:
                    logging.info("[Reconcile] Cloudflare tunnel configuration updated successfully.")
                    app.reconciliation_info["status"] = "Tunnel configuration updated."
            else:
                logging.info("[Reconcile] External mode: Skipping DockFlare-managed tunnel config update.")
        else:
            logging.info("[Reconcile] No changes to tunnel ingress rules needed.")
        
        if hostnames_requiring_dns_setup:
            app.reconciliation_info["status"] = f"Setting up DNS for {len(hostnames_requiring_dns_setup)} hostnames..."
            dns_total = len(hostnames_requiring_dns_setup)
            dns_processed = 0
        
            effective_tunnel_id_for_dns = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID
            if effective_tunnel_id_for_dns:
                
                unique_dns_setups = []
                seen_host_zone_pairs = set()
                for hostname_dns, zone_id_dns in hostnames_requiring_dns_setup:
                    if (hostname_dns, zone_id_dns) not in seen_host_zone_pairs:
                        unique_dns_setups.append((hostname_dns, zone_id_dns))
                        seen_host_zone_pairs.add((hostname_dns, zone_id_dns))
                
                logging.info(f"[Reconcile] Unique hostnames for DNS setup: {len(unique_dns_setups)}")

                for hostname_dns, zone_id_dns in unique_dns_setups:
                    dns_processed +=1 
                    app.reconciliation_info["status"] = f"DNS for {hostname_dns} ({dns_processed}/{dns_total})" 
                    
                    if time.time() - reconciliation_start > max_total_time - 5:
                        logging.warning("[Reconcile] Timeout reached during DNS setup phase.")
                        break
                    
                    create_cloudflare_dns_record(zone_id_dns, hostname_dns, effective_tunnel_id_for_dns)
                    if USE_EXTERNAL_CLOUDFLARED: time.sleep(0.1) 
            else:
                logging.error("[Reconcile] Cannot setup DNS: Effective tunnel ID is missing.")
                app.reconciliation_info["status"] = "Error: Missing tunnel ID for DNS setup."
            
    except Exception as e_reconcile_main:
        logging.error(f"[Reconcile] Unhandled error in reconciliation: {e_reconcile_main}", exc_info=True)
        app.reconciliation_info["status"] = f"Reconciliation main error: {str(e_reconcile_main)}"
    
    finally:
        app.reconciliation_info["in_progress"] = False
        app.reconciliation_info["progress"] = 100 
        app.reconciliation_info["status"] = app.reconciliation_info.get("status", "Reconciliation finished.") + " (Final)"
        if "start_time" not in app.reconciliation_info: app.reconciliation_info["start_time"] = reconciliation_start
        app.reconciliation_info["completed_at"] = time.time()
        duration = app.reconciliation_info["completed_at"] - app.reconciliation_info["start_time"]
        watchdog.cancel()
        logging.info(f"[Reconcile Thread] Reconciliation complete. Duration: {duration:.2f} seconds. Status: {app.reconciliation_info['status']}")


def get_cloudflared_container():
    """Gets the cloudflared agent container object."""
    if not docker_client:
        logging.warning("Docker client unavailable.")
        return None
       
    if USE_EXTERNAL_CLOUDFLARED:
        return None
        
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
    if not tunnel_state.get("id"):
        logging.warning("Cannot update CF config, tunnel ID missing.")
        return False

    with state_lock:
        logging.info("Constructing desired Cloudflare tunnel configuration from managed rules...")
      
        desired_dockflare_rules = []
        for hostname, rule_details in managed_rules.items():
            if rule_details.get("status") == "active":
                service = rule_details.get("service")
                if service:

                    no_tls_verify = rule_details.get("no_tls_verify", False)
                    rule_config = {
                        "hostname": hostname,
                        "service": service
                    }
                    if no_tls_verify: 
                        rule_config["originRequest"] = {"noTLSVerify": True}
                    desired_dockflare_rules.append(rule_config)
                else:
                    logging.warning(f"Rule {hostname} is active but missing 'service' detail. Skipping.")

        current_api_config = get_current_cf_config()
        if current_api_config is None:
            logging.error("Failed to fetch current CF config; cannot reliably update.")
            return False
        
        current_api_ingress_rules = current_api_config.get("ingress", [])

        preserved_api_rules = []
        catch_all_rule_template = {"service": "http_status:404"} 

        for api_rule in current_api_ingress_rules:
            api_hostname = api_rule.get("hostname")
            api_service = api_rule.get("service")

            if api_service == catch_all_rule_template["service"] and not api_hostname: 
                preserved_api_rules.append(api_rule)
                continue

            if api_hostname and '*' in api_hostname:
                is_managed_wildcard = False
                for managed_host in managed_rules:
                    if managed_host == api_hostname:
                        is_managed_wildcard = True
                        break
                if not is_managed_wildcard:
                    preserved_api_rules.append(api_rule)

        final_ingress_rules_to_put = list(desired_dockflare_rules)
        for p_rule in preserved_api_rules:
            is_duplicate = False
            p_hostname = p_rule.get("hostname")
            p_service = p_rule.get("service")
            for f_rule in final_ingress_rules_to_put:
                if f_rule.get("hostname") == p_hostname and f_rule.get("service") == p_service:
                    is_duplicate = True
                    break
            if not is_duplicate:
                final_ingress_rules_to_put.append(p_rule)

        has_catch_all = any(r.get("service") == catch_all_rule_template["service"] and not r.get("hostname") for r in final_ingress_rules_to_put)
        if not has_catch_all:
            final_ingress_rules_to_put.append(catch_all_rule_template)
            logging.info("Adding default catch-all rule as none was found/preserved.")

        def rule_to_comparable_dict(rule):          
            comp_dict = {}
            if rule.get("hostname"):
                comp_dict["hostname"] = rule.get("hostname")
            if rule.get("service"):
                comp_dict["service"] = rule.get("service")
            if rule.get("originRequest", {}).get("noTLSVerify"):
                comp_dict["noTLSVerify"] = True 
            return comp_dict

        current_api_comparable_set = {json.dumps(rule_to_comparable_dict(r), sort_keys=True) for r in current_api_ingress_rules}
        final_put_comparable_set = {json.dumps(rule_to_comparable_dict(r), sort_keys=True) for r in final_ingress_rules_to_put}

        needs_api_update = False
        if current_api_comparable_set != final_put_comparable_set:
            logging.info("Ingress rule configuration differs from Cloudflare. Update required.")
            needs_api_update = True
        else:
            current_api_hostnames = [r.get("hostname") for r in current_api_ingress_rules if r.get("hostname")]
            final_put_hostnames = [r.get("hostname") for r in final_ingress_rules_to_put if r.get("hostname")]
            if current_api_hostnames != final_put_hostnames and len(current_api_hostnames) == len(final_put_hostnames) : 
                 logging.info("Ingress rule order differs. Update required to enforce Dockflare's order.")
                 needs_api_update = True 

        if not needs_api_update:
            logging.info("Cloudflare configuration matches desired state. No API update needed.")
            return True 

        logging.info(f"Updating Cloudflare tunnel config. Rules to PUT ({len(final_ingress_rules_to_put)} total):")
        for r_idx, r_val in enumerate(final_ingress_rules_to_put):
            logging.debug(f"  Rule {r_idx+1}: {json.dumps(r_val)}")
    
    if needs_api_update:
        endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        config_payload = {"config": {"ingress": final_ingress_rules_to_put}}
        
        try:
            
            cf_api_request("PUT", endpoint, json_data=config_payload) 
            logging.info("Successfully updated Cloudflare tunnel configuration.")
            return True
        except Exception as e: 
            logging.error(f"Failed to update CF tunnel config: {e}", exc_info=True)
            
            return False
            
    return True 

def get_all_account_cloudflare_tunnels():
    if not CF_ACCOUNT_ID:
        logging.warning("CF_ACCOUNT_ID is not configured. Cannot list all Cloudflare tunnels from the account.")
        return []
    if not CF_API_TOKEN:
        logging.error("Cloudflare API token not configured. Cannot list all account tunnels.")
        return []

    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    params = {
        "is_deleted": "false"
    }

    logging.info(f"Attempting to list all Cloudflare tunnels for account ID {CF_ACCOUNT_ID} with params: {params}")
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])

        if isinstance(tunnels, list):
            logging.info(f"Successfully retrieved {len(tunnels)} Cloudflare tunnels from the account (any status).")
            
            desired_statuses = {"healthy", "degraded", "down", "inactive"}
            filtered_tunnels = [
                tunnel for tunnel in tunnels if tunnel.get("status") in desired_statuses
            ]
            
            logging.info(f"Returning {len(filtered_tunnels)} tunnels after client-side status check for relevant statuses.")
            filtered_tunnels.sort(key=lambda t: t.get("name", "").lower())
            return filtered_tunnels
        else:
            logging.error(f"Unexpected data format for account tunnels list: {type(tunnels)}. Expected a list. Response: {response_data}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"API error listing all Cloudflare tunnels for the account: {e}")
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 403:
                logging.error("Permission denied (403) listing account tunnels. Ensure API token has 'Account:Cloudflare Tunnel:Read' permission for the account.")
            elif e.response.status_code == 400:
                logging.error(f"Bad Request (400) listing account tunnels. API Response: {e.response.text}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error listing all Cloudflare tunnels for the account: {e}", exc_info=True)
        return []

def get_dns_records_for_tunnel(zone_id, tunnel_id):
    if not zone_id or not tunnel_id:
        logging.warning("get_dns_records_for_tunnel: Missing zone_id or tunnel_id.")
        return []

    zone_details = get_zone_details_by_id(zone_id)
    zone_name_for_display = zone_details.get("name") if zone_details else zone_id

    expected_cname_content = f"{tunnel_id}.cfargotunnel.com"
    endpoint = f"/zones/{zone_id}/dns_records"
    params = {"type": "CNAME", "content": expected_cname_content, "per_page": 100}
    logging.info(f"Fetching DNS records for tunnel {tunnel_id} in zone {zone_name_for_display} ({zone_id}) with content {expected_cname_content}")
    
    try:
        response_data = cf_api_request("GET", endpoint, params=params) 
        dns_records_from_api = response_data.get("result", [])
        
        processed_records = []
        if isinstance(dns_records_from_api, list):
            for record in dns_records_from_api:
                if record.get("name"):
                    processed_records.append({
                        "name": record.get("name"), 
                        "id": record.get("id"), 
                        "zone_id": zone_id,
                        "zone_name": zone_name_for_display
                    })
            return processed_records
        else:
            logging.error(f"Unexpected data format for DNS records list in zone {zone_name_for_display}: {type(dns_records_from_api)}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching DNS records for tunnel {tunnel_id} in zone {zone_name_for_display}: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error fetching DNS records for tunnel {tunnel_id} in zone {zone_name_for_display}: {e}", exc_info=True)
        return []
#
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# ! BIG REMINDER Flask start here ! Don't forget you dummy and drink coffee Chris..!
# !   remember you wasted an hour to find the error last time..............        !
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PREFERRED_URL_SCHEME'] = 'https'  

@app.before_request
def detect_protocol():
    """Detect the protocol to use for internal redirects."""
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    app.config['PREFERRED_URL_SCHEME'] = 'https' if forwarded_proto == 'https' or request.is_secure else 'http'

@app.after_request
def add_security_headers(response):
    """Add comprehensive security headers that work in both HTTP and HTTPS environments."""
    
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    is_https = forwarded_proto == 'https' or request.is_secure
    
    csp = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
        "script-src * 'unsafe-inline' 'unsafe-eval'; "
        "style-src * 'unsafe-inline'; "
        "img-src * data: blob:; "
        "font-src * data:; "
        "connect-src *; "
        "frame-src *; "
    )
    
    if is_https:
        csp += "upgrade-insecure-requests; "
    
    response.headers['Content-Security-Policy'] = csp
    
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    if is_https:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
    
    return response

def get_display_token(token):
    """Returns a truncated token for display."""
    if not token:
        return "Not available"
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token retrieved (short)"

@app.route('/ui_update_access_policy/<path:hostname>', methods=['POST'])
def ui_update_access_policy(hostname):
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: UI Policy Update - Docker client unavailable."
        return redirect(url_for('status_page'))

    new_policy_type = request.form.get('access_policy_type')
    auth_email = request.form.get('auth_email', '').strip()
    
    logging.info(f"UI Request: Update Access Policy for '{hostname}' to type '{new_policy_type}' with email '{auth_email if auth_email else 'N/A'}'.")

    state_changed_locally = False
    action_status_message = f"Processing UI policy update for {hostname}..."

    with state_lock:
        current_rule = managed_rules.get(hostname)
        if not current_rule:
            logging.error(f"Rule for hostname '{hostname}' not found in managed_rules for UI update.")
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {hostname} not found."
            return redirect(url_for('status_page'))

        current_access_app_id = current_rule.get("access_app_id")
        
        desired_session_duration = request.form.get("session_duration", current_rule.get("access_session_duration", "24h"))
        desired_app_launcher_visible = request.form.get("app_launcher_visible", str(current_rule.get("access_app_launcher_visible", False))).lower() in ["true", "1", "t", "yes"]
        desired_allowed_idps_str = request.form.get("allowed_idps", current_rule.get("access_allowed_idps_str"))
        desired_auto_redirect = request.form.get("auto_redirect", str(current_rule.get("access_auto_redirect", False))).lower() in ["true", "1", "t", "yes"]
        
        desired_app_name = f"DockFlare-{hostname}"
        
        cf_access_policies = []       
        final_policy_type_for_state = new_policy_type 
        custom_rules_for_hash = None
        operation_successful = False

        if new_policy_type == "none" or new_policy_type == "public_no_policy":
            if current_access_app_id:
                logging.info(f"UI: Setting {hostname} to public. Deleting Access App {current_access_app_id}.")
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = None 
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: {hostname} Access App deleted (set to public)."
                else:
                    action_status_message = f"Error: Failed to delete Access App for {hostname}."
            else:
                if current_rule.get("access_policy_type") is not None or current_rule.get("access_app_id") is not None:
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = None
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
                action_status_message = f"Info: {hostname} set to public (no existing Access App)."
            final_policy_type_for_state = None

        elif new_policy_type == "default_tld":
            if current_access_app_id:
                logging.info(f"UI: Setting {hostname} to default_tld. Deleting Access App {current_access_app_id}.")
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: {hostname} Access App deleted (set to default_tld)."
                else:
                    action_status_message = f"Error: Failed to delete Access App for {hostname} for default_tld."
            else:
                if current_rule.get("access_policy_type") != "default_tld":
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
                action_status_message = f"Info: {hostname} set to default_tld (no existing Access App)."
            final_policy_type_for_state = "default_tld"
        
        elif new_policy_type == "bypass": 
            cf_access_policies = [{"name": "UI Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            custom_rules_for_hash = json.dumps(cf_access_policies) 
            final_policy_type_for_state = "bypass"
        
        elif new_policy_type == "authenticate_email": 
            if not auth_email:
                cloudflared_agent_state["last_action_status"] = f"Error: Email address required for 'authenticate_email' policy for {hostname}."
                return redirect(url_for('status_page'))
            cf_access_policies = [
                {"name": f"UI Allow Email {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
                {"name": "UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
            ]
            custom_rules_for_hash = json.dumps(cf_access_policies)
            final_policy_type_for_state = "authenticate_email"
                
        if new_policy_type in ["bypass", "authenticate_email"]: 
            if not cf_access_policies: 
                logging.error(f"UI: No policies defined for {hostname} with type {new_policy_type} but expected. Aborting.")
                cloudflared_agent_state["last_action_status"] = f"Error: Internal - No policies for {new_policy_type}."
                return redirect(url_for('status_page'))
            
            new_config_hash = generate_access_app_config_hash(
                final_policy_type_for_state, 
                desired_session_duration, 
                desired_app_launcher_visible,
                desired_allowed_idps_str, 
                desired_auto_redirect,
                custom_access_rules_str=custom_rules_for_hash
            )
            allowed_idps_list_for_app = [idp.strip() for idp in desired_allowed_idps_str.split(',') if idp.strip()] if desired_allowed_idps_str else None

            if current_access_app_id:
                if current_rule.get("access_policy_type") != final_policy_type_for_state or \
                   current_rule.get("access_app_config_hash") != new_config_hash:
                    logging.info(f"UI: Attempting to update Access App. ID: {current_access_app_id}, Target Name: {desired_app_name}, Target Policy: {final_policy_type_for_state}")
                    updated_app = update_cloudflare_access_application(
                        current_access_app_id, hostname, desired_app_name,
                        desired_session_duration, desired_app_launcher_visible,
                        [hostname], cf_access_policies, allowed_idps_list_for_app, desired_auto_redirect
                    )
                    if updated_app:
                        current_rule["access_app_id"] = updated_app.get("id") 
                        current_rule["access_policy_type"] = final_policy_type_for_state
                        current_rule["access_app_config_hash"] = new_config_hash
                        state_changed_locally = True
                        operation_successful = True
                        action_status_message = f"Success: Access Policy for {hostname} updated to {final_policy_type_for_state}."
                    else:
                        action_status_message = f"Error: Failed to update Access App for {hostname}."
                else:
                    operation_successful = True 
                    action_status_message = f"Info: Access Policy for {hostname} already matched UI selection."
            else: 
                logging.info(f"UI: Attempting to create Access App. Target Name: {desired_app_name}, Target Policy: {final_policy_type_for_state}")
                created_app = create_cloudflare_access_application(
                    hostname, desired_app_name,
                    desired_session_duration, desired_app_launcher_visible,
                    [hostname], cf_access_policies, allowed_idps_list_for_app, desired_auto_redirect
                )
                if created_app and created_app.get("id"):
                    current_rule["access_app_id"] = created_app.get("id")
                    current_rule["access_policy_type"] = final_policy_type_for_state
                    current_rule["access_app_config_hash"] = new_config_hash
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: Access Policy for {hostname} created as {final_policy_type_for_state}."
                else:
                    action_status_message = f"Error: Failed to create Access App for {hostname}."
        
        if operation_successful:
            if not current_rule.get("access_policy_ui_override", False):
                 logging.info(f"Access policy for {hostname} is now UI-managed due to UI interaction.")
                 state_changed_locally = True 
            current_rule["access_policy_ui_override"] = True
        else:
            logging.warning(f"UI operation for {hostname} failed or no effective change made that requires API action. Override flag status based on prior state or this action's success.")

        if state_changed_locally:
            save_state()
    
    cloudflared_agent_state["last_action_status"] = action_status_message
    return redirect(url_for('status_page'))

@app.route('/tunnel-dns-records/<tunnel_id>')
def tunnel_dns_records(tunnel_id):
    if not tunnel_id:
        return jsonify({"error": "Tunnel ID is required"}), 400

    all_found_dns_records = []
    
    zone_ids_to_scan = set()

    if CF_ZONE_ID: 
        zone_ids_to_scan.add(CF_ZONE_ID)

    for zone_name in TUNNEL_DNS_SCAN_ZONE_NAMES: 
        resolved_zone_id = get_zone_id_from_name(zone_name) 
        if resolved_zone_id:
            zone_ids_to_scan.add(resolved_zone_id)
        else:
            logging.warning(f"Could not resolve Zone ID for configured scan name: {zone_name}")
    
    if not zone_ids_to_scan:
        logging.warning(f"No Zone IDs configured or resolved for DNS scan for tunnel {tunnel_id}.")

        return jsonify({"dns_records": [], "message": "No zones configured for DNS scan."})

    for zone_id in zone_ids_to_scan:
        records_in_zone = get_dns_records_for_tunnel(zone_id, tunnel_id)
        if records_in_zone: 

            all_found_dns_records.extend(records_in_zone)
    
    all_found_dns_records.sort(key=lambda r: r.get("name", "").lower())
    
    logging.info(f"Found {len(all_found_dns_records)} DNS records for tunnel {tunnel_id} across {len(zone_ids_to_scan)} zones.")
    return jsonify({"dns_records": all_found_dns_records})

@app.route('/')
def status_page():
    """Renders the main status dashboard page."""
    
    rules_for_template = {}
    template_tunnel_state = {}
    template_agent_state = {}
    initialization_status = {} 

    tld_policy_exists = False
    account_email_for_tld = None
    relevant_zone_name_for_tld_policy = None

    with state_lock: 
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

        
        initialization_status = {
            "complete": template_tunnel_state.get("id") is not None, 
            "in_progress": template_tunnel_state.get("status_message", "").startswith("Initializing") 
        }

        
        if CF_ZONE_ID and docker_client: 
            cached_zone_name = None
            if zone_id_cache: 
                for name, data in zone_id_cache.items():
                    if isinstance(data, tuple) and data[0] == CF_ZONE_ID:
                        cached_zone_name = name
                        break

            if cached_zone_name:
                relevant_zone_name_for_tld_policy = cached_zone_name
                logging.debug(f"Using cached zone name '{relevant_zone_name_for_tld_policy}' for CF_ZONE_ID '{CF_ZONE_ID}' for TLD check.")
            elif TUNNEL_NAME and TUNNEL_NAME.count('.') >= 1:
                parts = TUNNEL_NAME.split('.')
                potential_zone_name = f"{parts[-2]}.{parts[-1]}"
                
                resolved_id_for_tunnel_zone = get_zone_id_from_name(potential_zone_name) 
                if CF_ZONE_ID == resolved_id_for_tunnel_zone:
                     relevant_zone_name_for_tld_policy = potential_zone_name
                     logging.debug(f"Derived zone name '{relevant_zone_name_for_tld_policy}' from TUNNEL_NAME and it matches CF_ZONE_ID.")
                
            if relevant_zone_name_for_tld_policy:
                
                tld_policy_exists = check_for_tld_access_policy(relevant_zone_name_for_tld_policy)
                if not tld_policy_exists: 
                    account_email_for_tld = get_cloudflare_account_email()
            else:
                logging.info("Relevant zone name for TLD policy check could not be determined (CF_ZONE_ID might be set, but its name is not cached or derivable). Skipping TLD policy UI elements.")
        else:
            if not CF_ZONE_ID:
                logging.debug("CF_ZONE_ID not set, TLD policy assistant feature will not be active.")
            if not docker_client:
                logging.debug("Docker client not available, TLD policy assistant API calls cannot be made.")
        
    display_token = get_display_token(template_tunnel_state.get("token")) 
    docker_available = docker_client is not None
    external_cloudflared = USE_EXTERNAL_CLOUDFLARED
    external_tunnel_id = EXTERNAL_TUNNEL_ID

    all_account_tunnels_list = get_all_account_cloudflare_tunnels() 

    return render_template('status_page.html',
                        tunnel_state=template_tunnel_state,
                        agent_state=template_agent_state,
                        initialization=initialization_status,
                        display_token=display_token,
                        cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                        docker_available=docker_available,
                        external_cloudflared=external_cloudflared,
                        external_tunnel_id=external_tunnel_id,
                        rules=rules_for_template,
                        all_account_tunnels=all_account_tunnels_list,
                        CF_ACCOUNT_ID_CONFIGURED=bool(CF_ACCOUNT_ID), 
                        ACCOUNT_ID_FOR_DISPLAY=CF_ACCOUNT_ID if CF_ACCOUNT_ID else "Not Configured",
                        relevant_zone_name_for_tld_policy=relevant_zone_name_for_tld_policy,
                        tld_policy_exists=tld_policy_exists,
                        account_email_for_tld=account_email_for_tld,
                        CF_ZONE_ID_CONFIGURED=bool(CF_ZONE_ID) 
                        )

@app.route('/revert_access_policy_to_labels/<path:hostname>', methods=['POST'])
def revert_access_policy_to_labels(hostname):
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: Revert Policy - Docker client unavailable."
        return redirect(url_for('status_page'))

    action_status_message = f"Attempting to revert Access Policy for '{hostname}' to label configuration..."
    logging.info(action_status_message)
    
    app_id_to_delete_if_any = None
    state_changed_for_revert = False

    with state_lock:
        current_rule = managed_rules.get(hostname)

        if not current_rule:
            action_status_message = f"Error: Rule for '{hostname}' not found during revert attempt."
            logging.error(action_status_message)
            cloudflared_agent_state["last_action_status"] = action_status_message
            return redirect(url_for('status_page'))

        if not current_rule.get("access_policy_ui_override", False):
            action_status_message = f"Info: Access Policy for '{hostname}' is already managed by labels. No action taken."
            logging.info(action_status_message)
            cloudflared_agent_state["last_action_status"] = action_status_message
            return redirect(url_for('status_page'))

        app_id_to_delete_if_any = current_rule.get("access_app_id")

        current_rule["access_policy_ui_override"] = False
        current_rule["access_app_id"] = None
        current_rule["access_policy_type"] = "pending_label_sync" 
        current_rule["access_app_config_hash"] = None
        state_changed_for_revert = True
        
        if state_changed_for_revert:
            save_state()
            logging.info(f"State for '{hostname}' updated to remove UI override. Awaiting label reprocessing.")

    if app_id_to_delete_if_any:
        logging.info(f"Reverting policy for '{hostname}': Deleting previously UI-managed Access App ID '{app_id_to_delete_if_any}'.")
        if delete_cloudflare_access_application(app_id_to_delete_if_any):
            action_status_message = f"Access Policy for '{hostname}' reverted. UI-managed app deleted. Label config will apply on next reconciliation/restart."
        else:
            action_status_message = f"Access Policy for '{hostname}' reverted. Failed to delete UI-managed app '{app_id_to_delete_if_any}'. Label config will apply on next reconciliation/restart."
            logging.warning(action_status_message)
    else:
        action_status_message = f"Access Policy for '{hostname}' reverted. No specific UI-managed app to delete. Label config will apply on next reconciliation/restart."

    logging.info(f"Triggering reconciliation after reverting policy for '{hostname}' to apply label settings.")
    reconcile_state() 
    action_status_message += " Reconciliation triggered."

    cloudflared_agent_state["last_action_status"] = action_status_message
    logging.info(action_status_message)
    return redirect(url_for('status_page'))

@app.context_processor
def inject_protocol():
    """Inject protocol info into all templates with more reliable detection."""
    
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    
    
    is_https = forwarded_proto == 'https' or request.is_secure
    
    
    base_url = f"{'https' if is_https else 'http'}://{request.host}"
    
    
    request_scheme = request.scheme
    
    return {
        'protocol': 'https' if is_https else 'http',
        'is_https': is_https,
        'base_url': base_url,
        'host': request.host,
        'request_scheme': request_scheme
    }

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
    if request.method != 'POST':
    
        logging.warning(f"GET request to /force_delete_rule/{hostname}. Redirecting. Should be POST.")
        return redirect(url_for('status_page'))

    logging.info(f"UI request: Force delete rule for hostname: {hostname}")
    rule_removed_from_state = False
    dns_delete_success = False
    access_app_delete_success = False
    zone_id_for_delete = None
    access_app_id_for_delete = None

    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details:
            zone_id_for_delete = rule_details.get("zone_id")
            access_app_id_for_delete = rule_details.get("access_app_id")
            logging.info(f"Found rule for {hostname} with Zone ID: {zone_id_for_delete} and Access App ID: {access_app_id_for_delete}")
        else:
            logging.warning(f"Rule {hostname} not found in state during force delete. Attempting DNS delete in default zone ID ({CF_ZONE_ID}) if available. Access App cannot be determined.")
            zone_id_for_delete = CF_ZONE_ID
    

    effective_tunnel_id = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID
    
    
    if zone_id_for_delete and effective_tunnel_id:
        logging.info(f"Attempting immediate DNS record deletion for force-deleted rule: {hostname} in zone {zone_id_for_delete} using tunnel {effective_tunnel_id}")
        dns_delete_success = delete_cloudflare_dns_record(zone_id_for_delete, hostname, effective_tunnel_id)
        if not dns_delete_success:
            logging.error(f"Failed immediate DNS delete for {hostname} in zone {zone_id_for_delete}.")
    elif not zone_id_for_delete:
        logging.error(f"Cannot delete DNS for {hostname}: Zone ID could not be determined.")
    elif not effective_tunnel_id:
        logging.error(f"Cannot delete DNS for {hostname}: Missing effective Tunnel ID.")

    
    if access_app_id_for_delete:
        logging.info(f"Attempting immediate Access Application deletion for force-deleted rule: {hostname}, App ID: {access_app_id_for_delete}")
        access_app_delete_success = delete_cloudflare_access_application(access_app_id_for_delete)
        if not access_app_delete_success:
            logging.error(f"Failed immediate Access App delete for {hostname}, App ID: {access_app_id_for_delete}.")
    else:
        logging.info(f"No Access App ID associated with rule {hostname} for force deletion.")
        access_app_delete_success = True 

    
    with state_lock:
        if hostname in managed_rules:
            logging.info(f"Force deleting rule for {hostname} from local state.")
            del managed_rules[hostname]
            rule_removed_from_state = True
            save_state()
        else:
            logging.warning(f"Rule '{hostname}' was already removed from state when force delete requested.")
            rule_removed_from_state = True 

    status_msg_parts = [f"Rule for {hostname}"]
    if rule_removed_from_state:
        status_msg_parts.append("removed from local state.")
    else:
        status_msg_parts.append("not found in local state.")
    
    if zone_id_for_delete: 
        status_msg_parts.append(f"DNS delete: {'successful' if dns_delete_success else 'failed/skipped'}.")
    
    if access_app_id_for_delete is not None: 
        status_msg_parts.append(f"Access App delete: {'successful' if access_app_delete_success else 'failed'}.")
    else:
        status_msg_parts.append("No associated Access App to delete.")

    if rule_removed_from_state: 
        if not USE_EXTERNAL_CLOUDFLARED:
            logging.info(f"Triggering Cloudflare tunnel config update after force deleting {hostname}.")
            if update_cloudflare_config():
                logging.info(f"CF tunnel config update successful after force deleting {hostname}.")
                status_msg_parts.append("Tunnel config updated.")
            else:
                logging.error(f"CRITICAL: State updated after force delete of {hostname}, but subsequent tunnel config update FAILED!")
                status_msg_parts.append("Tunnel config update FAILED!")
                cloudflared_agent_state["last_action_status"] = f"Error: Removed {hostname} (DNS: {dns_delete_success}, Access: {access_app_delete_success}), but FAILED tunnel config update! Reconciliation needed."
        else:
            
            logging.info(f"External mode: Skipping tunnel config update for force-deleted rule {hostname}.")
            status_msg_parts.append("Tunnel config unchanged (external mode).")
    
    final_status_msg = " ".join(status_msg_parts)
    cloudflared_agent_state["last_action_status"] = final_status_msg
    logging.info(final_status_msg)

    time.sleep(0.2) 
    return redirect(url_for('status_page'))

@app.route('/stream-logs')
def stream_logs():
    """Streams log messages using Server-Sent Events with proper WSGI compatibility."""
    client_id = f"client-{random.randint(1000, 9999)}"
    logging.info(f"Log stream client {client_id} connected.")
    
    def event_stream():
        """Generate events without accessing Flask request context."""
        try:
            
            yield f"data: --- Log stream connected (client {client_id}) ---\n\n"
            yield f"data: heartbeat\n\n"
                        
            last_heartbeat = time.time()
            heartbeat_interval = 2  
                        
            while True:
                try:
            
                    current_time = time.time()
                    if current_time - last_heartbeat > heartbeat_interval:
                        yield f"data: heartbeat\n\n"
                        last_heartbeat = current_time
                        continue
                    
            
                    log_entry = log_queue.get(timeout=0.25)
                    yield f"data: {log_entry}\n\n"
                except queue.Empty:
            
                    yield f": keepalive\n\n"
                    time.sleep(0.1)
        
        except GeneratorExit:
            logging.info(f"Log stream client {client_id} disconnected.")
        except Exception as e:
            logging.error(f"Error in log stream for {client_id}: {e}", exc_info=True)
        finally:
            logging.info(f"Log stream for client {client_id} ended.")
        
    response = Response(event_stream(), mimetype='text/event-stream')
    
    
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'
        
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    
    return response

@app.route('/ui/manual-rules/add', methods=['POST'])
def ui_add_manual_rule():
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to add manual rule. Docker client unavailable."
        return redirect(url_for('status_page'))
    if not tunnel_state.get("id"):
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to add manual rule. Tunnel not initialized."
        return redirect(url_for('status_page'))

    hostname = request.form.get('manual_hostname', '').strip()
    service_input = request.form.get('manual_service', '').strip() 
    zone_name = request.form.get('manual_zone_name', '').strip() 
    no_tls_verify = request.form.get('manual_no_tls_verify') == 'on'

    if not hostname or not service_input:
        cloudflared_agent_state["last_action_status"] = "Error: Hostname and Service are required for manual rule."
        return redirect(url_for('status_page'))

    if not is_valid_hostname(hostname):
        cloudflared_agent_state["last_action_status"] = f"Error: Invalid hostname provided for manual rule: {hostname}"
        return redirect(url_for('status_page'))

    processed_service_for_cf = ""
    try:
        parsed_url = urlparse(service_input)
        if not parsed_url.scheme or not parsed_url.netloc:

            raise ValueError("Service URL must include scheme (e.g., http:// or https://) and host/IP.")

        processed_service_for_cf = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        logging.info(f"Manual rule service input '{service_input}' processed to '{processed_service_for_cf}' for Cloudflare config.")

    except ValueError as e:
        cloudflared_agent_state["last_action_status"] = f"Error: Invalid service URL format '{service_input}': {e}"
        return redirect(url_for('status_page'))

    if not is_valid_service(processed_service_for_cf):
        cloudflared_agent_state["last_action_status"] = f"Error: Processed service URL '{processed_service_for_cf}' (from input '{service_input}') is invalid for Cloudflare."
        return redirect(url_for('status_page'))

    target_zone_id = None
    if zone_name:
        target_zone_id = get_zone_id_from_name(zone_name)
        if not target_zone_id:
            cloudflared_agent_state["last_action_status"] = f"Error: Could not find Zone ID for '{zone_name}'."
            return redirect(url_for('status_page'))
    elif CF_ZONE_ID:
        target_zone_id = CF_ZONE_ID
    else:
        cloudflared_agent_state["last_action_status"] = "Error: Zone Name required for manual rule as CF_ZONE_ID is not set."
        return redirect(url_for('status_page'))

    with state_lock:
        existing_rule_details = managed_rules.get(hostname)
        if existing_rule_details and existing_rule_details.get("source", "docker") == "docker":
            cloudflared_agent_state["last_action_status"] = f"Error: Hostname {hostname} is already managed by Docker labels. Manual rule not added/updated."
            return redirect(url_for('status_page'))
        
        if existing_rule_details:
             logging.info(f"Updating existing manual rule for {hostname} with service {processed_service_for_cf}")
        else:
             logging.info(f"Adding new manual rule for {hostname} with service {processed_service_for_cf}")

        managed_rules[hostname] = {
            "service": processed_service_for_cf,
            # "original_service_input": service_input, # Optional: display the user's full input later --- need to check on this -> on my open task list don't forget
            "container_id": None, 
            "status": "active",
            "delete_at": None,
            "zone_id": target_zone_id,
            "no_tls_verify": no_tls_verify,
            "access_app_id": existing_rule_details.get("access_app_id") if existing_rule_details else None,
            "access_policy_type": existing_rule_details.get("access_policy_type") if existing_rule_details else None,
            "access_app_config_hash": existing_rule_details.get("access_app_config_hash") if existing_rule_details else None,
            "access_policy_ui_override": existing_rule_details.get("access_policy_ui_override", False) if existing_rule_details else False,
            "source": "manual"
        }
        save_state()

    effective_tunnel_id = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID
    if not effective_tunnel_id:
        cloudflared_agent_state["last_action_status"] = f"Error: Cannot setup DNS/Tunnel for {hostname}, effective tunnel ID missing."
        return redirect(url_for('status_page'))

    if update_cloudflare_config():
        create_cloudflare_dns_record(target_zone_id, hostname, effective_tunnel_id)
        cloudflared_agent_state["last_action_status"] = f"Success: Manual rule for {hostname} (service: {processed_service_for_cf}) added/updated."
    else:
        cloudflared_agent_state["last_action_status"] = f"Error: Failed to update Cloudflare config for manual rule {hostname}. DNS record might also be affected."

    return redirect(url_for('status_page'))

@app.route('/ui/manual-rules/delete/<path:hostname>', methods=['POST'])
def ui_delete_manual_rule(hostname):
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to delete manual rule. Docker client unavailable."
        return redirect(url_for('status_page'))
    if not tunnel_state.get("id"):
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to delete manual rule. Tunnel not initialized."
        return redirect(url_for('status_page'))

    logging.info(f"UI request: Delete manual rule for hostname: {hostname}")
    
    zone_id_for_delete = None
    access_app_id_for_delete = None
    rule_existed_as_manual = False

    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details and rule_details.get("source") == "manual":
            rule_existed_as_manual = True
            zone_id_for_delete = rule_details.get("zone_id")
            access_app_id_for_delete = rule_details.get("access_app_id")
            del managed_rules[hostname]
            save_state()
        elif rule_details:
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {hostname} is not a manual rule. Cannot delete via this action."
            return redirect(url_for('status_page'))
        else:
            cloudflared_agent_state["last_action_status"] = f"Info: Manual rule for {hostname} not found to delete."
            return redirect(url_for('status_page'))

    if rule_existed_as_manual:
        effective_tunnel_id = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID
        if not effective_tunnel_id:
            cloudflared_agent_state["last_action_status"] = f"Warning: Rule {hostname} deleted from state, but DNS/Tunnel resources cannot be cleaned (missing tunnel ID)."
            return redirect(url_for('status_page'))

        if zone_id_for_delete:
            delete_cloudflare_dns_record(zone_id_for_delete, hostname, effective_tunnel_id)
        
        if access_app_id_for_delete:
            delete_cloudflare_access_application(access_app_id_for_delete)

        if update_cloudflare_config():
            cloudflared_agent_state["last_action_status"] = f"Success: Manual rule {hostname} and associated resources deleted."
        else:
            cloudflared_agent_state["last_action_status"] = f"Warning: Manual rule {hostname} deleted from state & DNS/Access attempted, but Cloudflare tunnel config update failed."
    
    return redirect(url_for('status_page'))

@app.route('/cloudflare-ping')
def cloudflare_ping():
    """Specialized ping endpoint to diagnose Cloudflare tunnel connectivity."""
    try:
    
        cf_headers = {k: v for k, v in request.headers.items() if k.lower().startswith('cf-')}
        cf_visitor = request.headers.get('Cf-Visitor', '')
      
    
        visitor_data = {}
        if cf_visitor:
            try:
                visitor_data = json.loads(cf_visitor)
            except:
                visitor_data = {"parse_error": "Invalid JSON in Cf-Visitor header"}
                

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
        

    if USE_EXTERNAL_CLOUDFLARED:
        if not tunnel_state.get("id"):
            logging.warning("External tunnel ID not available. Background tasks cannot start.")
            return threads
    else:

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


    def initialization_process():

        global background_threads
        
        logging.info("Running initialization process in background thread")
        if not docker_client:
            logging.error("Docker client unavailable for initialization. Skipping initialization tasks.")
            return
            
        initialize_tunnel()
        logging.info(f"Tunnel initialization complete. Status: {tunnel_state.get('status_message')}")
        

        if USE_EXTERNAL_CLOUDFLARED and tunnel_state.get("id"):
            logging.info("External tunnel initialized. Proceeding with initial reconciliation.")
            

            try:
                logging.info("Running initial direct container scan (non-threaded)...")
                

                max_reconciliation_time = 90  
                reconciliation_start = time.time()
                

                app.reconciliation_info = {
                    "in_progress": True,
                    "progress": 0,
                    "total_items": 0,
                    "processed_items": 0,
                    "start_time": time.time(),
                    "status": "Starting initial container scan..."
                }
                
                
                try:
                    containers = docker_client.containers.list(all=SCAN_ALL_NETWORKS)
                    container_count = len(containers)
                    logging.info(f"[Init] Found {container_count} total containers to scan")
                    
                    
                    batch_size = 2
                    processed = 0
                    
                    for i in range(0, container_count, batch_size):
                        if time.time() - reconciliation_start > max_reconciliation_time:
                            logging.warning("[Init] Initial container scan timeout")
                            break
                            
                        batch = containers[i:i+batch_size]
                        
                    
                        app.reconciliation_info["status"] = f"Initial scan: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                        app.reconciliation_info["total_items"] = container_count
                        processed += len(batch)
                        app.reconciliation_info["processed_items"] = processed
                        app.reconciliation_info["progress"] = min(100, int((processed / container_count) * 100))
                        
                        for container in batch:
                    
                            process_container_start(container)
                            
                    
                        time.sleep(1.0)
                        
                except Exception as e:
                    logging.error(f"Error during initial container processing: {e}", exc_info=True)
                
                
                app.reconciliation_info["in_progress"] = False
                app.reconciliation_info["progress"] = 100
                app.reconciliation_info["status"] = "Initial container scan complete"
                app.reconciliation_info["completed_at"] = time.time()
                
                
                logging.info("Initial container scan complete - scheduling full background reconciliation")
                threading.Timer(15, reconcile_state).start()
                
            except Exception as e:
                logging.error(f"Error during initial container scan: {e}", exc_info=True)
            
            logging.info("Initial state reconciliation complete.")
            
            background_threads.extend(run_background_tasks())
            
        elif not USE_EXTERNAL_CLOUDFLARED and tunnel_state.get("id") and tunnel_state.get("token"):
            logging.info("Tunnel initialized with ID and Token. Proceeding with initial reconciliation & agent checks.")
            
            
            try:
                logging.info("Running initial direct container scan (non-threaded)...")
                
            
                max_reconciliation_time = 90  
                reconciliation_start = time.time()
                
                
                app.reconciliation_info = {
                    "in_progress": True,
                    "progress": 0,
                    "total_items": 0,
                    "processed_items": 0,
                    "start_time": time.time(),
                    "status": "Starting initial container scan..."
                }
                
                
                try:
                    containers = docker_client.containers.list(all=SCAN_ALL_NETWORKS)
                    container_count = len(containers)
                    logging.info(f"[Init] Found {container_count} total containers to scan")
                    
                
                    batch_size = 3
                    processed = 0
                    
                    for i in range(0, container_count, batch_size):
                        if time.time() - reconciliation_start > max_reconciliation_time:
                            logging.warning("[Init] Initial container scan timeout")
                            break
                            
                        batch = containers[i:i+batch_size]
                        
                
                        app.reconciliation_info["status"] = f"Initial scan: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size}"
                        app.reconciliation_info["total_items"] = container_count
                        processed += len(batch)
                        app.reconciliation_info["processed_items"] = processed
                        app.reconciliation_info["progress"] = min(100, int((processed / container_count) * 100))
                        
                        for container in batch:
                
                            process_container_start(container)
                            
                
                        time.sleep(0.5)
                        
                except Exception as e:
                    logging.error(f"Error during initial container processing: {e}", exc_info=True)
                
                
                app.reconciliation_info["in_progress"] = False
                app.reconciliation_info["progress"] = 100
                app.reconciliation_info["status"] = "Initial container scan complete"
                app.reconciliation_info["completed_at"] = time.time()
                
                
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
            
            
            background_threads.extend(run_background_tasks())
            
        else:
            logging.warning("Tunnel not fully initialized. Skipping reconciliation, agent start, and event/cleanup tasks.")
            if not tunnel_state.get("error"):
                tunnel_state["status_message"] = "Tunnel setup incomplete (missing ID/Token)."

    
    if not docker_client:
        logging.error("Docker client unavailable at startup. Dockflare will run with limited functionality.")
        tunnel_state["status_message"] = "Error: Docker client unavailable."
        tunnel_state["error"] = "Failed to connect to Docker daemon."
        cloudflared_agent_state["container_status"] = "docker_unavailable"
        logging.warning("Flagging initialization limitations due to Docker connection failure.")
    else:
        logging.info("Docker client available. Setting up initial UI states...")
        
        tunnel_state["status_message"] = "Initializing (in progress)..."
        cloudflared_agent_state["container_status"] = "initializing"
        
    
        logging.info("Starting periodic agent status updater thread...")
        agent_status_thread = threading.Thread(target=periodic_agent_status_updater, name="AgentStatusUpdater", daemon=True)
        agent_status_thread.start()
        
    
        init_thread = threading.Thread(
            target=initialization_process,
            name="InitializationProcess",
            daemon=True
        )
        init_thread.start()

    
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