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
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s') # Added thread name
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
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/state.json')

# Cloudflared Agent Config
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"

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
    docker_client = None # Allow app to start but log error

# --- Global State & Locking ---
tunnel_state = { # Info about the tunnel itself
    "name": TUNNEL_NAME, "id": None, "token": None, "status_message": "Initializing...", "error": None
}
cloudflared_agent_state = { # Info about the running cloudflared container
    "container_status": "unknown", "last_action_status": None
}
managed_rules = {} # Our desired state: { hostname: { service, container_id, status, delete_at } }
state_lock = threading.Lock() # Lock for accessing managed_rules and updating CF config
stop_event = threading.Event() # To signal background threads to stop

# --- State Persistence ---
def load_state():
    """Loads managed_rules state from file."""
    global managed_rules
    if not os.path.exists(STATE_FILE_PATH):
        logging.info("State file not found, starting fresh.")
        managed_rules = {}
        return
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            loaded_data = json.load(f)
            # Basic validation could be added here
            managed_rules = loaded_data
            logging.info(f"Loaded state for {len(managed_rules)} rules from {STATE_FILE_PATH}")
            # Convert delete_at back to datetime objects if necessary (or store as ISO strings)
            for hostname, rule in managed_rules.items():
                 if rule.get("delete_at"):
                     try:
                         rule["delete_at"] = datetime.fromisoformat(rule["delete_at"])
                     except (ValueError, TypeError):
                          logging.warning(f"Could not parse delete_at timestamp for {hostname}, resetting.")
                          rule["delete_at"] = None # Or remove the rule?

    except (json.JSONDecodeError, IOError, OSError) as e:
        logging.error(f"Error loading state from {STATE_FILE_PATH}: {e}. Starting fresh.", exc_info=True)
        managed_rules = {} # Start fresh if load fails

def save_state():
    """Saves managed_rules state to file."""
    with state_lock: # Ensure consistent state during save
        try:
            # Convert datetime objects to ISO strings for JSON serialization
            serializable_state = {}
            for hostname, rule in managed_rules.items():
                rule_copy = rule.copy()
                if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
                    rule_copy["delete_at"] = rule_copy["delete_at"].isoformat()
                serializable_state[hostname] = rule_copy

            temp_file_path = STATE_FILE_PATH + ".tmp"
            with open(temp_file_path, 'w') as f:
                json.dump(serializable_state, f, indent=2)
            # Atomic rename
            os.replace(temp_file_path, STATE_FILE_PATH)
            logging.debug(f"Saved state for {len(managed_rules)} rules to {STATE_FILE_PATH}")
        except (IOError, OSError) as e:
            logging.error(f"Error saving state to {STATE_FILE_PATH}: {e}", exc_info=True)


# --- Cloudflare API Helpers ---
def cf_api_request(method, endpoint, json_data=None, params=None):
    """Helper function to make Cloudflare API requests."""
    url = f"{CF_API_BASE_URL}{endpoint}"
    error_msg = None # Initialize error message
    try:
        logging.info(f"API Request: {method} {url} Params: {params} Data: {json_data}")
        response = requests.request(method, url, headers=CF_HEADERS, json=json_data, params=params, timeout=30)
        response.raise_for_status()
        logging.info(f"API Response: {response.status_code}")
        # Handle cases where success might return empty body (e.g., DELETE)
        if response.content:
            return response.json()
        else:
            return {"success": True} # Assume success if no content and status is 2xx
    except requests.exceptions.RequestException as e:
        logging.error(f"API Request Failed: {method} {url}")
        if e.response is not None:
            logging.error(f"Status Code: {e.response.status_code}")
            try: error_data = e.response.json()
            except ValueError: error_data = {"errors": [{"message": e.response.text[:100]}]} # Non-JSON response
            logging.error(f"Response Body: {error_data}")
            cf_errors = error_data.get('errors', [])
            error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}" if cf_errors else f"HTTP {e.response.status_code}"
        else:
            logging.error(f"Error details: {e}")
            error_msg = f"Request Exception: {e}"

        # Store error related to tunnel setup in tunnel_state, others maybe return/raise
        if "cfd_tunnel" in endpoint and tunnel_state.get("id") is None:
             tunnel_state["error"] = error_msg
        raise requests.exceptions.RequestException(error_msg, response=e.response) # Re-raise with details

