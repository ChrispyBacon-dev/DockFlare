import os
import sys
import logging
import re
import docker # Docker SDK
from docker.errors import NotFound, APIError
from flask import Flask, jsonify, render_template_string, redirect, url_for, request
from dotenv import load_dotenv
import time
import requests # <-- Import requests library

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

CF_API_TOKEN = os.getenv('CF_API_TOKEN')
TUNNEL_NAME = os.getenv('TUNNEL_NAME')
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"

# --- Environment Variable Checks ---
if not CF_API_TOKEN:
    logging.error("FATAL: CF_API_TOKEN environment variable not set.")
    sys.exit(1)
if not TUNNEL_NAME:
    logging.error("FATAL: TUNNEL_NAME environment variable not set.")
    sys.exit(1)
if not CF_ACCOUNT_ID:
    logging.error("FATAL: CF_ACCOUNT_ID environment variable not set.")
    sys.exit(1)

# --- Cloudflare API Configuration ---
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}

# --- Docker Client ---
try:
    docker_client = docker.from_env()
    docker_client.ping()
    logging.info("Successfully connected to Docker daemon.")
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    docker_client = None

# --- Global State ---
tunnel_state = {
    "name": TUNNEL_NAME,
    "id": None,
    "token": None, # This will now come from the API create response
    "status_message": "Initializing...",
    "error": None,
    "cloudflared_container_status": "unknown",
    "last_action_status": None,
}

# --- Cloudflare API Helpers ---

def cf_api_request(method, endpoint, json_data=None, params=None):
    """Helper function to make Cloudflare API requests."""
    url = f"{CF_API_BASE_URL}{endpoint}"
    try:
        logging.info(f"Making API request: {method} {url} Params: {params} Data: {json_data}")
        response = requests.request(
            method,
            url,
            headers=CF_HEADERS,
            json=json_data,
            params=params,
            timeout=30 # Add a timeout
            )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logging.info(f"API request successful (Status: {response.status_code})")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Cloudflare API request failed: {method} {url}")
        if e.response is not None:
            logging.error(f"Status Code: {e.response.status_code}")
            try:
                error_data = e.response.json()
                logging.error(f"Response Body: {error_data}")
                # Extract Cloudflare specific errors if possible
                cf_errors = error_data.get('errors', [])
                error_msg = f"API Error: {cf_errors[0].get('message', 'Unknown error')}" if cf_errors else f"HTTP {e.response.status_code}"
            except ValueError: # If response body is not JSON
                error_msg = f"HTTP {e.response.status_code} - Non-JSON response: {e.response.text}"
        else:
            logging.error(f"Error details: {e}")
            error_msg = f"Request Exception: {e}"
        tunnel_state["error"] = error_msg # Store the error
        raise # Re-raise the exception to be handled by the caller

# --- Tunnel Management Logic (using API) ---

def find_tunnel_via_api(name):
    """Finds a tunnel by name using the API."""
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    params = {"name": name, "is_deleted": "false"} # Filter by name and ensure not deleted
    try:
        response_data = cf_api_request("GET", endpoint, params=params)
        tunnels = response_data.get("result", [])
        if tunnels:
            tunnel = tunnels[0] # Assume first match is the one
            tunnel_id = tunnel.get("id")
            logging.info(f"Found existing tunnel '{name}' with ID: {tunnel_id} via API.")
            # We need the TOKEN here too if it already exists.
            # The list endpoint doesn't return the token.
            # We need to call the specific tunnel GET or the token endpoint.
            token = get_tunnel_token_via_api(tunnel_id)
            return tunnel_id, token
        else:
            logging.info(f"Tunnel '{name}' not found via API.")
            return None, None
    except Exception as e:
        logging.error(f"Error finding tunnel via API: {e}")
        # Error state is set within cf_api_request helper
        return None, None # Indicate failure

