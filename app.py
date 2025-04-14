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
# Updated import: Added render_template, flash, session (flash might be useful later)
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, session
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
# CF_ZONE_ID is the *default* zone ID
CF_ZONE_ID = os.getenv('CF_ZONE_ID')
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}
logging.info(f"[DEBUG] CF_HEADERS created: Authorization Header starts with 'Bearer {str(CF_API_TOKEN)[:5]}...'")

# App Config
LABEL_PREFIX = os.getenv('LABEL_PREFIX', 'cloudflare.tunnel')
# Default grace period now 2 hours (7200 seconds), can be overridden by env var or state file
GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 7200))
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 300))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')

# Cloudflared Agent Config
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"
CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net')

# Environment Variable Checks
if not CF_API_TOKEN or not TUNNEL_NAME or not CF_ACCOUNT_ID:
    logging.error("FATAL: Missing required environment variables (CF_API_TOKEN, TUNNEL_NAME, CF_ACCOUNT_ID)")
    sys.exit(1)
if not CF_ZONE_ID:
    logging.warning("CF_ZONE_ID environment variable is not set. DNS management will ONLY work if containers specify 'cloudflare.tunnel.zonename' label or rules are added manually with a zone name.")


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
managed_rules = {} # Stores rule details including 'zone_id' and 'type' ('docker' or 'manual')
zone_id_cache = {} # Cache for zone name -> zone ID lookups
state_lock = threading.Lock()
stop_event = threading.Event()


# --- load_state ---
# UPDATED: Handle loading grace period and default rule type
def load_state():
    global managed_rules
    global GRACE_PERIOD_SECONDS

    current_default_grace_period = GRACE_PERIOD_SECONDS
    logging.info(f"Initial default GRACE_PERIOD_SECONDS: {current_default_grace_period}")
    state_dir = os.path.dirname(STATE_FILE_PATH)
    if not os.path.exists(state_dir):
        try: os.makedirs(state_dir, exist_ok=True); logging.info(f"Created state dir: {state_dir}")
        except OSError as e: logging.error(f"FATAL: Cannot create state dir {state_dir}: {e}."); managed_rules = {}; return
    if not os.path.exists(STATE_FILE_PATH):
        logging.info(f"State file '{STATE_FILE_PATH}' not found."); managed_rules = {}; return
    try:
        with open(STATE_FILE_PATH, 'r') as f: loaded_data = json.load(f)
        # Load Settings
        loaded_settings = loaded_data.get("settings", {}); saved_grace_period = loaded_settings.get("grace_period_seconds")
        if saved_grace_period is not None:
            try:
                saved_grace_period_int = int(saved_grace_period)
                if saved_grace_period_int >= 0:
                     GRACE_PERIOD_SECONDS = saved_grace_period_int
                     logging.info(f"Loaded GRACE_PERIOD_SECONDS from state: {GRACE_PERIOD_SECONDS}")
                else:
                    logging.warning(f"Invalid grace period in state: {saved_grace_period}. Using default: {current_default_grace_period}")
                    GRACE_PERIOD_SECONDS = current_default_grace_period
            except (ValueError, TypeError):
                 logging.warning(f"Invalid grace period type in state: {saved_grace_period}. Using default: {current_default_grace_period}")
                 GRACE_PERIOD_SECONDS = current_default_grace_period
        else:
            logging.info("No grace period in state settings. Using default.")
            GRACE_PERIOD_SECONDS = current_default_grace_period
        # Load Rules
        loaded_rules = loaded_data.get("rules", {}); parsed_rules = {}
        for hostname, rule in loaded_rules.items():
            if rule.get("delete_at") and isinstance(rule.get("delete_at"), str):
                try:
                     dt_str = rule["delete_at"]
                     if dt_str.endswith('Z'): rule["delete_at"] = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                     else: dt = datetime.fromisoformat(dt_str); rule["delete_at"] = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                except ValueError: logging.warning(f"Could not parse delete_at for {hostname}: {rule['delete_at']}. Setting None."); rule["delete_at"] = None
            elif not isinstance(rule.get("delete_at"), datetime): rule["delete_at"] = None
            if "zone_id" not in rule: logging.warning(f"Rule {hostname} missing 'zone_id'."); rule["zone_id"] = None
            if "type" not in rule: logging.warning(f"Rule {hostname} missing 'type', defaulting to 'docker'."); rule["type"] = "docker"
            parsed_rules[hostname] = rule
        managed_rules = parsed_rules
        logging.info(f"Loaded state: {len(managed_rules)} rules, Grace={GRACE_PERIOD_SECONDS}s")
    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Error loading state: {e}. Starting fresh.", exc_info=True); managed_rules = {}; GRACE_PERIOD_SECONDS = current_default_grace_period