# --- Tunnel Initialization (API Based) ---
# (find_tunnel_via_api, create_tunnel_via_api, initialize_tunnel remain mostly unchanged
#  from the previous API-based version, just ensure they set tunnel_state correctly)
def find_tunnel_via_api(name):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"name": name, "is_deleted": "false"}
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])
        if tunnels:
            tunnel = tunnels[0]
            tunnel_id = tunnel.get("id")
            logging.info(f"Found existing tunnel '{name}' with ID: {tunnel_id} via API.")
            token = get_tunnel_token_via_api(tunnel_id) # Need token even if exists
            return tunnel_id, token
        else:
            logging.info(f"Tunnel '{name}' not found via API.")
            return None, None
    except Exception as e:
        logging.error(f"Error finding tunnel via API: {e}")
        tunnel_state["error"] = f"Failed finding tunnel: {e}"
        return None, None

def get_tunnel_token_via_api(tunnel_id):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    url = f"{CF_API_BASE_URL}{endpoint}"
    try:
        logging.info(f"API Request: GET {url} (for token)")
        response = requests.request("GET", url, headers=CF_HEADERS, timeout=30)
        response.raise_for_status()
        token = response.text.strip()
        if not token or len(token) < 20: raise ValueError("Invalid token format")
        logging.info(f"Successfully retrieved token via API for tunnel {tunnel_id}")
        return token
    except requests.exceptions.RequestException as e:
        error_msg = f"API Error getting token: {e}"
        if e.response is not None: error_msg += f" Status: {e.response.status_code}"
        logging.error(error_msg, exc_info=True)
        tunnel_state["error"] = error_msg # Set error state
        raise # Re-raise

def create_tunnel_via_api(name):
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    payload = {"name": name, "config_src": "cloudflare"}
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        token = result.get("token")
        if not tunnel_id or not token: raise ValueError("Missing ID or Token in API response")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id} via API.")
        return tunnel_id, token
    except Exception as e:
        logging.error(f"Error creating tunnel via API: {e}")
        tunnel_state["error"] = f"Failed creating tunnel: {e}"
        return None, None

def initialize_tunnel():
    """Sets up tunnel_state using API calls."""
    tunnel_state["status_message"] = f"Checking for tunnel '{TUNNEL_NAME}' via API..."
    tunnel_state["error"] = None
    tunnel_id = None
    token = None
    try:
        tunnel_id, token = find_tunnel_via_api(TUNNEL_NAME)
        if not tunnel_id and not tunnel_state.get("error"):
            tunnel_state["status_message"] = f"Tunnel '{TUNNEL_NAME}' not found. Creating via API..."
            tunnel_id, token = create_tunnel_via_api(TUNNEL_NAME)
        # Ensure token is fetched if find succeeded but didn't return it
        if tunnel_id and not token and not tunnel_state.get("error"):
             token = get_tunnel_token_via_api(tunnel_id)

        if tunnel_id and token:
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = token
            tunnel_state["status_message"] = "Tunnel setup complete (using API)."
            tunnel_state["error"] = None
        elif not tunnel_state.get("error"):
             tunnel_state["status_message"] = "Tunnel initialization failed (API)."
             tunnel_state["error"] = "Failed to find/create tunnel or retrieve token."

    except Exception as e: # Catch errors raised from helpers
        logging.error(f"Error during tunnel initialization: {e}", exc_info=False) # Already logged in helper
        if not tunnel_state.get("error"): tunnel_state["error"] = f"Initialization failed: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (API - see error details)."

# --- Cloudflare Tunnel Configuration Management ---

def get_current_cf_config():
    """Fetches the current tunnel configuration from Cloudflare."""
    if not tunnel_state.get("id"):
        logging.warning("Cannot get CF config, tunnel ID not available.")
        return None
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
    try:
        response = cf_api_request("GET", endpoint)
        # The config is nested under 'result' -> 'config'
        return response.get("result", {}).get("config", {})
    except Exception as e:
        logging.error(f"Failed to get current tunnel config from Cloudflare: {e}")
        return None # Return None on failure

