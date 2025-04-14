import os
import sys
import logging
import re
import json
import threading
import time
from datetime import datetime, timedelta, timezone

import docker # Docker SDK
from docker.errors import NotFound, APIError
from flask import Flask, jsonify, render_template_string, redirect, url_for, request
from dotenv import load_dotenv
import requests # Cloudflare API

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')
load_dotenv()

# Cloudflare Config
CF_API_TOKEN = os.getenv('CF_API_TOKEN')
TUNNEL_NAME = os.getenv('TUNNEL_NAME')
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}

# App Config
LABEL_PREFIX = os.getenv('LABEL_PREFIX', 'cloudflare.tunnel')
GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 28800)) # 8 hours default
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 300)) # 5 mins default
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/state.json') # Ensure this path is writable inside the container

# Cloudflared Agent Config
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"
# --- NEW: Docker network for cloudflared and target services ---
CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net')

# --- Environment Variable Checks ---
if not CF_API_TOKEN or not TUNNEL_NAME or not CF_ACCOUNT_ID:
    logging.error("FATAL: Missing required environment variables (CF_API_TOKEN, TUNNEL_NAME, CF_ACCOUNT_ID)")
    sys.exit(1)

# --- Docker Client ---
try:
    docker_client = docker.from_env()
    docker_client.ping()
    logging.info("Successfully connected to Docker daemon.")
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    docker_client = None # Keep track that client is unavailable

# --- Global State & Locking ---
tunnel_state = { "name": TUNNEL_NAME, "id": None, "token": None, "status_message": "Initializing...", "error": None }
cloudflared_agent_state = { "container_status": "unknown", "last_action_status": None }
managed_rules = {} # { hostname: { service, container_id, status, delete_at } }
state_lock = threading.Lock()
stop_event = threading.Event()

# --- State Persistence ---
def load_state():
    global managed_rules
    if not os.path.exists(STATE_FILE_PATH):
        logging.info(f"State file '{STATE_FILE_PATH}' not found, starting fresh.")
        managed_rules = {}
        return
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            loaded_data = json.load(f)
        # Convert delete_at back to datetime objects
        for hostname, rule in loaded_data.items():
             if rule.get("delete_at") and isinstance(rule.get("delete_at"), str):
                 try:
                     # Try parsing with timezone, fallback to naive then localize
                     rule["delete_at"] = datetime.fromisoformat(rule["delete_at"])
                 except ValueError:
                     try:
                        naive_dt = datetime.fromisoformat(rule["delete_at"].replace('Z', '+00:00'))
                        rule["delete_at"] = naive_dt.replace(tzinfo=timezone.utc) if naive_dt.tzinfo is None else naive_dt
                     except Exception as date_err:
                         logging.warning(f"Could not parse delete_at for {hostname}: {rule['delete_at']} Error: {date_err}. Setting to None.")
                         rule["delete_at"] = None
             elif not isinstance(rule.get("delete_at"), datetime):
                 rule["delete_at"] = None # Ensure it's either datetime or None

        managed_rules = loaded_data # Assign after successful parsing
        logging.info(f"Loaded state for {len(managed_rules)} rules from {STATE_FILE_PATH}")

    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Error loading state from {STATE_FILE_PATH}: {e}. Starting fresh.", exc_info=True)
        managed_rules = {} # Reset state on error

def save_state():
    # No lock here, assume it's called within a locked block or thread-safely
    serializable_state = {}
    for hostname, rule in managed_rules.items():
        rule_copy = rule.copy()
        # Ensure delete_at is ISO formatted string with UTC timezone ('Z')
        if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
            dt_utc = rule_copy["delete_at"].astimezone(timezone.utc)
            rule_copy["delete_at"] = dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ') # More compatible ISO format
        serializable_state[hostname] = rule_copy

    try:
        temp_file_path = STATE_FILE_PATH + ".tmp"
        with open(temp_file_path, 'w') as f:
            json.dump(serializable_state, f, indent=2)
        os.replace(temp_file_path, STATE_FILE_PATH) # Atomic replace
        logging.debug(f"Saved state for {len(managed_rules)} rules to {STATE_FILE_PATH}")
    except (IOError, OSError) as e:
        logging.error(f"Error saving state to {STATE_FILE_PATH}: {e}", exc_info=True)

# --- Cloudflare API Helpers ---
def cf_api_request(method, endpoint, json_data=None, params=None):
    url = f"{CF_API_BASE_URL}{endpoint}"
    error_msg = None
    try:
        logging.info(f"API Request: {method} {url} Params: {params} Data: {json_data}")
        response = requests.request(method, url, headers=CF_HEADERS, json=json_data, params=params, timeout=30)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        logging.info(f"API Response Status: {response.status_code}")

        # Handle potential empty success responses (e.g., PUT, DELETE)
        if response.status_code == 204 or not response.content:
            return {"success": True} # Simulate success structure

        # Try to parse JSON, handle potential errors
        try:
            response_data = response.json()
            logging.debug(f"API Response Body: {response_data}")
            return response_data
        except json.JSONDecodeError:
            logging.error(f"API response for {method} {url} was not valid JSON. Status: {response.status_code}. Body: {response.text[:200]}")
            raise requests.exceptions.RequestException(f"Invalid JSON response from API. Status: {response.status_code}", response=response)

    except requests.exceptions.RequestException as e:
        logging.error(f"API Request Failed: {method} {url}")
        error_msg = f"Request Exception: {e}"
        # Try to get more specific error from response body if available
        if e.response is not None:
            logging.error(f"Status Code: {e.response.status_code}")
            try:
                error_data = e.response.json()
                logging.error(f"Response Body: {error_data}")
                cf_errors = error_data.get('errors', [])
                if cf_errors and isinstance(cf_errors, list) and len(cf_errors) > 0 and isinstance(cf_errors[0], dict):
                    error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}"
                else:
                    error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
            except (ValueError, AttributeError): # Handle non-JSON error response
                 error_msg = f"HTTP {e.response.status_code} - {e.response.text[:100]}"
        else:
            logging.error(f"Error details (no response received): {e}")

        # Update global state only if it's a tunnel creation/lookup issue during initialization
        if "cfd_tunnel" in endpoint and tunnel_state.get("id") is None:
             tunnel_state["error"] = error_msg

        raise requests.exceptions.RequestException(error_msg, response=e.response) # Re-raise with refined message

# --- Tunnel Initialization (API Based) ---
def find_tunnel_via_api(name):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"name": name, "is_deleted": "false"}
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])
        if tunnels and isinstance(tunnels, list):
            tunnel = tunnels[0] # Assume first is the one if multiple somehow exist
            tunnel_id = tunnel.get("id")
            if tunnel_id:
                logging.info(f"Found existing tunnel '{name}' with ID: {tunnel_id} via API.")
                # Token is *not* returned by list, need separate call
                token = get_tunnel_token_via_api(tunnel_id)
                return tunnel_id, token
            else:
                 logging.warning(f"Found tunnel entry for '{name}' but it has no ID in API response: {tunnel}")
                 return None, None
        else:
            logging.info(f"Tunnel '{name}' not found via API.")
            return None, None
    except Exception as e:
        logging.error(f"Error finding tunnel '{name}' via API: {e}")
        tunnel_state["error"] = f"Failed finding tunnel: {e}"
        return None, None