# --- save_state ---
# UPDATED: Save structured state with settings and rules
def save_state():
    state_to_save = { "settings": { "grace_period_seconds": GRACE_PERIOD_SECONDS }, "rules": {} }
    for hostname, rule in managed_rules.items():
        rule_copy = rule.copy()
        if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
            rule_copy["delete_at"] = rule_copy["delete_at"].astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        if "zone_id" not in rule_copy: rule_copy["zone_id"] = None
        if "type" not in rule_copy: rule_copy["type"] = "docker"
        state_to_save["rules"][hostname] = rule_copy
    try:
        state_dir = os.path.dirname(STATE_FILE_PATH)
        if not os.path.exists(state_dir):
            try: os.makedirs(state_dir, exist_ok=True); logging.info(f"Created dir {state_dir} for state.")
            except OSError as e: logging.error(f"Cannot create state dir {state_dir}: {e}. Save failed."); return
        temp_file_path = STATE_FILE_PATH + ".tmp"
        with open(temp_file_path, 'w') as f: json.dump(state_to_save, f, indent=2)
        os.replace(temp_file_path, STATE_FILE_PATH)
        logging.debug(f"Saved state ({len(managed_rules)} rules, grace={GRACE_PERIOD_SECONDS}s) to {STATE_FILE_PATH}")
    except (IOError, OSError) as e: logging.error(f"Error saving state: {e}", exc_info=True)


# --- cf_api_request ---
def cf_api_request(method, endpoint, json_data=None, params=None):
    url = f"{CF_API_BASE_URL}{endpoint}"; error_msg = None
    try:
        request_headers = CF_HEADERS.copy(); logging.info(f"API Request: {method} {url} P={params} D={json_data}")
        response = requests.request(method, url, headers=request_headers, json=json_data, params=params, timeout=30)
        response.raise_for_status(); logging.info(f"API Response Status: {response.status_code}")
        if response.status_code == 204 or not response.content: return {"success": True, "result": None}
        try:
            response_data = response.json(); logging.debug(f"API Response Body (500): {str(response_data)[:500]}")
            if isinstance(response_data, dict) and 'success' in response_data:
                 if response_data['success']: return response_data
                 else:
                      cf_errors = response_data.get('errors', [])
                      if cf_errors and isinstance(cf_errors[0], dict): error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown')}"
                      else: error_msg = f"API fail, no details: {response_data}"
                      logging.error(f"API Fail ({method} {url}): {error_msg} - Full: {cf_errors}"); raise requests.exceptions.RequestException(error_msg, response=response)
            else: logging.warning(f"API JSON unexpected format: {str(response_data)[:200]}"); raise requests.exceptions.RequestException("Unexpected JSON format", response=response)
        except json.JSONDecodeError: logging.error(f"API invalid JSON: {response.text[:200]}"); raise requests.exceptions.RequestException("Invalid JSON response", response=response)
    except requests.exceptions.RequestException as e:
        if error_msg is None:
            logging.error(f"API Request Failed: {method} {url}"); error_msg = f"Request Exception: {e}"
            if e.response is not None:
                try: error_data = e.response.json(); logging.error(f"Response Body: {error_data}"); cf_errors = error_data.get('errors', []); error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown')}" if cf_errors and isinstance(cf_errors[0], dict) else f"HTTP {e.response.status_code} - {e.response.text[:100]}"
                except: error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
            else: logging.error(f"No response received: {e}")
        if "cfd_tunnel" in endpoint and tunnel_state.get("id") is None and "token" not in endpoint: tunnel_state["error"] = error_msg
        raise requests.exceptions.RequestException(error_msg, response=e.response)