def update_cloudflare_config():
    """
    Pushes the desired state from managed_rules to Cloudflare Tunnel config.
    This function acquires the state_lock.
    """
    if not tunnel_state.get("id"):
        logging.warning("Cannot update Cloudflare config, tunnel ID not available.")
        return False

    with state_lock: # Acquire lock before modifying state or pushing config
        logging.info("Attempting to update Cloudflare tunnel configuration...")
        current_config = get_current_cf_config()
        if current_config is None:
            logging.error("Failed to fetch current config, aborting update.")
            return False

        # Make a deep copy to avoid modifying the fetched dict directly? Not strictly needed
        # current_ingress = current_config.get("ingress", [])
        new_ingress_rules = []
        changed = False
        catch_all_rule = {"service": "http_status:404"} # Default catch-all

        # Build the new ingress list based on our desired state (managed_rules)
        current_hostnames_in_cf = {rule.get("hostname") for rule in current_config.get("ingress", []) if rule.get("hostname")}

        for hostname, rule_details in managed_rules.items():
            if rule_details["status"] == "active":
                desired_rule = {"hostname": hostname, "service": rule_details["service"]}
                # Check if rule exists and matches in current CF config
                found_in_cf = False
                for existing_rule in current_config.get("ingress", []):
                    if existing_rule.get("hostname") == hostname:
                        found_in_cf = True
                        if existing_rule.get("service") != rule_details["service"]:
                            logging.info(f"Updating service for hostname {hostname} in CF config.")
                            changed = True # Mark change even if only service differs
                        break
                if not found_in_cf:
                     logging.info(f"Adding new hostname {hostname} to CF config.")
                     changed = True # Mark change if adding new rule
                new_ingress_rules.append(desired_rule) # Add desired active rule

        # Check if any rules existing in CF are NOT in our active managed_rules
        # These might be manually added or stale from previous runs. We leave them alone for now.
        # Alternatively, could add logic to remove unmanaged rules if strict control is desired.
        for existing_rule in current_config.get("ingress", []):
             # Keep manually added rules (those without hostname or not in our managed state)
             # And keep the catch-all rule (we'll ensure it's last later)
            if not existing_rule.get("hostname") or existing_rule.get("hostname") not in managed_rules:
                 # Except the catch-all, which we handle explicitly
                 if existing_rule.get("service") != catch_all_rule["service"]:
                      logging.debug(f"Keeping unmanaged rule: {existing_rule}")
                      new_ingress_rules.append(existing_rule) # Keep existing rule we don't manage

        # Detect if any active rule was removed from our state but still in CF (shouldn't happen if stop event handled)
        cf_hostnames_to_remove = current_hostnames_in_cf - set(r for r, d in managed_rules.items() if d['status'] == 'active')
        if cf_hostnames_to_remove:
             logging.warning(f"Found hostnames in CF config no longer in active state: {cf_hostnames_to_remove}. Triggering change.")
             # Rules will be implicitly removed by not being added to new_ingress_rules above
             changed = True


        # Ensure the catch-all rule is present and is the LAST rule
        # Remove any existing catch-all rules first
        new_ingress_rules = [rule for rule in new_ingress_rules if rule.get("service") != catch_all_rule["service"]]
        # Add the definitive catch-all rule at the end
        new_ingress_rules.append(catch_all_rule)

        # Compare the final list to the original list (ignoring order of rules before catch-all)
        # A simple length check or set comparison isn't enough due to potential service changes
        # Check if 'changed' flag was set during iteration
        current_cf_rules_no_catchall = [r for r in current_config.get("ingress", []) if r.get("service") != catch_all_rule["service"]]
        new_rules_no_catchall = new_ingress_rules[:-1]

        # More robust check: convert lists of dicts to comparable form (e.g., tuples of sorted items)
        def rule_to_tuple(rule):
            return tuple(sorted(rule.items()))

        if not changed: # Only do expensive comparison if no change detected yet
            if set(map(rule_to_tuple, current_cf_rules_no_catchall)) != set(map(rule_to_tuple, new_rules_no_catchall)):
                logging.info("Detected difference in rule sets.")
                changed = True


        if not changed:
            logging.info("No changes detected in Cloudflare config. Skipping update.")
            return True # Indicate success (no update needed)

        # Push the new configuration
        logging.info("Pushing updated configuration to Cloudflare API...")
        endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_state['id']}/configurations"
        payload = {"config": {"ingress": new_ingress_rules}}
        try:
            cf_api_request("PUT", endpoint, json_data=payload)
            logging.info("Successfully updated Cloudflare tunnel configuration.")
            return True
        except Exception as e:
            logging.error(f"Failed to update Cloudflare tunnel configuration: {e}")
            # Store the error for the UI maybe?
            cloudflared_agent_state["last_action_status"] = f"Error updating CF config: {e}"
            return False # Indicate failure

# --- Docker Event Handling ---

