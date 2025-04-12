import os
import subprocess
import sys
import logging
import re
import docker # <-- Import Docker SDK
from docker.errors import NotFound, APIError
from flask import Flask, jsonify, render_template_string, redirect, url_for, request
from dotenv import load_dotenv
import time # For potential waits

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

CF_API_TOKEN = os.getenv('CF_API_TOKEN')
TUNNEL_NAME = os.getenv('TUNNEL_NAME')
# Name for the separate cloudflared container we will manage
CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
# Cloudflared Docker image
CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"

if not CF_API_TOKEN:
    logging.error("FATAL: CF_API_TOKEN environment variable not set.")
    sys.exit(1)
if not TUNNEL_NAME:
    logging.error("FATAL: TUNNEL_NAME environment variable not set.")
    sys.exit(1)

# --- Docker Client ---
try:
    docker_client = docker.from_env()
    docker_client.ping() # Check connection
    logging.info("Successfully connected to Docker daemon.")
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    logging.error("Ensure Docker is running and the socket is mounted correctly if applicable.")
    # Note: In Docker Compose with socket mount, this usually works unless Docker daemon is down.
    # We won't exit here, maybe Docker starts later, but functions will fail.
    docker_client = None


# --- Global State ---
tunnel_state = {
    "name": TUNNEL_NAME,
    "id": None,
    "token": None,
    "status_message": "Initializing...",
    "error": None,
    "cloudflared_container_status": "unknown", # e.g., running, exited, not_found
    "last_action_status": None, # Feedback after start/stop
}