# --- get_zone_id_from_name ---
def get_zone_id_from_name(zone_name):
    """Retrieves the Zone ID for a given zone name using the Cloudflare API."""
    global zone_id_cache
    if not zone_name: logging.warning("get_zone_id: empty zone_name."); return None
    with state_lock: cached_id = zone_id_cache.get(zone_name)
    if cached_id: logging.debug(f"Zone ID '{zone_name}' from cache: {cached_id}"); return cached_id
    logging.info(f"Zone ID '{zone_name}' not cached. Querying API..."); endpoint = "/zones"; params = {"name": zone_name, "status": "active"}
    try:
        response_data = cf_api_request("GET", endpoint, params=params); results = response_data.get("result", [])
        if results and len(results) == 1:
            zone_id = results[0].get("id"); zone_actual_name = results[0].get("name")
            if zone_id and zone_actual_name == zone_name:
                logging.info(f"Found Zone ID for '{zone_name}': {zone_id}"); with state_lock: zone_id_cache[zone_name] = zone_id; return zone_id
            else: logging.error(f"API name mismatch for zone '{zone_name}': {results[0]}"); return None
        elif results: logging.error(f"Multiple zones match name '{zone_name}'. Ambiguous."); return None
        else: logging.warning(f"No active zone found matching '{zone_name}'."); return None
    except requests.exceptions.RequestException as e: logging.error(f"API error zone lookup '{zone_name}': {e}"); return None
    except Exception as e: logging.error(f"Unexpected error zone lookup '{zone_name}': {e}", exc_info=True); return None

# --- find_tunnel_via_api / get_tunnel_token_via_api / create_tunnel_via_api ---
def find_tunnel_via_api(name): # ... (implementation as before) ...
def get_tunnel_token_via_api(tunnel_id): # ... (implementation as before) ...
def create_tunnel_via_api(name): # ... (implementation as before) ...

# --- initialize_tunnel ---
def initialize_tunnel(): # ... (implementation as before) ...

# --- get_current_cf_config / find_dns_record_id / create_cloudflare_dns_record / delete_cloudflare_dns_record ---
def get_current_cf_config(): # ... (implementation as before) ...
def find_dns_record_id(zone_id, hostname, tunnel_id): # ... (implementation as before) ...
def create_cloudflare_dns_record(zone_id, hostname, tunnel_id): # ... (implementation as before) ...
def delete_cloudflare_dns_record(zone_id, hostname, tunnel_id): # ... (implementation as before) ...

# --- update_cloudflare_config ---
def update_cloudflare_config(): # ... (implementation as before) ...

# --- process_container_start ---
def process_container_start(container): # ... (implementation as before, setting type='docker') ...

# --- schedule_container_stop ---
def schedule_container_stop(container_id): # ... (implementation as before, checking type='docker') ...

# --- docker_event_listener ---
def docker_event_listener(): # ... (implementation as before) ...

# --- cleanup_expired_rules ---
def cleanup_expired_rules(): # ... (implementation as before) ...