def process_container_start(container):
    """Processes a container start event."""
    if not container: return
    try:
        container.reload() # Get fresh attributes
        labels = container.labels
        container_id = container.id
        container_name = container.name

        enabled = labels.get(f"{LABEL_PREFIX}.enable", "false").lower() == "true"
        hostname = labels.get(f"{LABEL_PREFIX}.hostname")
        service = labels.get(f"{LABEL_PREFIX}.service") # e.g., http://localhost:8000 or http://<container_name>:<port>

        if not enabled:
            logging.debug(f"Ignoring container {container_name} ({container_id[:12]}): Label '{LABEL_PREFIX}.enable' is not 'true'.")
            return

        if not hostname or not service:
            logging.warning(f"Ignoring container {container_name} ({container_id[:12]}): Missing required labels '{LABEL_PREFIX}.hostname' or '{LABEL_PREFIX}.service'.")
            return

        # Validate hostname (basic check)
        if not re.match(r"^[a-zA-Z0-9.-]+$", hostname):
             logging.warning(f"Ignoring container {container_name} ({container_id[:12]}): Invalid hostname format '{hostname}'.")
             return
        # Validate service (basic check - should be URL)
        if not service.startswith(("http://", "https://", "tcp://", "unix:")):
             logging.warning(f"Ignoring container {container_name} ({container_id[:12]}): Invalid service format '{service}'. Expected URL.")
             return

        logging.info(f"Detected start for managed container: {container_name} ({container_id[:12]}) - Hostname: {hostname}, Service: {service}")

        needs_update = False
        with state_lock:
            existing_rule = managed_rules.get(hostname)
            if existing_rule:
                # Rule exists, maybe reactivating or updating
                if existing_rule["status"] == "pending_deletion":
                    logging.info(f"Cancelling pending deletion for hostname {hostname}.")
                    existing_rule["status"] = "active"
                    existing_rule["delete_at"] = None
                    needs_update = True # Config might have been removed by cleanup

                if existing_rule["service"] != service or existing_rule["container_id"] != container_id:
                    logging.info(f"Updating service/container for existing hostname {hostname}.")
                    existing_rule["service"] = service
                    existing_rule["container_id"] = container_id
                    # No need to trigger update here, reconciliation/start handles it if needed
                    # We just update our state. The config push happens if needed.
                    # needs_update = True # Mark change if service differs? Handled by main comparison.

            else:
                # New rule
                logging.info(f"Adding new rule for hostname {hostname}.")
                managed_rules[hostname] = {
                    "service": service,
                    "container_id": container_id,
                    "status": "active",
                    "delete_at": None
                }
                needs_update = True # New rule requires config push

        if needs_update:
             # Update CF config outside the main state lock if possible, or just trigger it
             # Let's trigger an update check which acquires its own lock
             if update_cloudflare_config():
                 save_state() # Save state only after successful push
             else:
                 logging.error(f"Failed to update Cloudflare config after processing start for {hostname}. State may be inconsistent.")
                 # Revert state change? Or retry later? For now, log error.
                 # TODO: Add retry or better error handling
        else:
             # Even if no immediate API update needed, save state if it changed (e.g. pending deletion cancelled)
             save_state()


    except NotFound:
         logging.warning(f"Container {container_id[:12]} not found during processing, likely stopped quickly.")
    except Exception as e:
        logging.error(f"Error processing container start event: {e}", exc_info=True)


def schedule_container_stop(container_id):
    """Schedules a rule for deletion after grace period."""
    logging.info(f"Detected stop for container {container_id[:12]}. Scheduling rule deletion.")
    hostname_to_schedule = None
    with state_lock:
        # Find which hostname belongs to this container
        for hn, details in managed_rules.items():
            if details["container_id"] == container_id and details["status"] == "active":
                hostname_to_schedule = hn
                break

        if hostname_to_schedule:
            logging.info(f"Marking hostname {hostname_to_schedule} for deletion after grace period.")
            rule = managed_rules[hostname_to_schedule]
            rule["status"] = "pending_deletion"
            rule["delete_at"] = datetime.now(timezone.utc) + timedelta(seconds=GRACE_PERIOD_SECONDS)
            save_state() # Save the updated status/timestamp
        else:
            logging.info(f"Container {container_id[:12]} stopped, but no active managed rule found for it.")

def docker_event_listener():
    """Listens for Docker events in a background thread."""
    if not docker_client:
        logging.error("Docker client unavailable, cannot start event listener.")
        return

    logging.info("Starting Docker event listener...")
    try:
        # Get events since the listener started
        events = docker_client.events(decode=True, since=int(time.time()))
        for event in events:
            if stop_event.is_set():
                logging.info("Stop event received, exiting Docker event listener.")
                break

            event_type = event.get("Type")
            action = event.get("Action")
            actor = event.get("Actor", {})
            container_id = actor.get("ID")

            logging.debug(f"Docker Event: Type={event_type}, Action={action}, ActorID={container_id[:12] if container_id else 'N/A'}")

            if event_type == "container" and container_id:
                if action == "start":
                    try:
                        container = docker_client.containers.get(container_id)
                        process_container_start(container)
                    except NotFound:
                        logging.warning(f"Container {container_id[:12]} not found immediately after start event.")
                    except Exception as e:
                        logging.error(f"Error getting container details for {container_id[:12]}: {e}", exc_info=True)
                elif action == "stop" or action == "die": # Treat 'die' similar to stop
                    schedule_container_stop(container_id)

    except Exception as e:
         # Handle exceptions like Docker daemon stopping
         logging.error(f"Error in Docker event listener: {e}", exc_info=True)
         # Maybe attempt to restart the listener after a delay?
    finally:
        logging.info("Docker event listener stopped.")