def get_tunnel_token_via_api(tunnel_id):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    url = f"{CF_API_BASE_URL}{endpoint}"
    try:
        logging.info(f"API Request: GET {url} (for token)")
        # Token endpoint returns plain text, not JSON
        response = requests.request("GET", url, headers={"Authorization": f"Bearer {CF_API_TOKEN}"}, timeout=30)
        response.raise_for_status()
        token = response.text.strip()
        # Basic validation for token format
        if not token or len(token) < 50: # Tokens are usually quite long
            logging.error(f"Retrieved token for tunnel {tunnel_id} appears invalid (too short or empty).")
            raise ValueError("Invalid token format received from API")
        logging.info(f"Successfully retrieved token via API for tunnel {tunnel_id}")
        return token
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error getting token for tunnel {tunnel_id}: {e}"
        if e.response is not None:
             error_msg += f" Status: {e.response.status_code} Body: {e.response.text[:100]}"
        logging.error(error_msg, exc_info=True)
        tunnel_state["error"] = error_msg # Update state if token fetch fails
        raise # Re-raise the exception

def create_tunnel_via_api(name):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    # Send tunnel secret only on creation for security
    # Generate a dummy secret, cloudflared will manage its own connector secret
    # config_src='cloudflare' is important for API management
    payload = {"name": name, "config_src": "cloudflare"}
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        # The token is *also* returned on creation
        token = result.get("token")
        if not tunnel_id or not token:
            logging.error(f"API response for tunnel creation missing ID or Token: {result}")
            raise ValueError("Missing ID or Token in API response for tunnel creation")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id} via API.")
        return tunnel_id, token
    except Exception as e:
        logging.error(f"Error creating tunnel '{name}' via API: {e}")
        tunnel_state["error"] = f"Failed creating tunnel: {e}"
        return None, None

def initialize_tunnel():
    tunnel_state["status_message"] = f"Checking for tunnel '{TUNNEL_NAME}' via API..."
    tunnel_state["error"] = None # Reset error at start
    tunnel_id = None
    token = None

    try:
        # Step 1: Try to find the tunnel
        tunnel_id, token = find_tunnel_via_api(TUNNEL_NAME)

        # Step 2: If not found, create it
        if not tunnel_id and not tunnel_state.get("error"): # Only create if find didn't error
            tunnel_state["status_message"] = f"Tunnel '{TUNNEL_NAME}' not found. Creating via API..."
            tunnel_id, token = create_tunnel_via_api(TUNNEL_NAME)

        # Step 3: If found but token fetch failed earlier, or creation failed, we won't have both
        if tunnel_id and token:
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = token
            tunnel_state["status_message"] = "Tunnel setup complete (using API)."
            tunnel_state["error"] = None # Clear any transient error from find/create steps if we ultimately succeed
        elif not tunnel_state.get("error"): # If no specific error was recorded, set a generic one
             tunnel_state["status_message"] = "Tunnel initialization failed."
             tunnel_state["error"] = "Failed to find/create tunnel or retrieve token. Check logs."
        else:
             # An error was already set by find/create/token functions
             tunnel_state["status_message"] = "Tunnel initialization failed (see error details)."

    except Exception as e:
        # Catch any unexpected errors during the process
        logging.error(f"Unhandled exception during tunnel initialization: {e}", exc_info=True)
        if not tunnel_state.get("error"): # Avoid overwriting a more specific API error
            tunnel_state["error"] = f"Initialization failed: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (unexpected error)."

# --- Cloudflare Tunnel Configuration Management ---
def get_current_cf_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot get CF config, tunnel ID not available.")
        return None
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
    try:
        response_data = cf_api_request("GET", endpoint)
        # Check structure carefully based on actual Cloudflare API response
        if response_data and isinstance(response_data, dict) and response_data.get("success"):
            result_data = response_data.get("result")
            if isinstance(result_data, dict):
                 config_data = result_data.get("config")
                 # config can be null or an empty dict if no config set yet
                 if isinstance(config_data, dict):
                     logging.debug(f"Successfully fetched and parsed config: {config_data}")
                     return config_data
                 elif config_data is None:
                     logging.info("Fetched config is null (no configuration set yet). Returning empty config.")
                     return {} # Return empty dict to signify no rules
                 else:
                     logging.warning(f"Unexpected type for 'config' field in API response. Expected dict or null, got {type(config_data)}. Response: {response_data}")
                     return {} # Treat as empty/invalid
            else:
                logging.warning(f"API response success but no 'result' dict or unexpected format. Response: {response_data}")
                return {} # Treat as empty/invalid
        elif response_data:
            logging.warning(f"API response format unexpected or success=false. Response: {response_data}")
            # Attempt to extract error if possible
            cf_errors = response_data.get('errors', [])
            if cf_errors: tunnel_state["error"] = f"Failed get tunnel config: {cf_errors[0].get('message', 'Unknown API error')}"
            return None # Indicate failure
        else:
            # This case shouldn't happen if cf_api_request works correctly, but handle defensively
            logging.error("cf_api_request returned None unexpectedly for GET config.")
            return None # Indicate failure

    except requests.exceptions.RequestException as e: # Catch API errors specifically
        logging.error(f"API error fetching config for tunnel {tunnel_state['id']}: {e}")
        if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]: # Avoid overwriting init errors
             tunnel_state["error"] = f"Failed get tunnel config: {e}"
        return None # Indicate failure
    except Exception as e: # Catch other unexpected errors
        logging.error(f"Unexpected exception in get_current_cf_config: {e}", exc_info=True)
        if not tunnel_state.get("error"): tunnel_state["error"] = f"Failed get/parse tunnel config: {e}"
        return None # Indicate failure