# --- reconcile_state ---
# UPDATED: Handle 'type' field and CORRECTED syntax error in DNS check loop
def reconcile_state():
    if not docker_client: logging.warning("Reconcile: Docker client unavailable."); return
    if not tunnel_state.get("id"): logging.warning("Reconcile: Tunnel not initialized."); return
    logging.info("Starting state reconciliation..."); needs_cf_update = False; state_changed_locally = False
    try:
        # --- Get Docker State ---
        running_labeled_containers = {}
        try: containers = docker_client.containers.list(sparse=False); logging.debug(f"[Reconcile] Found {len(containers)} running.")
        except (APIError, requests.exceptions.ConnectionError) as e: logging.error(f"[Reconcile] Docker error list: {e}. Abort."); return
        for c in containers:
             try:
                 labels = c.labels; cid = c.id; cname = c.name
                 enabled = labels.get(f"{LABEL_PREFIX}.enable", "false").lower() in ["true", "1", "t", "yes"]
                 hn = labels.get(f"{LABEL_PREFIX}.hostname"); svc = labels.get(f"{LABEL_PREFIX}.service"); zn = labels.get(f"{LABEL_PREFIX}.zonename")
                 if enabled and hn and svc:
                     if not re.match(r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$", hn): continue
                     if not (re.match(r"^(https?|tcp|unix)://", svc) or re.match(r"^[a-zA-Z0-9._-]+:\d+$", svc)): continue
                     if hn in running_labeled_containers: logging.warning(f"[Reconcile] Dup hostname {hn} on {cname} & {running_labeled_containers[hn]['container_name']}.")
                     running_labeled_containers[hn] = {"service": svc, "container_id": cid, "container_name": cname, "zone_name": zn }
             except (NotFound, APIError) as e: logging.warning(f"[Reconcile] Error proc container {c.id[:12]}: {e}. Skip.")
        logging.info(f"[Reconcile] Found {len(running_labeled_containers)} valid labeled running containers.")
        # --- Compare ---
        with state_lock:
            logging.debug("[Reconcile] Acquired lock."); now_utc = datetime.now(timezone.utc)
            managed_hostnames = set(managed_rules.keys()); running_hostnames = set(running_labeled_containers.keys()); hostnames_dns_check = []
            # 1. Check running containers
            for hostname, running_details in running_labeled_containers.items():
                target_zone_id = None; zone_name = running_details.get("zone_name")
                if zone_name: target_zone_id = get_zone_id_from_name(zone_name); # ... (handle lookup failure) ...
                else: target_zone_id = CF_ZONE_ID
                if not target_zone_id: logging.error(f"[Reconcile] Skip {hostname}: No valid Zone ID."); continue
                rule_data = {"service": running_details["service"], "container_id": running_details["container_id"], "status": "active", "delete_at": None, "zone_id": target_zone_id, "type": "docker"}
                if hostname in managed_rules:
                    rule = managed_rules[hostname]; zone_id_changed = rule.get("zone_id") != target_zone_id
                    if rule.get("status") == "pending_deletion": logging.info(f"[Reconcile] Reactivating {hostname}."); rule.update(rule_data); state_changed_locally=True; needs_cf_update=True; hostnames_dns_check.append(hostname)
                    elif rule.get("status") == "active":
                        if rule.get("service") != running_details["service"] or rule.get("zone_id") != target_zone_id: needs_cf_update = True
                        if rule.get("service") != running_details["service"] or rule.get("container_id") != running_details["container_id"] or rule.get("zone_id") != target_zone_id: logging.info(f"[Reconcile] Updating active rule {hostname}."); rule.update(rule_data); state_changed_locally = True
                        if zone_id_changed: hostnames_dns_check.append(hostname)
                    elif rule.get("type") == "manual": logging.debug(f"[Reconcile] Docker running for manual rule {hostname}. Ignore.")
                else: logging.info(f"[Reconcile] Adding new docker rule for {hostname}."); managed_rules[hostname] = rule_data; state_changed_locally=True; needs_cf_update=True; hostnames_dns_check.append(hostname)
            # 2. Check managed rules vs running
            for hostname in list(managed_hostnames):
                if hostname not in running_hostnames:
                     if hostname in managed_rules:
                         rule = managed_rules[hostname]
                         if rule.get("status") == "active" and rule.get("type") == "docker": logging.info(f"[Reconcile] Docker rule {hostname} active but container gone. Scheduling delete."); rule["status"] = "pending_deletion"; rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS); state_changed_locally = True
                         elif rule.get("status") == "active" and rule.get("type") == "manual": logging.debug(f"[Reconcile] Manual rule {hostname} active, no container. OK.")
            # 3. Compare local state vs CF state
            current_cf_config = get_current_cf_config()
            if current_cf_config is not None:
                cf_hostnames = {r.get("hostname") for r in current_cf_config.get("ingress", []) if r.get("hostname") and r.get("service") != "http_status:404"}
                active_managed = {hn for hn, d in managed_rules.items() if d.get("status") == "active"}
                if cf_hostnames != active_managed: logging.warning(f"[Reconcile] Mismatch: Managed={active_managed} vs CF={cf_hostnames}!"); needs_cf_update = True
            else: logging.error("[Reconcile] Failed CF config fetch for compare.")
            if state_changed_locally: logging.info("[Reconcile] Saving state changes."); save_state()
            logging.debug("[Reconcile] Releasing lock.")
        # --- Trigger Updates ---
        if needs_cf_update:
            logging.info("[Reconcile] Triggering CF tunnel update.");
            if update_cloudflare_config():
                 if hostnames_dns_check:
                      logging.info(f"[Reconcile] Checking DNS for: {hostnames_dns_check}")
                      for hn in hostnames_dns_check:
                           # --- SYNTAX ERROR FIXED HERE ---
                           rule = None # Initialize rule variable
                           with state_lock: # Get rule details safely under lock
                               rule = managed_rules.get(hn)
                           # --- END FIX ---
                           if rule and rule.get("zone_id") and tunnel_state.get("id"):
                                if not create_cloudflare_dns_record(rule["zone_id"], hn, tunnel_state["id"]):
                                     logging.error(f"[Reconcile] DNS check/create failed for {hn} in {rule['zone_id']}")
                           else:
                                logging.error(f"[Reconcile] Cannot check/create DNS for {hn}: missing required data (rule details, zone ID, or tunnel ID).")
            else: logging.error("[Reconcile] Failed CF update. DNS checks skipped.")
        elif state_changed_locally: logging.info("[Reconcile] Local state only changes.")
        else: logging.info("[Reconcile] No changes needed.")
    except Exception as e: logging.error(f"Unexpected reconcile error: {e}", exc_info=True)
    finally: logging.info("Reconciliation complete.")