# --- Cleanup Task ---
def cleanup_expired_rules():
    """Periodically checks for and removes expired rules."""
    logging.info("Starting cleanup task...")
    while not stop_event.is_set():
        try:
            logging.debug("Running cleanup check for expired rules...")
            hostnames_to_remove = []
            now = datetime.now(timezone.utc)

            with state_lock: # Need lock to read state safely
                for hostname, details in managed_rules.items():
                    if details["status"] == "pending_deletion" and details["delete_at"] and details["delete_at"] <= now:
                        logging.info(f"Found expired rule for {hostname} (delete_at: {details['delete_at']}). Scheduling removal.")
                        hostnames_to_remove.append(hostname)

            if hostnames_to_remove:
                logging.info(f"Attempting to remove expired hostnames from Cloudflare: {hostnames_to_remove}")
                # Call update_cloudflare_config which handles fetching current, merging, and PUTting
                # It will implicitly remove the rules not present in the 'active' part of managed_rules
                if update_cloudflare_config():
                    logging.info(f"Cloudflare config updated. Removing expired rules from local state: {hostnames_to_remove}")
                    # Remove from state only after successful API update
                    with state_lock:
                        for hostname in hostnames_to_remove:
                            if hostname in managed_rules: # Check if still exists (could have been reactivated?)
                                # Only remove if still pending deletion
                                if managed_rules[hostname]["status"] == "pending_deletion":
                                    del managed_rules[hostname]
                                else:
                                     logging.warning(f"Rule for {hostname} was no longer pending deletion during cleanup removal. Skipping state deletion.")
                            else:
                                logging.warning(f"Rule for {hostname} was already removed from state before cleanup completion.")
                    save_state() # Save state after removal
                else:
                    logging.error("Failed to update Cloudflare config during cleanup. Expired rules remain in state. Will retry later.")

        except Exception as e:
            logging.error(f"Error in cleanup task: {e}", exc_info=True)

        # Wait for the next interval or until stop event is set
        stop_event.wait(CLEANUP_INTERVAL_SECONDS)

    logging.info("Cleanup task stopped.")