def get_tunnel_token_via_api(tunnel_id):
    """Gets the tunnel token using the API endpoint."""
    # Note: Documentation implies create returns token, but if tunnel exists, we need it.
    # Let's try the dedicated token endpoint if it exists (check API docs)
    # Alternatively, the GET /cfd_tunnel/{tunnel_id} might return it? Let's assume create is primary source for now.
    # UPDATE: The docs show a dedicated GET token endpoint!
    # https://developers.cloudflare.com/api/resources/zero_trust/subresources/tunnels/subresources/cloudflared/subresources/token/methods/get/
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel/{tunnel_id}/token"
    try:
        # This endpoint seems to return the token directly as a string in the response body
        url = f"{CF_API_BASE_URL}{endpoint}"
        logging.info(f"Making API request: GET {url} (for token)")
        response = requests.request("GET", url, headers=CF_HEADERS, timeout=30)
        response.raise_for_status()
        token = response.text.strip() # Get raw text response
        if not token or len(token) < 20: # Basic sanity check
             raise ValueError("Invalid token format received from API")
        logging.info(f"Successfully retrieved token via API for tunnel {tunnel_id}")
        return token
    except requests.exceptions.RequestException as e:
        logging.error(f"Cloudflare API request failed getting token: GET {url}")
        if e.response is not None:
            logging.error(f"Status Code: {e.response.status_code}")
            try:
                error_data = e.response.json()
                logging.error(f"Response Body: {error_data}")
                cf_errors = error_data.get('errors', [])
                error_msg = f"API Error getting token: {cf_errors[0].get('message', 'Unknown error')}" if cf_errors else f"HTTP {e.response.status_code}"
            except ValueError:
                error_msg = f"HTTP {e.response.status_code} - Non-JSON response: {e.response.text}"
        else:
            logging.error(f"Error details: {e}")
            error_msg = f"Request Exception getting token: {e}"
        tunnel_state["error"] = error_msg
        raise # Re-raise

def create_tunnel_via_api(name):
    """Creates a tunnel using the API and returns its ID and Token."""
    endpoint = f"/accounts/{CF_ACCOUNT_ID}/cfd_tunnel"
    payload = {"name": name, "config_src": "cloudflare"} # As per docs
    try:
        response_data = cf_api_request("POST", endpoint, json_data=payload)
        result = response_data.get("result", {})
        tunnel_id = result.get("id")
        # The docs show the token is returned directly in the 'result' object
        token = result.get("token")
        if not tunnel_id or not token:
            logging.error(f"API response missing 'id' or 'token': {response_data}")
            raise ValueError("Missing ID or Token in API response")
        logging.info(f"Successfully created tunnel '{name}' with ID {tunnel_id} via API.")
        return tunnel_id, token
    except Exception as e:
        logging.error(f"Error creating tunnel via API: {e}")
        # Error state is set within cf_api_request helper
        return None, None # Indicate failure

def initialize_tunnel():
    """Checks for the tunnel via API, creates if needed, and gets token."""
    tunnel_state["status_message"] = f"Checking for tunnel '{TUNNEL_NAME}' via API..."
    tunnel_state["error"] = None
    tunnel_id = None
    token = None

    try:
        tunnel_id, token = find_tunnel_via_api(TUNNEL_NAME)

        if not tunnel_id and not tunnel_state.get("error"): # Only create if find didn't error
            tunnel_state["status_message"] = f"Tunnel '{TUNNEL_NAME}' not found. Creating via API..."
            tunnel_id, token = create_tunnel_via_api(TUNNEL_NAME)
            if not tunnel_id:
                 # create_tunnel_via_api already set the error state
                 tunnel_state["status_message"] = "Failed to create tunnel via API (see error details)."
                 return

        # If we have an ID but didn't get token from find_tunnel (or create failed somehow)
        if tunnel_id and not token:
             logging.warning(f"Tunnel ID {tunnel_id} found/created, but token is missing. Attempting explicit token fetch.")
             # This path might be redundant if create_tunnel_via_api always returns token on success
             token = get_tunnel_token_via_api(tunnel_id)


        if tunnel_id and token:
            tunnel_state["id"] = tunnel_id
            tunnel_state["token"] = token
            tunnel_state["status_message"] = "Tunnel setup complete (using API)."
            tunnel_state["error"] = None # Clear errors on success
        elif not tunnel_state.get("error"): # If we finished without success and no error recorded
             tunnel_state["status_message"] = "Tunnel initialization failed (API)."
             tunnel_state["error"] = "Failed to find/create tunnel or retrieve token via API."

    except Exception as e:
        # Catch errors raised from the API helper functions
        logging.error(f"Error during tunnel initialization: {e}", exc_info=True)
        if not tunnel_state.get("error"): # Set general error if specific one wasn't set
            tunnel_state["error"] = f"Initialization failed: {e}"
        tunnel_state["status_message"] = "Tunnel initialization failed (API - see error details)."


# --- Docker Container Management ---
# (This section remains unchanged - it uses the 'token' from tunnel_state)
def get_cloudflared_container():
    """Gets the cloudflared container object if it exists."""
    if not docker_client:
        logging.warning("Docker client not available.")
        return None
    try:
        container = docker_client.containers.get(CLOUDFLARED_CONTAINER_NAME)
        return container
    except NotFound:
        return None
    except APIError as e:
        logging.error(f"Docker API error getting container: {e}")
        tunnel_state["error"] = f"Docker API error: {e}"
        return None