# --- get_cloudflared_container / update_cloudflared_container_status / ensure_docker_network_exists ---
def get_cloudflared_container(): # ... (implementation as before) ...
def update_cloudflared_container_status(): # ... (implementation as before) ...
def ensure_docker_network_exists(network_name): # ... (implementation as before) ...

# --- start_cloudflared_container / stop_cloudflared_container ---
def start_cloudflared_container(): # ... (implementation as before) ...
def stop_cloudflared_container(): # ... (implementation as before) ...

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- get_display_token ---
def get_display_token(token): # ... (implementation as before) ...

# --- status_page ---
@app.route('/')
def status_page(): # ... (implementation as before, passing current_grace_period_seconds) ...

# --- start_tunnel / stop_tunnel ---
@app.route('/start', methods=['POST'])
def start_tunnel(): # ... (implementation as before) ...
@app.route('/stop', methods=['POST'])
def stop_tunnel(): # ... (implementation as before) ...

# --- force_delete_rule ---
@app.route('/force_delete/<hostname>', methods=['POST'])
def force_delete_rule(hostname): # ... (implementation as before) ...

# --- update_settings ---
@app.route('/update_settings', methods=['POST'])
def update_settings(): # ... (implementation as before) ...

# --- add_manual_rule ---
@app.route('/add_manual_rule', methods=['POST'])
def add_manual_rule(): # ... (implementation as before) ...

# --- run_background_tasks ---
def run_background_tasks(): # ... (implementation as before) ...

# --- Main Execution ---
if __name__ == '__main__':
    # ... (implementation as before) ...
    logging.info("-" * 52); logging.info("--- DockFlare Tunnel Manager Starting ---"); logging.info("-" * 52)
    load_state(); logging.info("State loaded.") # Includes grace period load
    event_thread = None; cleanup_thread = None
    if not CF_API_TOKEN or not TUNNEL_NAME or not CF_ACCOUNT_ID: logging.error("FATAL: Missing required env vars."); sys.exit(1)
    if not docker_client: # ... (handle no docker) ...
    else: # ... (normal startup flow, including initialize_tunnel, reconcile, agent start, background tasks) ...
    logging.info("Starting Flask web server..."); # ... (waitress start and main loop) ...