# --- Reconciliation ---
def reconcile_state():
    """Compares Docker state, local state, and CF config on startup."""
    if not docker_client:
        logging.warning("Docker client unavailable, skipping reconciliation.")
        return
    if not tunnel_state.get("id"):
        logging.warning("Tunnel not initialized, skipping reconciliation.")
        return

    logging.info("Starting state reconciliation...")
    needs_update = False
    try:
        with state_lock: # Lock for duration of reconciliation
            # 1. Get current running containers with labels
            running_labeled_containers = {}
            try:
                 containers = docker_client.containers.list()
                 for container in containers:
                     labels = container.labels
                     enabled = labels.get(f"{LABEL_PREFIX}.enable", "false").lower() == "true"
                     hostname = labels.get(f"{LABEL_PREFIX}.hostname")
                     service = labels.get(f"{LABEL_PREFIX}.service")
                     if enabled and hostname and service:
                         running_labeled_containers[hostname] = {
                             "service": service,
                             "container_id": container.id,
                             "container_name": container.name
                         }
                 logging.info(f"Found {len(running_labeled_containers)} running containers with managed labels.")
            except APIError as e:
                logging.error(f"Docker API error listing containers during reconciliation: {e}")
                return # Cannot reconcile without Docker state

            # 2. Get current Cloudflare config
            current_cf_config = get_current_cf_config()
            if current_cf_config is None:
                 logging.error("Cannot reconcile state, failed to get Cloudflare config.")
                 return # Cannot reconcile without CF state
            cf_ingress_rules = {rule.get("hostname"): rule.get("service")
                                for rule in current_cf_config.get("ingress", []) if rule.get("hostname")}
            logging.info(f"Found {len(cf_ingress_rules)} hostnames in current Cloudflare config.")


            # 3. Compare and update managed_rules state
            now = datetime.now(timezone.utc)
            hostnames_processed = set()

            # Check running containers against state
            for hostname, running_details in running_labeled_containers.items():
                hostnames_processed.add(hostname)
                if hostname in managed_rules:
                    rule = managed_rules[hostname]
                    # If running but state says pending delete -> reactivate
                    if rule["status"] == "pending_deletion":
                        logging.info(f"[Reconcile] Reactivating rule for running container: {hostname}")
                        rule["status"] = "active"
                        rule["delete_at"] = None
                        needs_update = True
                    # Update service/container ID if different
                    if rule["service"] != running_details["service"] or rule["container_id"] != running_details["container_id"]:
                        logging.info(f"[Reconcile] Updating state for running container: {hostname}")
                        rule["service"] = running_details["service"]
                        rule["container_id"] = running_details["container_id"]
                        # needs_update = True # Update CF only if service differs from CF actual
                else:
                    # Container running but not in state -> add it
                    logging.info(f"[Reconcile] Adding rule for newly found running container: {hostname}")
                    managed_rules[hostname] = {
                        "service": running_details["service"],
                        "container_id": running_details["container_id"],
                        "status": "active",
                        "delete_at": None
                    }
                    needs_update = True

            # Check state against running containers
            for hostname, rule in list(managed_rules.items()): # Iterate copy for safe deletion
                 hostnames_processed.add(hostname)
                 if rule["status"] == "active" and hostname not in running_labeled_containers:
                      # Active in state, but container not running -> schedule deletion
                      logging.info(f"[Reconcile] Container for active rule {hostname} not running. Scheduling deletion.")
                      rule["status"] = "pending_deletion"
                      rule["delete_at"] = now + timedelta(seconds=GRACE_PERIOD_SECONDS)
                      # Needs update only if rule exists in CF and needs removal eventually
                 elif rule["status"] == "pending_deletion" and hostname in running_labeled_containers:
                      # Pending delete in state, but container IS running -> reactivate
                      logging.info(f"[Reconcile] Container for pending deletion rule {hostname} is running. Reactivating.")
                      rule["status"] = "active"
                      rule["delete_at"] = None
                      needs_update = True # Needs potential update if rule was removed by cleanup

            # 4. Compare desired state (managed_rules 'active') with CF config (implicit in update_cloudflare_config)
            # Just trigger the update function which does the final comparison and push
            if needs_update:
                 logging.info("[Reconcile] State changes detected, triggering Cloudflare config update.")
                 if update_cloudflare_config():
                     save_state() # Save updated state after successful push
                 else:
                     logging.error("[Reconcile] Failed to update Cloudflare config after reconciliation.")
            else:
                 # Even if no state changes, run update_cloudflare_config once to ensure CF matches state
                 logging.info("[Reconcile] No state changes, ensuring Cloudflare config matches current state.")
                 update_cloudflare_config()


            logging.info("Reconciliation complete.")

    except Exception as e:
        logging.error(f"Error during state reconciliation: {e}", exc_info=True)


# --- Docker Container Management ---
# (get_cloudflared_container, start_cloudflared_container, stop_cloudflared_container remain unchanged)
# ... (paste the Docker control functions from previous versions here) ...
def get_cloudflared_container():
    """Gets the cloudflared container object if it exists."""
    if not docker_client: logging.warning("Docker client not available."); return None
    try: return docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
    except NotFound: return None
    except APIError as e: logging.error(f"Docker API error getting container: {e}"); cloudflared_agent_state["last_action_status"] = f"Error: Docker API error {e}"; return None

def update_cloudflared_container_status():
    """Updates the agent_state with the current container status."""
    if not docker_client: cloudflared_agent_state["container_status"] = "docker_unavailable"; return
    container = get_cloudflared_container()
    if container:
        try: container.reload(); cloudflared_agent_state["container_status"] = container.status
        except (NotFound, APIError) as e: logging.warning(f"Error reloading container status: {e}"); cloudflared_agent_state["container_status"] = "not_found"
    else: cloudflared_agent_state["container_status"] = "not_found"

def start_cloudflared_container():
    """Starts the cloudflared agent container using the token from tunnel_state."""
    cloudflared_agent_state["last_action_status"] = None
    if not docker_client: msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
    if not tunnel_state.get("token"): msg = "Tunnel token not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
    token = tunnel_state["token"]
    container = get_cloudflared_container()
    try:
        if container:
            if container.status == 'running': msg = f"Already running."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; return True
            else: logging.info(f"Starting existing container..."); container.start(); msg = f"Started existing."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg)
        else:
            logging.info(f"Container not found. Creating and starting...")
            try: logging.info(f"Pulling image {CLOUDFLARED_IMAGE}..."); docker_client.images.pull(CLOUDFLARED_IMAGE)
            except APIError as img_err: logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Proceeding.")
            new_container = docker_client.containers.run( image=CLOUDFLARED_IMAGE, command=f"tunnel --no-autoupdate run --token {token}", name=CLOUDFLARED_CONTAINER_NAME, network_mode="host", restart_policy={"Name": "unless-stopped"}, detach=True, remove=False )
            msg = f"Created and started container '{new_container.name}'."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg)
        time.sleep(2); update_cloudflared_container_status(); return True
    except APIError as e: msg = f"Docker API error starting: {e}"; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; update_cloudflared_container_status(); return False
    except Exception as e: msg = f"Unexpected error starting: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; update_cloudflared_container_status(); return False