# --- Cloudflared CLI Helper (Unchanged from previous version) ---
def run_cloudflared_command(command_args):
    command = ['cloudflared'] + command_args
    env = os.environ.copy()
    env['CF_API_TOKEN'] = CF_API_TOKEN
    env['NONINTERACTIVE'] = '1'
    logging.info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, env=env, timeout=60)
        logging.info(f"Command successful. stdout:\n{result.stdout}")
        if result.stderr:
             logging.warning(f"Command stderr:\n{result.stderr}")
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {' '.join(command)}")
        logging.error(f"Return code: {e.returncode}\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logging.error(f"Command timed out: {' '.join(command)}")
        raise
    except Exception as e:
        logging.error(f"Error running command {' '.join(command)}: {e}")
        raise

# --- Tunnel Management Logic (Unchanged, just sets state) ---
def find_tunnel_id(name):
    try:
        stdout, _ = run_cloudflared_command(['tunnel', 'list'])
        lines = stdout.splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == name:
                tunnel_id = parts[0]
                logging.info(f"Found existing tunnel '{name}' with ID: {tunnel_id}")
                return tunnel_id
    except Exception as e:
        logging.error(f"Failed to list tunnels: {e}")
        tunnel_state["error"] = f"Failed to list tunnels: {e}"
    return None

def create_tunnel(name):
    try:
        stdout, _ = run_cloudflared_command(['tunnel', 'create', name])
        match = re.search(r'with id\s+([a-f0-9-]+)', stdout)
        if match:
            tunnel_id = match.group(1)
            logging.info(f"Successfully created tunnel '{name}' with ID: {tunnel_id}")
            return tunnel_id
        else:
             logging.error(f"Could not parse tunnel ID from creation output: {stdout}")
             tunnel_state["error"] = "Could not parse tunnel ID from creation output."
             return None
    except Exception as e:
        logging.error(f"Failed to create tunnel '{name}': {e}")
        tunnel_state["error"] = f"Failed to create tunnel: {e}"
        return None

def get_tunnel_token(tunnel_identifier):
    try:
        token, _ = run_cloudflared_command(['tunnel', 'token', tunnel_identifier])
        logging.info(f"Successfully retrieved token for tunnel: {tunnel_identifier}")
        return token
    except Exception as e:
        logging.error(f"Failed to get token for tunnel '{tunnel_identifier}': {e}")
        tunnel_state["error"] = f"Failed to get token: {e}"
        return None

def initialize_tunnel():
    """Checks for the tunnel, creates if needed, and gets the token."""
    tunnel_state["status_message"] = f"Checking for tunnel '{TUNNEL_NAME}'..."
    tunnel_id = find_tunnel_id(TUNNEL_NAME)

    if not tunnel_id:
        tunnel_state["status_message"] = f"Tunnel '{TUNNEL_NAME}' not found. Creating..."
        tunnel_id = create_tunnel(TUNNEL_NAME)
        if not tunnel_id:
            tunnel_state["status_message"] = "Failed to create tunnel."
            return

    tunnel_state["id"] = tunnel_id
    tunnel_state["status_message"] = f"Fetching token for tunnel ID {tunnel_id}..."
    token = get_tunnel_token(tunnel_id)

    if token:
        tunnel_state["token"] = token
        tunnel_state["status_message"] = "Tunnel setup complete."
        tunnel_state["error"] = None
    else:
        tunnel_state["status_message"] = "Failed to retrieve tunnel token."

# --- Docker Container Management ---

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
    container = get_cloudflared_container()
    if container:
        tunnel_state["cloudflared_container_status"] = container.status
    else:
        # Check if the error state already indicates a Docker problem
        if "Docker API error" not in str(tunnel_state["error"]):
             tunnel_state["cloudflared_container_status"] = "not_found"


def start_cloudflared_container():
    """Starts the cloudflared agent container."""
    tunnel_state["last_action_status"] = None # Clear previous action status
    if not docker_client:
        msg = "Docker client not available. Cannot start container."
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False
    if not tunnel_state.get("token"):
        msg = "Tunnel token not available. Cannot start container."
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
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
                return True
        else:
            logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' not found. Creating and starting...")
            # Run the container
            # Common options: --network host or a shared bridge network
            # Using host network for simplicity here to allow tunnel to reach host ports.
            # Consider using a shared network for better isolation.
            new_container = docker_client.containers.run(
                image=CLOUDFLARED_IMAGE,
                command=f"tunnel --no-autoupdate run --token {token}",
                name=CLOUDFLARED_CONTAINER_NAME,
                network_mode="host", # Or specific network: network="your-network-name"
                restart_policy={"Name": "unless-stopped"}, # Optional: manage restarts
                detach=True, # Run in background
                remove=False # Don't auto-remove when stopped from here
            )
            tunnel_state["last_action_status"] = f"Successfully created and started container '{new_container.name}'."
            logging.info(tunnel_state["last_action_status"])
            # Give it a moment to potentially update status
            time.sleep(2)
            return True
    except APIError as e:
        msg = f"Docker API error starting container: {e}"
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False
    except Exception as e:
        msg = f"Unexpected error starting container: {e}"
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False


def stop_cloudflared_container():
    """Stops the cloudflared agent container."""
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
        return False # Or True, as it's already 'stopped' in a sense

    if container.status != 'running':
        msg = f"Container '{CLOUDFLARED_CONTAINER_NAME}' is not running (status: {container.status})."
        logging.info(msg)
        tunnel_state["last_action_status"] = msg
        return True

    try:
        logging.info(f"Stopping container '{CLOUDFLARED_CONTAINER_NAME}'...")
        # Add timeout to stop command
        container.stop(timeout=30)
        # Optional: Remove container after stopping?
        # container.remove()
        # logging.info(f"Container '{CLOUDFLARED_CONTAINER_NAME}' removed.")
        tunnel_state["last_action_status"] = f"Successfully stopped container '{CLOUDFLARED_CONTAINER_NAME}'."
        logging.info(tunnel_state["last_action_status"])
         # Give it a moment to potentially update status
        time.sleep(2)
        return True
    except APIError as e:
        msg = f"Docker API error stopping container: {e}"
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False
    except Exception as e:
        msg = f"Unexpected error stopping container: {e}"
        logging.error(msg)
        tunnel_state["last_action_status"] = f"Error: {msg}"
        return False

# --- Flask Web Server ---
app = Flask(__name__)

@app.route('/')
def status_page():
    """Displays the current tunnel status and controls."""
    # Update container status before rendering
    update_cloudflared_container_status()

    # Mask token for display purposes
    display_token = "Error retrieving token"
    if tunnel_state["token"]:
        if len(tunnel_state["token"]) > 10:
            display_token = f"{tunnel_state['token'][:5]}...{tunnel_state['token'][-5:]}"
        else:
            display_token = "Token retrieved (short)"
    elif tunnel_state["error"] and "token" in tunnel_state["error"].lower():
         display_token = "Failed to retrieve token"
    elif tunnel_state["id"]:
        display_token = "Token not yet retrieved or failed"
    else:
        display_token = "Tunnel not created or ID not found"

    # Simple HTML template as a string
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cloudflare Tunnel Status</title>
        <style>
            body { font-family: sans-serif; padding: 20px; background-color: #f4f4f4; color: #333; }
            h1, h2 { color: #555; }
            .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .status-box { padding: 10px; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; }
            .error { background-color: #ffebeb; border-color: #ffc2c2; color: #a00; }
            .success { background-color: #e6ffed; border-color: #c3e6cb; color: #155724;}
            .info { background-color: #e7f3fe; border-color: #b8daff; color: #004085;}
            pre { background-color: #eee; padding: 10px; border-radius: 3px; word-wrap: break-word; }
            .button { padding: 10px 15px; border: none; border-radius: 4px; color: white; cursor: pointer; font-size: 1em; margin-right: 10px; }
            .start-button { background-color: #28a745; } /* Green */
            .stop-button { background-color: #dc3545; } /* Red */
            .button:disabled { background-color: #cccccc; cursor: not-allowed; }
            form { display: inline-block; }
        </style>
    </head>
    <body>
        <h1>Cloudflare Tunnel Manager</h1>

        <div class="container">
            <h2>Initialization Status</h2>
            <div class="status-box {{ 'error' if error else ('success' if token else 'info') }}">
                <p><strong>Message:</strong> {{ status_message }}</p>
                {% if error %}
                <p><strong>Error Details:</strong> <span style="color: red;">{{ error }}</span></p>
                {% endif %}
            </div>
            <h3>Tunnel Details</h3>
            <p><strong>Desired Tunnel Name:</strong> {{ name }}</p>
            <p><strong>Tunnel ID:</strong> {{ id if id else 'Not available' }}</p>
            <p><strong>Tunnel Token:</strong> <pre>{{ display_token }}</pre></p>
             <p><small>Note: Full token must be available internally to start the tunnel agent.</small></p>
        </div>

        <div class="container">
             <h2>Tunnel Agent Control (<pre>{{ cloudflared_container_name }}</pre>)</h2>
             <p><strong>Agent Container Status:</strong> <strong style="text-transform: capitalize;">{{ cloudflared_container_status }}</strong></p>

             {% if last_action_status %}
             <div class="status-box {{ 'error' if 'Error' in last_action_status else 'info' }}">
                <strong>Last Action:</strong> {{ last_action_status }}
             </div>
             {% endif %}

             <form action="{{ url_for('start_tunnel') }}" method="post" style="margin-right: 10px;">
                <button type="submit" class="button start-button"
                        {{ 'disabled' if not token or cloudflared_container_status == 'running' }}>
                    Start Tunnel Agent
                </button>
             </form>
             <form action="{{ url_for('stop_tunnel') }}" method="post">
                <button type="submit" class="button stop-button"
                        {{ 'disabled' if cloudflared_container_status != 'running' }}>
                    Stop Tunnel Agent
                </button>
             </form>
        </div>

    </body>
    </html>
    """
    return render_template_string(
        html_template,
        # Tunnel details
        name=tunnel_state["name"],
        id=tunnel_state["id"],
        status_message=tunnel_state["status_message"],
        error=tunnel_state["error"],
        display_token=display_token,
        token=tunnel_state.get("token"), # Pass raw token for button logic
        # Agent details
        cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
        cloudflared_container_status=tunnel_state["cloudflared_container_status"],
        last_action_status=tunnel_state.get("last_action_status")
    )

# --- Action Routes ---

@app.route('/start', methods=['POST'])
def start_tunnel():
    """Endpoint to trigger starting the tunnel."""
    logging.info("Received request to start tunnel agent.")
    start_cloudflared_container()
    # Redirect back to the status page to show the result
    return redirect(url_for('status_page'))

@app.route('/stop', methods=['POST'])
def stop_tunnel():
    """Endpoint to trigger stopping the tunnel."""
    logging.info("Received request to stop tunnel agent.")
    stop_cloudflared_container()
    # Redirect back to the status page
    return redirect(url_for('status_page'))


# --- Main Execution ---
if __name__ == '__main__':
    initialize_tunnel()
    # Ensure initial container status is known
    update_cloudflared_container_status()
    app.run(host='0.0.0.0', port=5000)