def update_cloudflared_container_status():
    """Updates the tunnel_state with the current container status."""
    if not docker_client:
        tunnel_state["cloudflared_container_status"] = "docker_unavailable"
        return
    container = get_cloudflared_container()
    if container:
        try:
            container.reload()
            tunnel_state["cloudflared_container_status"] = container.status
        except (NotFound, APIError) as e:
            logging.warning(f"Error reloading container status: {e}")
            tunnel_state["cloudflared_container_status"] = "not_found"
    else:
        if "Docker API error" not in str(tunnel_state.get("error", "")):
             tunnel_state["cloudflared_container_status"] = "not_found"
        else:
             tunnel_state["cloudflared_container_status"] = "docker_error"


def start_cloudflared_container():
    """Starts the cloudflared agent container using the token from tunnel_state."""
    tunnel_state["last_action_status"] = None
    if not docker_client:
        msg = "Docker client not available. Cannot start container."
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False
    if not tunnel_state.get("token"): # Check if token was retrieved via API
        msg = "Tunnel token not available (API init likely failed). Cannot start container."
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        # Optionally, try re-initializing here?
        # initialize_tunnel()
        # if not tunnel_state.get("token"): return False
        return False


    token = tunnel_state["token"]
    container = get_cloudflared_container()

    try:
        if container:
            if container.status == 'running':
                msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is already running."
                logging.info(msg)
                tunnel_state["last_action_status"] = msg
                return True
            else:
                logging.info(f"Starting existing container '{CLOUDFLARED_CONTAINER_NAME}'...")
                container.start()
                tunnel_state["last_action_status"] = f"Successfully started container '{CLOUDFLARED_CONTAINER_NAME}'."
                logging.info(tunnel_state["last_action_status"])
                time.sleep(2)
                update_cloudflared_container_status()
                return True
        else:
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found. Creating and starting...")
            try:
                logging.info(f"Pulling image {CLOUDFLARED_IMAGE}...")
                docker_client.images.pull(CLOUDFLARED_IMAGE)
            except APIError as img_err:
                 logging.warning(f"Could not pull image {CLOUDFLARED_IMAGE}: {img_err}. Proceeding with local version if available.")

            # THIS is where we use the cloudflared binary via Docker, with the API-obtained token
            new_container = docker_client.containers.run(
                image=CLOUDFLARED_IMAGE,
                command=f"tunnel --no-autoupdate run --token {token}", # Use the API token
                name=CLOUDFLARED_CONTAINER_NAME,
                network_mode="host",
                restart_policy={"Name": "unless-stopped"},
                detach=True,
                remove=False
            )
            tunnel_state["last_action_status"] = f"Successfully created and started container '{new_container.name}'."
            logging.info(tunnel_state["last_action_status"])
            time.sleep(2)
            update_cloudflared_container_status()
            return True
    except APIError as e:
        msg = f"Docker API error starting container: {e}"
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        update_cloudflared_container_status()
        return False
    except Exception as e:
        msg = f"Unexpected error starting container: {e}"
        logging.error(msg, exc_info=True)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        update_cloudflared_container_status()
        return False


def stop_cloudflared_container():
    """Stops the cloudflared agent container."""
    # (No changes needed here)
    tunnel_state["last_action_status"] = None
    if not docker_client:
        msg = "Docker client not available. Cannot stop container."
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False

    container = get_cloudflared_container()

    if not container:
        msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found. Cannot stop."
        logging.warning(msg)
        tunnel_state["last_action_status"] = msg
        update_cloudflared_container_status()
        return True

    if container.status != 'running':
        msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is not running (status: {container.status})."
        logging.info(msg)
        tunnel_state["last_action_status"] = msg
        update_cloudflared_container_status()
        return True

    try:
        logging.info(f"Stopping container '{CLOUDFLARED_CONTAINER_NAME}'...")
        container.stop(timeout=30)
        tunnel_state["last_action_status"] = f"Successfully stopped container '{CLOUDFLARED_CONTAINER_NAME}'."
        logging.info(tunnel_state["last_action_status"])
        time.sleep(2)
        update_cloudflared_container_status()
        return True
    except APIError as e:
        msg = f"Docker API error stopping container: {e}"
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        update_cloudflared_container_status()
        return False
    except Exception as e:
        msg = f"Unexpected error stopping container: {e}"
        logging.error(msg, exc_info=True)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        update_cloudflared_container_status()
        return False