def stop_cloudflared_container():
    """Stops the cloudflared agent container."""
    cloudflared_agent_state["last_action_status"] = None
    if not docker_client: msg = "Docker client not available."; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; return False
    container = get_cloudflared_container()
    if not container: msg = f"Not found."; logging.warning(msg); cloudflared_agent_state["last_action_status"] = msg; update_cloudflared_container_status(); return True
    if container.status != 'running': msg = f"Not running (status: {container.status})."; logging.info(msg); cloudflared_agent_state["last_action_status"] = msg; update_cloudflared_container_status(); return True
    try: logging.info(f"Stopping container..."); container.stop(timeout=30); msg = f"Stopped."; cloudflared_agent_state["last_action_status"] = msg; logging.info(msg); time.sleep(2); update_cloudflared_container_status(); return True
    except APIError as e: msg = f"Docker API error stopping: {e}"; logging.error(msg); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; update_cloudflared_container_status(); return False
    except Exception as e: msg = f"Unexpected error stopping: {e}"; logging.error(msg, exc_info=True); cloudflared_agent_state["last_action_status"] = f"Error: {msg}"; update_cloudflared_container_status(); return False


# --- Flask Web Server ---
app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def status_page():
    """Displays the current tunnel status and controls."""
    update_cloudflared_container_status()
    # Make a copy of managed_rules for safe iteration in template
    with state_lock:
        template_rules = json.loads(json.dumps(managed_rules, default=str)) # Serialize datetimes for display

    display_token = "Not available"
    if tunnel_state.get("token"):
        token = tunnel_state["token"]
        if len(token) > 10: display_token = f"{token[:5]}...{token[-5:]}"
        else: display_token = "Token retrieved (short)"

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cloudflare Tunnel Manager</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background-color: #f4f4f4; color: #333; }
            h1, h2, h3 { color: #555; }
            .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            td pre { margin: 0; background-color: transparent; padding: 0; white-space: pre-wrap; word-break: break-all;}
            .status-box { padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; word-wrap: break-word; }
            .error { background-color: #ffebeb; border-color: #ffc2c2; color: #a00; }
            .success { background-color: #e6ffed; border-color: #c3e6cb; color: #155724;}
            .info { background-color: #e7f3fe; border-color: #b8daff; color: #004085;}
            .warning { background-color: #fff3cd; border-color: #ffeeba; color: #856404;}
            .status-active { color: green; }
            .status-pending { color: orange; }
            .button { padding: 10px 15px; border: none; border-radius: 4px; color: white; cursor: pointer; font-size: 1em; margin-right: 10px; }
            .start-button { background-color: #28a745; }
            .stop-button { background-color: #dc3545; }
            .button:disabled { background-color: #cccccc; cursor: not-allowed; opacity: 0.6; }
            form { display: inline-block; }
        </style>
    </head>
    <body>
        <h1>Cloudflare Tunnel Manager</h1>

        <!-- Initialization & Tunnel Details -->
        <div class="container">
            <h2>Initialization Status</h2>
            <div class="status-box {{ 'error' if tunnel_state.get('error') else ('success' if tunnel_state.get('token') else 'info') }}">
                <p><strong>Message:</strong> {{ tunnel_state.status_message }}</p>
                {% if tunnel_state.get('error') %}
                <p><strong>Error Details:</strong> <pre>{{ tunnel_state.error }}</pre></p>
                {% endif %}
            </div>
            <h3>Tunnel Details</h3>
            <p><strong>Desired Tunnel Name:</strong> <pre>{{ tunnel_state.name }}</pre></p>
            <p><strong>Tunnel ID:</strong> <pre>{{ tunnel_state.id if tunnel_state.id else 'Not available' }}</pre></p>
            <p><strong>Tunnel Token:</strong> <pre>{{ display_token }}</pre></p>
        </div>

        <!-- Agent Control -->
        <div class="container">
             <h2>Tunnel Agent Control (<pre>{{ cloudflared_container_name }}</pre>)</h2>
             <p><strong>Agent Container Status:</strong>
                <strong style="text-transform: capitalize;"
                        class="{{ 'success' if agent_state.container_status == 'running' else ('error' if 'error' in agent_state.container_status or 'unavailable' in agent_state.container_status or agent_state.container_status == 'dead' else ('warning' if agent_state.container_status == 'exited' else 'info')) }}">
                  {{ agent_state.container_status.replace('_', ' ') }}
                </strong>
             </p>
             {% if agent_state.last_action_status %}
             <div class="status-box {{ 'error' if 'Error' in agent_state.last_action_status else 'info' }}">
                <strong>Last Action Result:</strong> {{ agent_state.last_action_status }}
             </div>
             {% endif %}
             <form action="{{ url_for('start_tunnel') }}" method="post" style="margin-right: 10px;">
                <button type="submit" class="button start-button"
                        {{ 'disabled' if not tunnel_state.get('token') or agent_state.container_status == 'running' or not docker_client }}>
                    Start Tunnel Agent</button>
             </form>
             <form action="{{ url_for('stop_tunnel') }}" method="post">
                <button type="submit" class="button stop-button"
                        {{ 'disabled' if agent_state.container_status != 'running' or not docker_client }}>
                    Stop Tunnel Agent</button>
             </form>
        </div>

        <!-- Managed Rules -->
        <div class="container">
            <h2>Managed Ingress Rules</h2>
            {% if rules %}
            <table>
                <thead>
                    <tr>
                        <th>Hostname</th>
                        <th>Service Target</th>
                        <th>Status</th>
                        <th>Managing Container</th>
                        <th>Delete Scheduled At (UTC)</th>
                    </tr>
                </thead>
                <tbody>
                    {% for hostname, details in rules.items() %}
                    <tr>
                        <td><pre>{{ hostname }}</pre></td>
                        <td><pre>{{ details.service }}</pre></td>
                        <td><strong class="{{ 'status-active' if details.status == 'active' else 'status-pending' }}">{{ details.status }}</strong></td>
                        <td><pre>{{ details.container_id[:12] if details.container_id else 'N/A' }}</pre></td>
                        <td>{{ details.delete_at if details.status == 'pending_deletion' else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p>No ingress rules are currently being managed based on container labels.</p>
            {% endif %}
        </div>

    </body>
    </html>
    """
    return render_template_string(
        html_template,
        tunnel_state=tunnel_state,
        agent_state=cloudflared_agent_state,
        display_token=display_token,
        cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
        docker_client=docker_client,
        rules=template_rules # Pass the managed rules to the template
    )

@app.route('/start', methods=['POST'])
def start_tunnel():
    start_cloudflared_container()
    return redirect(url_for('status_page'))

@app.route('/stop', methods=['POST'])
def stop_tunnel():
    stop_cloudflared_container()
    return redirect(url_for('status_page'))

# --- Main Execution ---
if __name__ == '__main__':
    load_state() # Load previous state first

    try:
        initialize_tunnel() # Setup tunnel entity, get ID and token
    except Exception as init_err:
        logging.error(f"Unexpected error during initial tunnel setup: {init_err}", exc_info=True)
        # Allow app to continue running, but show error

    if tunnel_state.get("id") and tunnel_state.get("token"):
         # Only reconcile and start agent if tunnel is ready
         try:
            reconcile_state() # Sync state on startup
         except Exception as recon_err:
              logging.error(f"Error during initial reconciliation: {recon_err}", exc_info=True)

         # --- Automatically Start Tunnel Agent ---
         logging.info("Attempting to automatically start tunnel agent...")
         if start_cloudflared_container():
             logging.info("Tunnel agent started successfully on startup.")
         else:
             logging.warning("Failed to automatically start tunnel agent on startup.")
             # Error message is set in start_cloudflared_container
    else:
        logging.warning("Tunnel not fully initialized, skipping agent start and background tasks.")


    if docker_client and tunnel_state.get("id"):
        # Start background threads only if Docker and Tunnel are ready
        logging.info("Starting background threads for Docker events and cleanup.")
        event_thread = threading.Thread(target=docker_event_listener, name="DockerEventListener", daemon=True)
        cleanup_thread = threading.Thread(target=cleanup_expired_rules, name="CleanupTask", daemon=True)
        event_thread.start()
        cleanup_thread.start()
    elif not docker_client:
         logging.warning("Docker client not available, background tasks disabled.")
    else: # Tunnel not ready
         logging.warning("Tunnel not initialized, background tasks disabled.")

    # Run Flask app
    logging.info("Starting Flask application server.")
    # Consider using a production WSGI server like Gunicorn or Waitress
    app.run(host='0.0.0.0', port=5000, use_reloader=False) # use_reloader=False important with threads

    # --- Cleanup on Exit (Optional - Basic) ---
    logging.info("Flask app stopping, signalling background threads...")
    stop_event.set()
    # Ideally wait for threads to finish, but daemon=True means they exit with main
    logging.info("Exiting application.")