def update_cloudflare_config():
    if not tunnel_state.get("id"):
        logging.warning("Cannot update Cloudflare config, tunnel ID not available.")
        return False

    # Perform read/modify of managed_rules and CF config fetch inside lock
    with state_lock:
        logging.info("Attempting to prepare Cloudflare tunnel configuration update...")

        # Fetch current config from Cloudflare first
        current_config = get_current_cf_config()
        if current_config is None:
            logging.error("Failed to fetch current Cloudflare config, aborting update.")
            # Error should already be set in tunnel_state by get_current_cf_config
            return False

        # Build the desired ingress rules based on current *active* managed rules
        desired_ingress_rules = []
        catch_all_rule = {"service": "http_status:404"}
        for hostname, rule_details in managed_rules.items():
            # Only include rules that are marked as active
            if rule_details.get("status") == "active":
                service = rule_details.get("service")
                if service:
                    desired_rule = {"hostname": hostname, "service": service}
                    # Add originRequest config if needed in the future
                    # desired_rule["originRequest"] = {"noTLSVerify": True} # Example
                    desired_ingress_rules.append(desired_rule)
                else:
                    logging.warning(f"Managed rule for '{hostname}' is active but missing 'service' detail. Skipping.")

        # Get existing ingress rules from Cloudflare, excluding the catch-all
        current_cf_ingress = [rule for rule in current_config.get("ingress", [])
                              if rule.get("service") != catch_all_rule["service"]]

        # Check if the desired set (excluding catch-all) matches the current set (excluding catch-all)
        # Convert rules to a comparable format (e.g., tuples of sorted items) to ignore order
        def rule_to_tuple(rule):
            # Ensure hostname and service exist for comparison
            if "hostname" in rule and "service" in rule:
                 return tuple(sorted(rule.items()))
            return None # Ignore rules missing key fields

        current_cf_set = {rule_to_tuple(rule) for rule in current_cf_ingress if rule_to_tuple(rule)}
        desired_set = {rule_to_tuple(rule) for rule in desired_ingress_rules if rule_to_tuple(rule)}

        # Compare the sets
        if current_cf_set == desired_set:
            logging.info("No changes detected between managed state and Cloudflare config. Skipping API update.")
            return True # No update needed, success

        logging.info("Change detected. Desired ingress rules differ from current Cloudflare config.")
        logging.debug(f"Current CF rules (non-404): {current_cf_ingress}")
        logging.debug(f"Desired rules (from state): {desired_ingress_rules}")

        # Prepare the final list of rules to push (desired + catch-all)
        final_ingress_rules = desired_ingress_rules + [catch_all_rule]
        payload = {"config": {"ingress": final_ingress_rules}}

        # Release lock before making the potentially slow API call
        pass # Exiting the 'with state_lock' block releases the lock

    # --- API call outside the lock ---
    logging.info("Pushing updated configuration to Cloudflare API...")
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
    try:
        cf_api_request("PUT", endpoint, json_data=payload)
        logging.info("Successfully updated Cloudflare tunnel configuration via API.")
        cloudflared_agent_state["last_action_status"] = "Cloudflare config updated successfully." # Give feedback
        return True
    except requests.exceptions.RequestException as e:
        # Log the specific API error
        logging.error(f"Failed to update Cloudflare tunnel configuration via API: {e}")
        # Update state to show error in UI
        cloudflared_agent_state["last_action_status"] = f"Error updating CF config: {e}"
        # Also store potentially more detailed error in tunnel_state if available
        if not tunnel_state.get("error") or "API Error" not in tunnel_state["error"]:
             tunnel_state["error"] = f"Failed update tunnel config: {e}"
        return False
    except Exception as e:
        # Catch any other unexpected error during the PUT request
        logging.error(f"Unexpected error updating Cloudflare config: {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected error updating CF config: {e}"
        if not tunnel_state.get("error"): tunnel_state["error"] = f"Failed update tunnel config: {e}"
        return False

# --- Docker Event Handling ---
def process_container_start(container):
    if not container: return
    try:
        # It's possible the container disappears between event and processing
        try:
             container.reload()
        except NotFound:
             logging.warning(f"Container {container.id[:12]} not found when processing start event (likely stopped quickly).")
             return

        labels = container.labels
        container_id = container.id
        container_name = container.name # Get name for logging/debugging

        # Check labels
        enabled_label = f"{LABEL_PREFIX}.enable"
        hostname_label = f"{LABEL_PREFIX}.hostname"
        service_label = f"{LABEL_PREFIX}.service"

        is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
        hostname = labels.get(hostname_label)
        service = labels.get(service_label)

        # Ignore if not enabled
        if not is_enabled:
            logging.debug(f"Ignoring start event for container {container_name} ({container_id[:12]}): '{enabled_label}' is not 'true'.")
            return

        # Validate required labels are present
        if not hostname or not service:
            logging.warning(f"Ignoring start event for container {container_name} ({container_id[:12]}): Missing required labels '{hostname_label}' or '{service_label}'.")
            return

        # Basic validation (can be enhanced)
        if not re.match(r"^[a-zA-Z0-9.-]+$", hostname):
             logging.warning(f"Ignoring start event for container {container_name} ({container_id[:12]}): Invalid hostname format '{hostname}'.")
             return
        # Ensure service points to http/https/tcp/unix *or* a container name (which implies http)
        # For bridge network, service should be like http://container_name:port
        if not (service.startswith(("http://", "https://", "tcp://", "unix:")) or re.match(r"^[a-zA-Z0-9_-]+:\d+$", service)):
             # Check if it's potentially just container_name:port which implies http
             # If using bridge mode, validate service format points to internal service.
             # Example: 'my-app:8080' will be automatically converted to 'http://my-app:8080' by cloudflared
             # Accept formats like 'http://container:port', 'https://..', 'tcp://..', 'unix:/..', or 'container:port'
             logging.warning(f"Ignoring start event for {container_name} ({container_id[:12]}): Invalid service format '{service}'. Needs scheme (http/https/tcp/unix) or be container_name:port.")
             return

        logging.info(f"Detected start for managed container: {container_name} ({container_id[:12]}) - Hostname: {hostname}, Service: {service}")

        needs_cf_update = False
        state_changed_locally = False
        update_needed = False # Combined flag

        with state_lock:
            existing_rule = managed_rules.get(hostname)

            if existing_rule:
                # Case 1: Rule exists, was pending deletion - reactivate
                if existing_rule.get("status") == "pending_deletion":
                    logging.info(f"Rule for {hostname} was pending deletion. Reactivating.")
                    existing_rule["status"] = "active"
                    existing_rule["delete_at"] = None
                    existing_rule["service"] = service # Update service just in case
                    existing_rule["container_id"] = container_id # Update container ID
                    state_changed_locally = True
                    needs_cf_update = True # Reactivation requires CF update

                # Case 2: Rule exists, active, check if service or container changed
                elif existing_rule.get("status") == "active":
                    service_changed = existing_rule.get("service") != service
                    container_changed = existing_rule.get("container_id") != container_id
                    if service_changed or container_changed:
                         log_msg = f"Updating rule for {hostname}:"
                         if service_changed: log_msg += f" Service changed ('{existing_rule.get('service')}' -> '{service}')."
                         if container_changed: log_msg += f" Container changed ('{existing_rule.get('container_id', 'N/A')[:12]}' -> '{container_id[:12]}')."
                         logging.info(log_msg)
                         existing_rule["service"] = service
                         existing_rule["container_id"] = container_id
                         state_changed_locally = True
                         # Only need CF update if the *service* definition changed
                         if service_changed: needs_cf_update = True
                    else:
                         logging.info(f"Container start event for {hostname}, but rule is already active with same details.")
            else:
                # Case 3: New rule
                logging.info(f"Adding new active rule for hostname: {hostname}")
                managed_rules[hostname] = {
                    "service": service,
                    "container_id": container_id,
                    "status": "active",
                    "delete_at": None
                }
                state_changed_locally = True
                needs_cf_update = True # Adding a rule requires CF update

            update_needed = state_changed_locally or needs_cf_update

            # --- Save state immediately if changed locally ---
            if state_changed_locally:
                logging.debug(f"Local state changed for {hostname}, saving state file...")
                save_state() # Save within lock

        # --- Trigger CF update outside lock if needed ---
        if needs_cf_update:
            logging.info(f"Triggering Cloudflare config update due to change for {hostname}.")
            if not update_cloudflare_config():
                # If CF update fails, the state is saved but CF is out of sync.
                # Reconciliation should eventually fix this, but log error.
                logging.error(f"Failed to update Cloudflare config after processing start for {hostname}. State might be inconsistent until next reconciliation.")
                # Optionally: could revert the local state change here, but complicates logic. Rely on reconcile.
        elif state_changed_locally:
             logging.debug(f"Local state updated for {hostname} (e.g., container ID), no Cloudflare config change needed.")


    except NotFound:
        # This can happen if container is removed very quickly after start event
        logging.warning(f"Container {container.id[:12] if container else 'Unknown'} not found during start processing.")
    except APIError as e:
        logging.error(f"Docker API error processing container start ({container.id[:12] if container else 'Unknown'}): {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error processing container start ({container.id[:12] if container else 'Unknown'}): {e}", exc_info=True)


def schedule_container_stop(container_id):
    if not container_id: return

    logging.info(f"Processing stop event for container {container_id[:12]}. Checking for managed rules.")
    hostname_to_schedule = None
    state_changed = False

    with state_lock:
        # Find if this container manages an *active* rule
        for hn, details in managed_rules.items():
            if details.get("container_id") == container_id and details.get("status") == "active":
                hostname_to_schedule = hn
                break # Assume one container manages at most one rule directly

        if hostname_to_schedule:
            logging.info(f"Container {container_id[:12]} managed active rule for {hostname_to_schedule}. Marking for deletion.")
            rule = managed_rules[hostname_to_schedule]
            if rule.get("status") != "pending_deletion": # Avoid rescheduling if already pending
                 rule["status"] = "pending_deletion"
                 # Ensure delete_at is timezone-aware (UTC)
                 rule["delete_at"] = datetime.now(timezone.utc) + timedelta(seconds=GRACE_PERIOD_SECONDS)
                 logging.info(f"Rule for {hostname_to_schedule} scheduled for deletion at {rule['delete_at']}")
                 state_changed = True
            else:
                 logging.info(f"Rule for {hostname_to_schedule} was already pending deletion.")
        else:
            logging.info(f"Stop event for container {container_id[:12]}, but it didn't manage any active rule in the current state.")

        # --- Save state if changed ---
        if state_changed:
            save_state() # Save within lock

    # Note: We don't trigger a Cloudflare update here. The cleanup task handles removal later.

def docker_event_listener():
    if not docker_client:
        logging.error("Docker client unavailable, event listener cannot start.")
        return
    logging.info("Starting Docker event listener...")
    try:
        # Get events from now onwards
        events = docker_client.events(decode=True, since=int(time.time()))
        for event in events:
            if stop_event.is_set():
                logging.info("Stop event received, exiting Docker event listener.")
                break

            ev_type = event.get("Type")
            action = event.get("Action")
            actor = event.get("Actor", {})
            cont_id = actor.get("ID")

            logging.debug(f"Docker Event: Type={ev_type}, Action={action}, ActorID={cont_id[:12] if cont_id else 'N/A'}")

            # We only care about container events with an ID
            if ev_type == "container" and cont_id:
                if action == "start":
                    # Need to get the container object to read labels
                    try:
                        container = docker_client.containers.get(cont_id)
                        process_container_start(container)
                    except NotFound:
                        # Can happen if container stops again very quickly
                        logging.warning(f"Container {cont_id[:12]} not found shortly after 'start' event.")
                    except APIError as e:
                         logging.error(f"Docker API error getting container {cont_id[:12]} after start event: {e}")
                    except Exception as e:
                         logging.error(f"Error processing start event for {cont_id[:12]}: {e}", exc_info=True)

                # Treat stop, die, destroy as triggers to schedule deletion
                elif action in ["stop", "die", "destroy"]:
                     try:
                         schedule_container_stop(cont_id)
                     except Exception as e:
                         logging.error(f"Error processing stop/die event for {cont_id[:12]}: {e}", exc_info=True)

    except APIError as e:
         # Handle errors like Docker daemon stopping
         logging.error(f"Docker API error in event listener stream: {e}. Listener stopping.")
         # Consider trying to restart the listener after a delay? For now, it stops.
    except Exception as e:
        # Catch other unexpected errors
        logging.error(f"Unexpected error in Docker event listener: {e}", exc_info=True)
    finally:
        logging.info("Docker event listener stopped.")


# --- Cleanup Task ---
def cleanup_expired_rules():
    logging.info("Starting cleanup task...")
    while not stop_event.is_set():
        try:
            logging.debug("Running cleanup check for expired rules...")
            hostnames_to_remove_from_cf = []
            now_utc = datetime.now(timezone.utc)
            state_changed_in_cleanup = False

            with state_lock:
                # Identify expired rules
                for hostname, details in managed_rules.items():
                    if details.get("status") == "pending_deletion":
                        delete_at = details.get("delete_at")
                        # Ensure delete_at is a timezone-aware datetime object
                        if isinstance(delete_at, datetime):
                             if delete_at.tzinfo is None: # If loaded state was naive, assume UTC
                                 delete_at = delete_at.replace(tzinfo=timezone.utc)
                             if delete_at <= now_utc:
                                 logging.info(f"Rule for {hostname} deletion grace period expired ({delete_at}). Scheduling removal from Cloudflare.")
                                 hostnames_to_remove_from_cf.append(hostname)
                        else:
                             logging.warning(f"Rule {hostname} is pending_deletion but delete_at is invalid or missing: {delete_at}. Skipping cleanup for this rule.")

            # --- Trigger CF Update & State Change (outside initial lock) ---
            if hostnames_to_remove_from_cf:
                logging.info(f"Attempting Cloudflare update to remove expired rules: {hostnames_to_remove_from_cf}")
                # Important: We update CF based on the *current* active rules,
                # implicitly removing those not marked active anymore.
                if update_cloudflare_config():
                    logging.info(f"Cloudflare config updated successfully. Removing expired rules from local state: {hostnames_to_remove_from_cf}")
                    # Now, actually remove them from the local state dictionary
                    with state_lock:
                        deleted_count = 0
                        for hostname in hostnames_to_remove_from_cf:
                            # Double-check rule still exists and is pending before deleting
                            if hostname in managed_rules and managed_rules[hostname].get("status") == "pending_deletion":
                                del managed_rules[hostname]
                                deleted_count += 1
                                state_changed_in_cleanup = True
                            else:
                                logging.warning(f"Rule {hostname} was scheduled for removal but not found or no longer 'pending_deletion' when removing from state.")
                        logging.info(f"Removed {deleted_count} rules from local state.")
                        # Save state only if rules were actually deleted
                        if state_changed_in_cleanup:
                            save_state()
                else:
                    logging.error("Failed to update Cloudflare during rule cleanup. Expired rules remain in local state and potentially in Cloudflare. Will retry on next cleanup cycle.")
            else:
                logging.debug("No expired rules found requiring cleanup.")

        except Exception as e:
            logging.error(f"Error in cleanup task loop: {e}", exc_info=True)

        # Wait for the next interval or until stop event is set
        stop_event.wait(CLEANUP_INTERVAL_SECONDS)

    logging.info("Cleanup task stopped.")


# --- Reconciliation ---
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
        # --- Get Current State from Sources ---
        # 1. Running Docker Containers with Labels
        running_labeled_containers = {} # { hostname: { service, container_id, container_name } }
        try:
             containers = docker_client.containers.list(sparse=True) # sparse=True might be faster
             logging.debug(f"[Reconcile] Found {len(containers)} running containers.")
             for c in containers:
                 # Need full inspect for labels if sparse doesn't include them
                 try:
                     c.reload() # Get full attributes including labels
                     labels = c.labels
                     enabled_label = f"{LABEL_PREFIX}.enable"
                     hostname_label = f"{LABEL_PREFIX}.hostname"
                     service_label = f"{LABEL_PREFIX}.service"

                     is_enabled = labels.get(enabled_label, "false").lower() in ["true", "1", "t", "yes"]
                     hostname = labels.get(hostname_label)
                     service = labels.get(service_label)

                     if is_enabled and hostname and service:
                         # Basic validation again
                         if not re.match(r"^[a-zA-Z0-9.-]+$", hostname): continue
                         if not (service.startswith(("http://", "https://", "tcp://", "unix:")) or re.match(r"^[a-zA-Z0-9_-]+:\d+$", service)): continue

                         if hostname in running_labeled_containers:
                              logging.warning(f"[Reconcile] Duplicate hostname label '{hostname}' found on container {c.name} ({c.id[:12]}) and container {running_labeled_containers[hostname]['container_name']} ({running_labeled_containers[hostname]['container_id'][:12]}). Using the latest one found ({c.name}).")
                         running_labeled_containers[hostname] = {
                             "service": service,
                             "container_id": c.id,
                             "container_name": c.name
                         }
                 except NotFound:
                      logging.warning(f"[Reconcile] Container {c.id[:12]} listed but then not found during reload. Skipping.")
                      continue # Skip this container if it disappeared
                 except APIError as e:
                      logging.error(f"[Reconcile] Docker API error reloading container {c.id[:12]}: {e}. Skipping.")
                      continue

             logging.info(f"[Reconcile] Found {len(running_labeled_containers)} running containers with valid labels.")

        except APIError as e:
             logging.error(f"[Reconcile] Docker API error listing containers: {e}. Aborting reconciliation.")
             return

        # 2. Current Cloudflare Configuration (fetch outside lock if possible, but needs lock for comparison later)
        # Moved get_current_cf_config inside lock logic below where needed for comparison

        # --- Perform Reconciliation Logic (under lock) ---
        with state_lock:
            logging.debug("[Reconcile] Acquired state lock.")
            now_utc = datetime.now(timezone.utc)
            managed_hostnames = set(managed_rules.keys())
            running_hostnames = set(running_labeled_containers.keys())

            # Iterate through running labeled containers
            for hostname, running_details in running_labeled_containers.items():
                if hostname in managed_rules:
                    rule = managed_rules[hostname]
                    # Scenario 1: Rule exists, maybe pending deletion -> Reactivate if running
                    if rule.get("status") == "pending_deletion":
                        logging.info(f"[Reconcile] Hostname {hostname} is running but rule was pending deletion. Reactivating.")
                        rule["status"] = "active"
                        rule["delete_at"] = None
                        rule["service"] = running_details["service"] # Ensure service is up-to-date
                        rule["container_id"] = running_details["container_id"] # Update container ID
                        state_changed_locally = True
                        needs_cf_update = True
                    # Scenario 2: Rule exists and active -> Check if service/container changed
                    elif rule.get("status") == "active":
                         service_changed = rule.get("service") != running_details["service"]
                         container_changed = rule.get("container_id") != running_details["container_id"]
                         if service_changed or container_changed:
                              logging.info(f"[Reconcile] Updating state for active rule {hostname} (service/container changed).")
                              rule["service"] = running_details["service"]
                              rule["container_id"] = running_details["container_id"]
                              state_changed_locally = True
                              if service_changed: needs_cf_update = True # Only need CF update if service changed
                else:
                    # Scenario 3: Container running but no rule exists -> Add new rule
                    logging.info(f"[Reconcile] Found running container for {hostname} but no managed rule. Adding new rule.")
                    managed_rules[hostname] = {
                        "service": running_details["service"],
                        "container_id": running_details["container_id"],
                        "status": "active",
                        "delete_at": None
                    }
                    state_changed_locally = True
                    needs_cf_update = True

            # Iterate through managed rules to find ones that are no longer running
            for hostname in list(managed_hostnames): # Iterate over copy of keys
                if hostname not in running_hostnames:
                     rule = managed_rules[hostname]
                     # Scenario 4: Rule is active but container not running -> Schedule deletion
                     if rule.get("status") == "active":
                          logging.info(f"[Reconcile] Managed rule {hostname} is active but no container found running. Scheduling deletion.")
                          rule["status"] = "pending_deletion"
                          rule["delete_at"] = now_utc + timedelta(seconds=GRACE_PERIOD_SECONDS)
                          state_changed_locally = True
                          # Deletion doesn't trigger immediate CF update, cleanup task handles it.
                     # Scenario 5: Rule is pending deletion and container still not running -> Do nothing, let cleanup handle it
                     elif rule.get("status") == "pending_deletion":
                          logging.debug(f"[Reconcile] Rule {hostname} is pending deletion and container not running. No action needed.")

            # --- Optional: Compare with actual CF config for deeper reconciliation ---
            # This makes reconcile slower but more robust against external CF changes
            logging.debug("[Reconcile] Fetching current CF config for final comparison...")
            current_cf_config = get_current_cf_config()
            if current_cf_config is not None:
                cf_ingress_hostnames = {r.get("hostname") for r in current_cf_config.get("ingress", [])
                                         if r.get("hostname") and r.get("service") != "http_status:404"}
                active_managed_hostnames = {hn for hn, d in managed_rules.items() if d.get("status") == "active"}

                # If CF has hostnames that our active state doesn't, something is off.
                # This could happen if a rule was deleted locally but CF update failed.
                # Triggering an update based on our current state should fix it.
                if cf_ingress_hostnames != active_managed_hostnames:
                     logging.warning(f"[Reconcile] Mismatch detected between active managed rules and Cloudflare config!")
                     logging.warning(f"[Reconcile] Active Managed: {active_managed_hostnames}")
                     logging.warning(f"[Reconcile] Found in CF: {cf_ingress_hostnames}")
                     logging.info("[Reconcile] Marking for Cloudflare update to align.")
                     needs_cf_update = True
            else:
                logging.error("[Reconcile] Could not fetch Cloudflare config during reconciliation. Skipping final comparison.")

            # --- Save state if changed locally ---
            if state_changed_locally:
                logging.info("[Reconcile] Local state changed during reconciliation. Saving state file.")
                save_state() # Save within lock

            logging.debug("[Reconcile] Releasing state lock.")
            # Lock released here

        # --- Trigger Cloudflare Update (outside lock) ---
        if needs_cf_update:
            logging.info("[Reconcile] Triggering Cloudflare config update based on reconciliation results.")
            if not update_cloudflare_config():
                logging.error("[Reconcile] Failed to update Cloudflare config during reconciliation.")
        elif state_changed_locally:
            logging.info("[Reconcile] Reconciliation resulted in local state changes only.")
        else:
            logging.info("[Reconcile] No changes detected during reconciliation.")

    except Exception as e:
        logging.error(f"Unexpected error during state reconciliation: {e}", exc_info=True)
    finally:
        logging.info("Reconciliation complete.")


# --- Docker Container Management ---
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
    except Exception as e:
        logging.error(f"Unexpected error getting container '{CLOUDFLARED_CONTAINER_NAME}': {e}")
        cloudflared_agent_state["last_action_status"] = f"Error: Unexpected error getting agent: {e}"
        return None


def update_cloudflared_container_status():
    if not docker_client:
        if cloudflared_agent_state["container_status"] != "docker_unavailable":
             logging.warning("Docker client not available, setting agent status.")
             cloudflared_agent_state["container_status"] = "docker_unavailable"
        return

    container = get_cloudflared_container()
    if container:
        try:
            container.reload() # Get fresh status
            if cloudflared_agent_state["container_status"] != container.status:
                 logging.info(f"Cloudflared agent container status changed to: {container.status}")
                 cloudflared_agent_state["container_status"] = container.status
        except (NotFound, APIError) as e:
            # Handle case where container disappeared between get() and reload()
            if cloudflared_agent_state["container_status"] != "not_found":
                 logging.warning(f"Error reloading cloudflared container status (container likely removed): {e}")
                 cloudflared_agent_state["container_status"] = "not_found"
                 cloudflared_agent_state["last_action_status"] = "Agent container disappeared."
    else:
        # Container not found by get_cloudflared_container
        if cloudflared_agent_state["container_status"] != "not_found":
            logging.info("Cloudflared agent container not found.")
            cloudflared_agent_state["container_status"] = "not_found"


def ensure_docker_network_exists(network_name):
    """Checks if a Docker network exists, creates it if not."""
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
            # Create a bridge network (standard)
            docker_client.networks.create(network_name, driver="bridge", check_duplicate=True)
            logging.info(f"Successfully created Docker network '{network_name}'.")
            return True
        except APIError as e:
            # Handle potential race condition if another process created it
            if "already exists" in str(e):
                 logging.warning(f"Docker network '{network_name}' already exists (created concurrently?).")
                 return True # Treat as success
            logging.error(f"Failed to create Docker network '{network_name}': {e}", exc_info=True)
            return False
    except APIError as e:
        logging.error(f"Error checking for Docker network '{network_name}': {e}", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking/creating Docker network '{network_name}': {e}", exc_info=True)
        return False

def start_cloudflared_container():
    logging.info(f"Attempting to start cloudflared agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Starting..."
    success_flag = False
    try:
        if not docker_client:
             msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
        if not tunnel_state.get("token"):
             msg = "Tunnel token not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        # --- Ensure required Docker network exists ---
        if not ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME):
             msg = f"Failed to ensure Docker network '{CLOUDFLARED_NETWORK_NAME}' exists."
             logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        token = tunnel_state["token"]
        container = get_cloudflared_container() # Check if it exists

        needs_recreate = False
        if container:
             try:
                 container.reload() # Refresh container state
                 logging.info(f"Found existing container '{CLOUDFLARED_CONTAINER_NAME}' with status: {container.status}")

                 # Check if running
                 if container.status == 'running':
                      msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is already running."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True # Already running, success

                 # Check if misconfigured (wrong network or host mode)
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
                      except APIError as rm_err: logging.error(f"Failed to remove misconfigured container: {rm_err}. Proceeding to create might fail."); needs_recreate=False # Reset flag if remove fails maybe? Or let create fail?
                      container = None # Ensure we enterLARED_CONTAINER_NAME}': {e}. Assuming it needs creation.")
                      container = None # Proceed to create block

        # Create container if it doesn't exist or needed recreation
        if not container and not success_flag: # Only create if not found or not successfully started above
            # --- THIS LINE IS CORRECTED ---
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found or needs creation. Creating...")
            # --- END CORRECTION ---
            try:
                # Pull image first (optional, run will pull if needed but good practice)
                try: logging.info(f"Pulling image {CLOUDFLARED_IMAGE}..."); docker_client.images.pull(CLOUDFLARED_IMAGE)
                except APIError as img_err: logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Docker run will attempt to pull.")

                # Run the container - **KEY CHANGE: use network, not network_mode**
                new_container = docker_client.containers.run(
                    image=CLOUDFLARED_IMAGE,
                    command=f"tunnel --no-autoupdate run --token {token}",
                    name=CLOUDFLARED_CONTAINER_NAME, # Use the correct variable here too
                    network=CLOUDFLARED_NETWORK_NAME, # Connect to the bridge network
                    restart_policy={"Name": "unless-stopped"},
                    detach=True,
                    remove=False, # Keep container after stop for inspection/restart
                    # Add labels for potential self-identification? Optional.
                    labels={"managed-by": "cloudflare-tunnel-ingress-controller"}
                )
                msg = f"Created and started container '{new_container.name}' on network '{CLOUDFLARED_NETWORK_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

            except APIError as create_err:
                # Handle case where name might be taken by a zombie container
                if "is already in use" in str(create_err):
                     logging.error(f"Container name '{CLOUDFLARED_ the creation block
                 else:
                      # Container exists, is stopped, and seems correctly configured - just start it
                      logging.info(f"Starting existing correctly configured container '{CLOUDFLARED_CONTAINER_NAME}'..."); container.start(); msg = f"Started existing container '{CLOUDFLARED_CONTAINER_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

             except (NotFound, APIError) as e:
                  logging.warning(f"Error checking existing container '{CLOUDFLARED_CONTAINER_NAME}': {e}. Assuming it needs creation.")
                  container = None # Proceed to create block

        # Create container if it doesn't exist or needed recreation
        if not container and not success_flag: # Only create if not found or not successfully started above
            # <<< --- THIS IS THE CORRECTED LINE --- >>>
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found or needs creation. Creating...")
            try:
                # Pull image first (optional, run will pull if needed but good practice)
                try: logging.info(f"Pulling image {CLOUDFLARED_IMAGE}..."); docker_client.images.pull(CLOUDFLARED_IMAGE)
                except APIError as img_err: logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Docker run will attempt to pull.")

                # Run the container - **KEY CHANGE: use network, not network_mode**
                new_container = docker_client.containers.run(
                    image=CLOUDFLARED_IMAGE,
                    command=f"tunnel --no-autoupdate run --token {token}",
                    name=CLOUDFLARED_CONTAINER_NAME,
                    network=CLOUDFLARED_NETWORK_NAME, # Connect to the bridge network
                    restart_policy={"Name": "unless-stopped"},
                    detach=True,
                    remove=False, # Keep container after stop for inspection/restart
                    # Add labels for potential self-identification? Optional.
                    labels={"managed-by": "cloudflare-tunnel-ingress-controller"}
                )
                msg = f"Created and started container '{new_container.name}' on network '{CLOUDFLARED_NETWORK_NAME}'."; cloudflared_agent_state["CONTAINER_NAME}' is already in use. Attempting to remove existing...") # Use correct variable
                     try:
                          stale_container = docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME) # Use correct variable
                          stale_container.remove(force=True)
                          logging.info("Removed stale container. Please try starting again.")
                          msg = f"Error: Container name conflict, removed stale container. Please retry start."
                     except (NotFound, APIError) as rm_err:
                          logging.error(f"Failed to remove stale container '{CLOUDFLARED_CONTAINER_NAME}': {rm_err}") # Use correct variable
                          msg = f"Error: Docker API error creating container: {create_err} (and failed to remove stale)"
                else:
                     msg = f"Docker API error creating container: {create_err}"; logging.error(msg, exc_info=True)
                cloudflared_agent_state["last_action_status"] = msg; success_flag = False
    except APIError as e:
        # Catch API errors from get/start/remove calls
        msg = f"Docker API error during start sequence: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        # Catch unexpected errors
        msg = f"Unexpectedlast_action_status"] = msg; logging.info(msg); success_flag = True

            except APIError as create_err:
                # Handle case where name might be taken by a zombie container
                if "is already in use" in str(create_err):
                     logging.error(f"Container name '{CLOUDFLARED_CONTAINER_NAME}' is already in use. Attempting to remove existing...")
                     try:
                          stale_container = docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
                          stale_container.remove(force=True)
                          logging.info("Removed stale container. Please try starting again.")
                          msg = f"Error: Container name conflict, removed stale container. Please retry start."
                     except (NotFound, APIError) as rm_err:
                          logging.error(f"Failed to remove stale container '{CLOUDFLARED_CONTAINER_NAME}': {rm_err}")
                          msg = f"Error: Docker API error creating container: {create_err} (and failed to remove stale)"
                else:
                     msg = f"Docker API error creating container: {create_err}"; logging.error(msg, exc_info=True)
                cloudflared_agent_state["last_action_status"] = msg; success_flag = False
    except APIError as e:
        # Catch API errors from get/start/remove calls
        msg = f"Docker API error during start sequence: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        # Catch unexpected errors
        msg = f"Unexpected error starting container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        # Update status after a short delay to allow container error starting container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        # Update status after a short delay to allow container state to settle
        if docker_client:
             logging.debug("Updating container status after start attempt...")
             time.sleep(2) # Small delay
             update_cloudflared_container_status()
        logging.info(f"Exiting start_cloudflared_container function (Success: {success_flag}).")
        return success_flag
        
def stop_cloudflared_container():
    logging.info(f"Attempting to stop cloudflared agent container '{CLOUDFLARED_CONTAINER_NAME}'...")
    cloudflared_agent_state["last_action_status"] = "Stopping..."
    success_flag = False
    try:
        if not docker_client:
            msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False

        container = get_cloudflared_container()
        if not container:
            msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found, cannot stop."; logging.warning(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True # Not found is success in this context

        # Check status before stopping
        container.reload()
        if container.status != 'running':
             msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is not running (status: {container.status}). No action needed."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; success_flag = True; return True

        logging.info(f"Stopping running container '{CLOUDFLARED_CONTAINER_NAME}'..."); container.stop(timeout=30); msg = f"Successfully stopped container '{CLOUDFLARED_CONTAINER_NAME}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); success_flag = True

    except APIError as e:
        msg = f"Docker API error stopping container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    except Exception as e:
        msg = f"Unexpected error stopping container: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; success_flag = False
    finally:
        # Update status after action
        if docker_client:
             logging.debug("Updating container status after stop attempt..."); time.sleep(2); update_cloudflared_container_status()
        logging.info(f"Exiting stop_cloudflared_container function (Success: {success_flag}).")
        return success_flag

# --- Flask Web Server ---
app = Flask(__name__)
app.secret_key = os.urandom(24) # For potential future session use

# UI Helper Function
def get_display_token(token):
    if not token: return "Not available"
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token retrieved (short)"

@app.route('/')
def status_page():
    # Always update status before rendering
    update_cloudflared_container_status()
    # Create copies for rendering to avoid race conditions with background threads
    with state_lock:
        template_rules = json.loads(json.dumps(managed_rules, default=str)) # Serialize/deserialize for safety
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()

    display_token = get_display_token(template_tunnel_state.get("token"))
    docker_available = docker_client is not None # Pass docker availability to template

    # Use the existing HTML template structure
    html_template = """<!DOCTYPE html><html><head><title>Cloudflare Tunnel Manager</title><style>body{font-family:sans-serif;padding:20px;background-color:#f4f4f4;color:#333}h1,h2,h3{color:#555}.container{background-color:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);margin-bottom:20px}table{width:100%;border-collapse:collapse;margin-top:15px}th,td{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}th{background-color:#f2f2f2}td pre{margin:0;background-color:transparent;padding:0;white-space:pre-wrap;word-break:break-all; font-family: monospace; font-size: 0.9em;}.status-box{padding:10px;border:1px solid #ccc;border-radius:5px;margin-top:10px;word-wrap:break-word}.error{background-color:#ffebeb;border-color:#ffc2c2;color:#a00}.success{background-color:#e6ffed;border-color:#c3e6cb;color:#155724}.info{background-color:#e7f3fe;border-color:#b8daff;color:#004085}.warning{background-color:#fff3cd;border-color:#ffeeba;color:#856404}.status-active{color:green}.status-pending{color:orange}.button{padding:10px 15px;border:none;border-radius:4px;color:#fff;cursor:pointer;font-size:1em;margin-right:10px}.small-button{padding:5px 10px;font-size:.9em}.start-button{background-color:#28a745}.stop-button{background-color:#dc3545}.delete-button{background-color:#dc3545}.button:disabled{background-color:#ccc;cursor:not-allowed;opacity:.6}form{display:inline-block;margin:0}</style></head><body><h1>Cloudflare Tunnel Manager</h1><div class="container"><h2>Initialization Status</h2><div class="status-box {{'error' if tunnel_state.get('error') else ('success' if tunnel_state.get('token') else 'info')}}"><p><strong>Message:</strong> {{tunnel_state.status_message}}</p>{% if tunnel_state.get('error') %}<p><strong>Error Details:</strong> <pre>{{tunnel_state.error}}</pre></p>{% endif %}</div><h3>Tunnel Details</h3><p><strong>Desired Tunnel Name:</strong> <pre>{{tunnel_state.name}}</pre></p><p><strong>Tunnel ID:</strong> <pre>{{tunnel_state.id if tunnel_state.id else 'Not available'}}</pre></p><p><strong>Tunnel Token:</strong> <pre>{{display_token}}</pre></p></div><div class="container"><h2>Tunnel Agent Control (<pre>{{cloudflared_container_name}}</pre>)</h2><p><strong>Agent Container Status:</strong> <strong style="text-transform:capitalize" class="{{'success' if agent_state.container_status=='running' else ('error' if 'error' in agent_state.container_status or agent_state.container_status=='docker_unavailable' or agent_state.container_status=='dead' else ('warning' if agent_state.container_status=='exited' or agent_state.container_status=='not_found' else 'info'))}}">{{agent_state.container_status.replace('_',' ')}}</strong></p>{% if agent_state.last_action_status %}<div class="status-box {{'error' if 'Error:' in agent_state.last_action_status else ('warning' if 'Warning:' in agent_state.last_action_status else 'info')}}"><strong>Last Action Result:</strong> {{agent_state.last_action_status}}</div>{% endif %}<form action="{{url_for('start_tunnel')}}" method="post" style="margin-right:10px"><button type="submit" class="button start-button" {{'disabled' if not tunnel_state.get('token') or agent_state.container_status=='running' or not docker_available }}>Start Tunnel Agent</button></form><form action="{{url_for('stop_tunnel')}}" method="post"><button type="submit" class="button stop-button" {{'disabled' if agent_state.container_status!='running' or not docker_available }}>Stop Tunnel Agent</button></form></div><div class="container"><h2>Managed Ingress Rules</h2>{% if rules %}<table><thead><tr><th>Hostname</th><th>Service Target</th><th>Status</th><th>Managing Container ID</th><th>Delete Scheduled At (UTC)</th><th>Actions</th></tr></thead><tbody>{% for hostname, details in rules.items() %}<tr><td><pre>{{hostname}}</pre></td><td><pre>{{details.service}}</pre></td><td><strong class="{{'status-active' if details.status=='active' else 'status-pending'}}">{{details.status}}</strong></td><td><pre>{{details.container_id[:12] if details.container_id else 'N/A'}}</pre></td><td>{{details.delete_at if details.status=='pending_deletion' else 'N/A'}}</td><td><form action="{{url_for('force_delete_rule', hostname=hostname)}}" method="post" onsubmit="return confirm('Are you sure you want to force delete the rule for {{hostname}} immediately? This will update Cloudflare.');"><button type="submit" class="button delete-button small-button" {{ 'disabled' if not docker_available }}>Force Delete</button></form></td></tr>{% endfor %}</tbody></table>{% else %}<p>No ingress rules are currently being managed.</p>{% endif %}</div></body></html>"""
    return render_template_string(html_template,
                                tunnel_state=template_tunnel_state,
                                agent_state=template_agent_state,
                                display_token=display_token,
                                cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                                docker_available=docker_available, # Pass availability flag
                                rules=template_rules)


@app.route('/start', methods=['POST'])
def start_tunnel():
    logging.info("Received request to start tunnel agent via UI.")
    start_cloudflared_container()
    return redirect(url_for('status_page'))

@app.route('/stop', methods=['POST'])
def stop_tunnel():
    logging.info("Received request to stop tunnel agent via UI.")
    stop_cloudflared_container()
    return redirect(url_for('status_page'))

@app.route('/force_delete/<hostname>', methods=['POST'])
def force_delete_rule(hostname):
    logging.info(f"Received request to force delete rule for hostname: {hostname}")
    state_changed = False
    update_triggered = False

    with state_lock:
        if hostname in managed_rules:
            logging.info(f"Force deleting rule for {hostname} from local state.")
            del managed_rules[hostname]
            state_changed = True
            # Save state immediately after removing locally
            save_state()
        else:
            logging.warning(f"Attempted force delete for hostname '{hostname}', but it was not found in managed rules.")
            cloudflared_agent_state["last_action_status"] = f"Warning: Rule {hostname} not found for force delete."
            # No state change, redirect back
            return redirect(url_for('status_page'))

    # If state was changed, trigger Cloudflare update (outside lock)
    if state_changed:
        logging.info(f"Triggering Cloudflare config update after force deleting {hostname}.")
        if update_cloudflare_config():
            logging.info(f"Cloudflare update successful after force deleting {hostname}.")
            cloudflared_agent_state["last_action_status"] = f"Successfully force deleted rule for {hostname} and updated Cloudflare."
        else:
            # CF update failed, but state is already saved without the rule.
            # Reconciliation should ideally fix CF later, but the immediate feedback is failure.
            logging.error(f"CRITICAL: State saved after force delete of {hostname}, but subsequent Cloudflare update FAILED. Config is inconsistent!")
            cloudflared_agent_state["last_action_status"] = f"Error: Removed {hostname} locally, but FAILED pushing update to Cloudflare! Reconciliation needed."
            # Tunnel state might contain a more specific error from the update attempt.

    return redirect(url_for('status_page'))


# --- Main Execution ---
if __name__ == '__main__':
    logging.info("----------------------------------------------------")
    logging.info("--- Cloudflare Tunnel Ingress Manager Starting ---")
    logging.info("----------------------------------------------------")

    # Load initial state from file
    load_state()
    logging.info("State loading complete.")

    # Ensure Docker is available before proceeding with Docker-dependent steps
    if not docker_client:
         logging.error("Docker client is unavailable. Limited functionality.")
         # Update state to reflect this issue
         tunnel_state["status_message"] = "Error: Docker client unavailable."
         tunnel_state["error"] = "Failed to connect to Docker daemon. Check socket mount and permissions."
         cloudflared_agent_state["container_status"] = "docker_unavailable"
         # Run Flask app to show error UI, but skip Docker-related tasks
         logging.warning("Skipping tunnel initialization, reconciliation, agent management, and background tasks due to Docker client unavailability.")
    else:
         # --- Docker client is available, proceed ---
         logging.info("Docker client available.")

         # Ensure the cloudflared network exists early on
         logging.info(f"Ensuring Docker network '{CLOUDFLARED_NETWORK_NAME}' exists...")
         ensure_docker_network_exists(CLOUDFLARED_NETWORK_NAME) # Best effort, continue even if it fails here

         # Initialize the Cloudflare Tunnel itself via API
         try:
             initialize_tunnel()
         except Exception as init_err:
             # Catch unexpected errors during initialization itself
             logging.error(f"Unhandled exception during initialize_tunnel call: {init_err}", exc_info=True)
             if not tunnel_state.get("error"): # Set generic error if none was set
                 tunnel_state["error"] = f"Unexpected error during init: {init_err}"
             tunnel_state["status_message"] = "Tunnel initialization failed unexpectedly."

         logging.info(f"Tunnel initialization process complete. Status: {tunnel_state.get('status_message')}")
         logging.info(f"Tunnel State: ID={tunnel_state.get('id')}, Token Present={bool(tunnel_state.get('token'))}, Error={tunnel_state.get('error')}")

         # Only proceed with reconciliation and agent start if tunnel is fully set up
         if tunnel_state.get("id") and tunnel_state.get("token"):
             logging.info("Tunnel appears initialized successfully. Proceeding with reconciliation and agent checks.")

             # Run initial reconciliation
             try:
                 reconcile_state()
                 logging.info("Initial state reconciliation complete.")
             except Exception as recon_err:
                 logging.error(f"Error during initial reconciliation: {recon_err}", exc_info=True)
                 cloudflared_agent_state["last_action_status"] = f"Error during initial reconcile: {recon_err}"

             # Attempt to start the cloudflared agent container if not running
             logging.info("Checking and attempting to automatically start tunnel agent container if needed...")
             update_cloudflared_container_status() # Get current status first
             if cloudflared_agent_state.get("container_status") != 'running':
                 logging.info("Agent container not running, attempting start...")
                 agent_started_ok = False
                 try:
                     agent_started_ok = start_cloudflared_container()
                 except Exception as start_err:
                     logging.error(f"Unhandled exception calling start_cloudflared_container: {start_err}", exc_info=True)
                     cloudflared_agent_state["last_action_status"] = f"Error: Unhandled exception during start ({start_err})"
                 if agent_started_ok:
                     logging.info("Call to start_cloudflared_container returned success.")
                 else:
                     logging.warning("Call to start_cloudflared_container returned failure. Check logs and agent status.")
             else:
                 logging.info("Agent container already running.")

             # Start background tasks ONLY if Docker is available and tunnel is initialized
             logging.info("Starting background threads for Docker events and rule cleanup.")
             event_thread = threading.Thread(target=docker_event_listener, name="DockerEventListener", daemon=True)
             cleanup_thread = threading.Thread(target=cleanup_expired_rules, name="CleanupTask", daemon=True)
             event_thread.start()
             cleanup_thread.start()

         else:
             logging.warning("Tunnel not fully initialized (missing ID or Token). Skipping reconciliation, agent start, and background tasks.")
             if not tunnel_state.get("error"): # Provide clearer status if no specific error occurred
                 tunnel_state["status_message"] = "Tunnel setup incomplete (ID/Token missing)."


    # Start the Flask web server regardless of initialization success to show status/errors
    logging.info("Starting Flask application web server on 0.0.0.0:5000...")
    try:
        # Use waitress or gunicorn in production instead of Flask dev server
        app.run(host='0.0.0.0', port=5000, use_reloader=False, threaded=True)
    except Exception as flask_err:
        logging.error(f"Flask server encountered a fatal error: {flask_err}", exc_info=True)

    # --- Cleanup ---
    logging.info("Flask app stopping or encountered error...")
    # Signal background threads to stop
    stop_event.set()
    logging.info("Stop event set for background threads.")

    # Optional: Wait briefly for threads to exit? (Daemon threads exit automatically)
    # time.sleep(1)

    logging.info("Exiting Cloudflare Tunnel Ingress Manager application.")
    sys.exit(0 if not tunnel_state.get("error") else 1) # Exit code based on tunnel status?