# --- Flask Web Server ---
# (No changes needed in Flask routes or template)
app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def status_page():
    """Displays the current tunnel status and controls."""
    update_cloudflared_container_status()
    display_token = "Not available"
    if tunnel_state.get("token"):
        token = tunnel_state["token"]
        if len(token) > 10: display_token = f"{token[:5]}...{token[-5:]}"
        else: display_token = "Token retrieved (short)"
    elif tunnel_state.get("error") and "token" in tunnel_state["error"].lower(): display_token = "Failed to retrieve token"
    elif tunnel_state.get("id"): display_token = "Token not retrieved"
    display_error = tunnel_state.get("error") or (tunnel_state.get("last_action_status") and "Error" in tunnel_state["last_action_status"])
    html_template = """<!DOCTYPE html><html><head><title>Cloudflare Tunnel Status</title><style>body{font-family:sans-serif;padding:20px;background-color:#f4f4f4;color:#333}h1,h2{color:#555}.container{background-color:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);margin-bottom:20px}.status-box{padding:10px;border:1px solid #ccc;border-radius:5px;margin-top:10px;word-wrap:break-word}.error{background-color:#ffebeb;border-color:#ffc2c2;color:#a00}.success{background-color:#e6ffed;border-color:#c3e6cb;color:#155724}.info{background-color:#e7f3fe;border-color:#b8daff;color:#004085}.warning{background-color:#fff3cd;border-color:#ffeeba;color:#856404}pre{background-color:#eee;padding:10px;border-radius:3px;word-wrap:break-word;white-space:pre-wrap}.button{padding:10px 15px;border:none;border-radius:4px;color:#fff;cursor:pointer;font-size:1em;margin-right:10px}.start-button{background-color:#28a745}.stop-button{background-color:#dc3545}.button:disabled{background-color:#ccc;cursor:not-allowed;opacity:.6}form{display:inline-block}</style></head><body><h1>Cloudflare Tunnel Manager</h1><div class="container"><h2>Initialization Status</h2><div class="status-box {{'error' if error else ('success' if token else 'info')}}"><p><strong>Message:</strong> {{status_message}}</p>{% if error %}<p><strong>Error Details:</strong> <pre>{{error}}</pre></p>{% endif %}</div><h3>Tunnel Details</h3><p><strong>Desired Tunnel Name:</strong> <pre>{{name}}</pre></p><p><strong>Tunnel ID:</strong> <pre>{{id if id else 'Not available'}}</pre></p><p><strong>Tunnel Token:</strong> <pre>{{display_token}}</pre></p><p><small>Note: Full token must be available internally to start the tunnel agent.</small></p></div><div class="container"><h2>Tunnel Agent Control (<pre>{{cloudflared_container_name}}</pre>)</h2><p><strong>Agent Container Status:</strong> <strong style="text-transform:capitalize" class="{{'success' if cloudflared_container_status=='running' else ('error' if 'error' in cloudflared_container_status or 'unavailable' in cloudflared_container_status or cloudflared_container_status=='dead' else ('warning' if cloudflared_container_status=='exited' else 'info'))}}">{{cloudflared_container_status.replace('_',' ')}}</strong></p>{% if last_action_status %}<div class="status-box {{'error' if 'Error' in last_action_status else 'info'}}"><strong>Last Action Result:</strong> {{last_action_status}}</div>{% endif %}<form action="{{url_for('start_tunnel')}}" method="post" style="margin-right:10px"><button type="submit" class="button start-button" {{'disabled' if not token or cloudflared_container_status=='running' or not docker_client}}>Start Tunnel Agent</button></form><form action="{{url_for('stop_tunnel')}}" method="post"><button type="submit" class="button stop-button" {{'disabled' if cloudflared_container_status!='running' or not docker_client}}>Stop Tunnel Agent</button></form><p><small>Agent control requires connection to Docker daemon.</small></p></div></body></html>"""
    return render_template_string(html_template, name=tunnel_state["name"], id=tunnel_state.get("id"), status_message=tunnel_state["status_message"], error=tunnel_state.get("error"), display_token=display_token, token=tunnel_state.get("token"), cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME, cloudflared_container_status=tunnel_state["cloudflared_container_status"], last_action_status=tunnel_state.get("last_action_status"), docker_client=docker_client)

@app.route('/start', methods=['POST'])
def start_tunnel():
    logging.info("Received request to start tunnel agent.")
    start_cloudflared_container()
    return redirect(url_for('status_page'))

@app.route('/stop', methods=['POST'])
def stop_tunnel():
    logging.info("Received request to stop tunnel agent.")
    stop_cloudflared_container()
    return redirect(url_for('status_page'))

# --- Main Execution ---
if __name__ == '__main__':
    try:
         initialize_tunnel()
    except Exception as init_err:
         logging.error(f"Unexpected error during initial tunnel setup: {init_err}", exc_info=True)
         if not tunnel_state.get("error"): tunnel_state["error"] = f"Initialization failed: {init_err}"
         tunnel_state["status_message"] = "Tunnel initialization failed."

    if docker_client:
        try: update_cloudflared_container_status()
        except Exception as docker_err:
            logging.error(f"Error getting initial Docker status: {docker_err}", exc_info=True)
            tunnel_state["cloudflared_container_status"] = "docker_error"

    logging.info("Starting Flask application server.")
    app.run(host='0.0.0.0', port=5000)