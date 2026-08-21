import os
import re
import time
import json
import docker
import requests
import logging
import tempfile
import http.server
import socketserver
from threading import Thread
from datetime import datetime, timezone
from dotenv import load_dotenv
import cloudflare_api

DEFAULT_CLOUDFLARED_IMAGE = "cloudflare/cloudflared:2025.9.0"
_SHA256_HEX_RE = re.compile(r"^[A-Fa-f0-9]{64}$")


def is_dockflare_enabled(labels):
    """Check if container has DockFlare enabled using new or legacy labels."""
    if not labels:
        return False
    return (labels.get("dockflare.enable") == "true" or
            labels.get("cloudflare.tunnel.enable") == "true")


def _normalize_cloudflared_image(raw_value, default_image):
    """Sanitize the configured cloudflared image reference."""
    if not raw_value:
        return default_image

    candidate = raw_value.strip()
    if not candidate:
        logging.warning("CLOUDFLARED_IMAGE is blank after trimming; falling back to default %s", default_image)
        return default_image

    # Split on whitespace to drop inline comments or accidental extra tokens.
    candidate = candidate.split()[0]

    if "#" in candidate:
        candidate = candidate.split("#", 1)[0].strip()
        if not candidate:
            logging.warning("CLOUDFLARED_IMAGE only contained a comment; falling back to default %s", default_image)
            return default_image

    if "@sha256:" in candidate:
        repository, digest = candidate.split("@sha256:", 1)
        if not repository:
            logging.error("CLOUDFLARED_IMAGE is missing the repository before @sha256; falling back to default %s", default_image)
            return default_image
        if not _SHA256_HEX_RE.fullmatch(digest):
            logging.error("CLOUDFLARED_IMAGE digest is not a valid 64 char hex string; falling back to default %s", default_image)
            return default_image
        return f"{repository}@sha256:{digest.lower()}"

    return candidate

# Basic Logging Configuration (configurable via LOG_LEVEL env var; default INFO)
_LOG_LEVEL_STR = os.getenv('LOG_LEVEL', 'INFO').upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_STR, logging.INFO)
logging.basicConfig(level=_LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().info(f"Logging initialized at level: {_LOG_LEVEL_STR}")

# Load environment variables from .env file
load_dotenv()

MASTER_URL = os.getenv("DOCKFLARE_MASTER_URL")
API_KEY = os.getenv("DOCKFLARE_API_KEY")
CF_ACCESS_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID", "")
CF_ACCESS_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET", "")


def get_headers(content_type=True):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    if content_type:
        headers["Content-Type"] = "application/json"
    if CF_ACCESS_CLIENT_ID:
        headers["CF-Access-Client-Id"] = CF_ACCESS_CLIENT_ID
        headers["CF-Access-Client-Secret"] = CF_ACCESS_CLIENT_SECRET
    return headers
CLOUDFLARED_NETWORK_NAME = os.getenv("CLOUDFLARED_NETWORK_NAME", "cloudflare-net")
CLOUDFLARED_IMAGE = _normalize_cloudflared_image(os.getenv("CLOUDFLARED_IMAGE"), DEFAULT_CLOUDFLARED_IMAGE)
if CLOUDFLARED_IMAGE != DEFAULT_CLOUDFLARED_IMAGE:
    logging.info(f"Using configured cloudflared image: {CLOUDFLARED_IMAGE}")
else:
    logging.info(f"Using default cloudflared image: {DEFAULT_CLOUDFLARED_IMAGE}")
AGENT_ID_FILE = "/app/data/agent_id.txt"
TUNNEL_STATE_FILE = "/app/data/tunnel_state.json"
AGENT_ID = None  # Will be assigned by the master

# --- Tunnel Management Globals ---
tunnel_container = None
current_tunnel_token = None
current_tunnel_id = None
current_tunnel_version = None
current_tunnel_name = None
desired_tunnel_state = "unknown"

# --- Health / Monitoring Globals ---
thread_health_status = {}
last_successful_master_contact = None


def fetch_cloudflared_version(container):
    try:
        exec_result = container.exec_run("cloudflared --version")
        output = getattr(exec_result, 'output', b'') or b''
        version_text = output.decode('utf-8', errors='ignore').strip()
        if version_text:
            first_line = version_text.splitlines()[0]
            logging.info(f"Detected cloudflared version: {first_line}")
            return first_line
    except Exception as e:
        logging.error(f"Failed to fetch cloudflared version: {e}")
    return None


def load_tunnel_state():
    global current_tunnel_token, current_tunnel_id, current_tunnel_name, desired_tunnel_state
    if not os.path.exists(TUNNEL_STATE_FILE):
        return
    try:
        with open(TUNNEL_STATE_FILE, 'r') as f:
            data = json.load(f)
        current_tunnel_token = data.get("token")
        current_tunnel_id = data.get("id")
        current_tunnel_name = data.get("name")
        desired_tunnel_state = data.get("desired_state", "unknown")
        logging.info("Loaded tunnel state from disk.")
    except Exception as e:
        logging.error(f"Failed to load tunnel state file: {e}")


def save_tunnel_state():
    data = {
        "token": current_tunnel_token,
        "id": current_tunnel_id,
        "name": current_tunnel_name,
        "desired_state": desired_tunnel_state
    }
    try:
        _write_secure_file(TUNNEL_STATE_FILE, lambda fh: json.dump(data, fh))
    except Exception as e:
        logging.error(f"Failed to persist tunnel state: {e}")


def _write_secure_file(path, writer):
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=directory, delete=False) as tmp_file:
            writer(tmp_file)
            tmp_file.flush()
            try:
                os.fsync(tmp_file.fileno())
            except (AttributeError, OSError):
                pass
            temp_path = tmp_file.name
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        os.replace(temp_path, path)
    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def ensure_cloudflared_running(client):
    global tunnel_container, current_tunnel_version
    if desired_tunnel_state != "running" or not current_tunnel_token or not current_tunnel_name:
        return
    try:
        existing = client.containers.get('dockflare-agent-tunnel')
        existing.reload()
        if existing.status == 'running':
            tunnel_container = existing
            if not current_tunnel_version:
                current_tunnel_version = fetch_cloudflared_version(existing)
            return
        logging.warning(f"Detected cloudflared container in status '{existing.status}'. Redeploying.")
    except docker.errors.NotFound:
        logging.warning("cloudflared container missing. Redeploying.")
    except Exception as e:
        logging.error(f"Error inspecting cloudflared container: {e}")

    _run_cloudflared_container(client, current_tunnel_name, current_tunnel_token)


def _remove_existing_container(client):
    global tunnel_container, current_tunnel_version
    try:
        existing_container = client.containers.get('dockflare-agent-tunnel')
        logging.info(f"Stopping existing cloudflared container '{existing_container.name}' ({existing_container.short_id}).")
        existing_container.stop()
        existing_container.remove()
        if tunnel_container and tunnel_container.id == existing_container.id:
            tunnel_container = None
    except docker.errors.NotFound:
        logging.info("No existing cloudflared container to remove.")
    except Exception as e:
        logging.error(f"Failed to remove existing cloudflared container: {e}")
    finally:
        current_tunnel_version = None


def _run_cloudflared_container(client, tunnel_name, tunnel_token):
    global tunnel_container, current_tunnel_version
    if not tunnel_token:
        logging.error("Cannot start cloudflared: missing tunnel token.")
        return False
    try:
        tunnel_container = client.containers.run(
            CLOUDFLARED_IMAGE,
            command=["tunnel", "--no-autoupdate", "run"],
            detach=True,
            name="dockflare-agent-tunnel",
            network=CLOUDFLARED_NETWORK_NAME,
            restart_policy={"Name": "unless-stopped"},
            environment={"TUNNEL_TOKEN": tunnel_token}
        )
        time.sleep(2)
        current_tunnel_version = fetch_cloudflared_version(tunnel_container)
        logging.info(f"cloudflared container started: {tunnel_container.short_id}")
        report_event_to_master("tunnel_status", {
            "name": tunnel_name,
            "status": "running",
            "version": current_tunnel_version
        })
        return True
    except Exception as e:
        logging.error(f"Failed to start cloudflared container: {e}")
        return False

def load_agent_id():
    """Loads agent ID from the filesystem."""
    global AGENT_ID
    if os.path.exists(AGENT_ID_FILE):
        try:
            with open(AGENT_ID_FILE, 'r') as f:
                agent_id = f.read().strip()
                if agent_id:
                    AGENT_ID = agent_id
                    logging.info(f"Loaded existing Agent ID: {AGENT_ID}")
        except IOError as e:
            logging.error(f"Could not read agent ID file: {e}")

def save_agent_id(agent_id):
    """Saves agent ID to the filesystem."""
    try:
        _write_secure_file(AGENT_ID_FILE, lambda fh: fh.write(agent_id))
        logging.info(f"Saved Agent ID to {AGENT_ID_FILE}")
    except IOError as e:
        logging.error(f"Could not save agent ID file: {e}")

def register_with_master():
    """
    Registers the agent with the DockFlare Master instance and retrieves an agent ID.
    """
    global AGENT_ID
    if not MASTER_URL or not API_KEY:
        logging.error("Error: DOCKFLARE_MASTER_URL and DOCKFLARE_API_KEY must be set.")
        return False

    endpoint = f"{MASTER_URL}/api/v2/agents/register"
    while True:
        logging.info(f"Attempting to register with master at {endpoint}")
        try:
            headers = get_headers()
            custom_display_name = os.getenv("AGENT_DISPLAY_NAME", "").strip()
            default_display_name = f"agent-{AGENT_ID[:8]}" if AGENT_ID else "dockflare-agent"
            payload = {
                "display_name": custom_display_name or default_display_name,
                "version": "1.0.0",
            }
            if AGENT_ID:
                payload["agent_id"] = AGENT_ID

            response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            new_agent_id = data.get("agent_id")

            if not new_agent_id:
                logging.error("Master did not provide an agent_id. Retrying in 60s...")
                time.sleep(60)
                continue

            if AGENT_ID and AGENT_ID != new_agent_id:
                logging.warning(f"Master assigned a new Agent ID ({new_agent_id}). Overwriting old one ({AGENT_ID}).")

            AGENT_ID = new_agent_id
            save_agent_id(AGENT_ID)
            logging.info(f"Successfully registered with master. Agent ID: {AGENT_ID}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Error registering with master: {e}. Retrying in 60s...")
            time.sleep(60)

def report_event_to_master(event_type, container_data=None):
    """
    Sends a JSON payload to the master's reporting endpoint.
    """
    if not AGENT_ID:
        logging.debug("report_event_to_master called but AGENT_ID is missing; skipping.")
        return
    try:
        from datetime import datetime, timezone
        payload = {
            "type": event_type,
            "timestamp": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
        }
        if container_data:
            payload["container"] = container_data

        headers = get_headers()
        endpoint = f"{MASTER_URL}/api/v2/agents/{AGENT_ID}/events"

        # Log endpoint and payload at debug level so container logs show activity without being too noisy at info.
        logging.debug(f"Reporting to master endpoint={endpoint} payload_type={event_type} payload_keys={list(payload.keys())}")

        response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        try:
            response.raise_for_status()
            logging.info(f"Successfully reported event to master: {event_type} (status={response.status_code})")
        except requests.exceptions.HTTPError as httpe:
            logging.error(f"HTTP error reporting event to master: {httpe} status={getattr(response, 'status_code', 'unknown')} body={getattr(response, 'text', '')}")
            raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Error reporting event to master: {e}")

def listen_for_docker_events(client, label_prefix):
    thread_health_status[f"events_listener_{label_prefix.strip('.')}"] = "running"
    logging.info(f"Performing initial scan of running containers for prefix {label_prefix}...")
    try:
        for container in client.containers.list():
            if container.labels.get(f"{label_prefix}enable") == "true":
                logging.info(f"Found existing container to report for {label_prefix}: {container.name}")
                report_event_to_master("container_start", {
                    "id": container.id,
                    "name": container.name,
                    "labels": container.labels
                })
    except Exception as e:
        logging.error(f"Error during initial container scan for {label_prefix}: {e}")

    logging.info(f"Listening for Docker events with prefix {label_prefix}...")
    event_filters = {
        "type": "container",
        "label": f"{label_prefix}enable=true"
    }
    try:
        for event in client.events(decode=True, filters=event_filters):
            try:
                if event.get("Type") == "container" and event.get("Action") in ["start", "stop", "die"]:
                    action = event['Action']
                    container_id = event['id']
                    try:
                        container = client.containers.get(container_id)
                        event_type = f"container_{action}"
                        logging.info(f"Detected event '{action}' for container {container.name} ({label_prefix})")
                        report_event_to_master(event_type, {
                            "id": container_id,
                            "name": container.name,
                            "labels": container.labels
                        })
                    except docker.errors.NotFound:
                        logging.warning(f"Container {container_id[:12]} not found after event '{action}' ({label_prefix}). Reporting to master.")
                        report_event_to_master({"action": action, "container_id": container_id})
            except Exception as e:
                logging.error(f"An error occurred in the event loop for {label_prefix}: {e}")
    except Exception as e:
        logging.error(f"Failed to connect to Docker event stream for {label_prefix}: {e}")
        thread_health_status[f"events_listener_{label_prefix.strip('.')}"] = "failed"

def start_event_listeners(client):
    threads = []
    label_prefixes = ["dockflare.", "cloudflare.tunnel."]
    for prefix in label_prefixes:
        thread = Thread(target=listen_for_docker_events, args=(client, prefix), daemon=True)
        threads.append(thread)
    return threads

def manage_tunnels(client):
    """
    Periodically polls for commands from the master and manages a cloudflared container.
    """
    global tunnel_container, current_tunnel_token, current_tunnel_id, current_tunnel_version, current_tunnel_name, desired_tunnel_state
    logging.info("Tunnel management thread started.")

    while True:
        if not AGENT_ID:
            time.sleep(10)
            continue
        try:
            headers = get_headers(content_type=False)
            endpoint = f"{MASTER_URL}/api/v2/agents/{AGENT_ID}/commands"
            response = requests.get(endpoint, headers=headers, timeout=15)
            response.raise_for_status()
            commands = response.json().get("commands", [])

            for cmd in commands:
                action = cmd.get("action")
                if action == "start_tunnel":
                    tunnel_token = cmd.get("token")
                    tunnel_name = cmd.get("tunnel_name")
                    tunnel_id = cmd.get("tunnel_id")
                    token_changed = tunnel_token and tunnel_token != current_tunnel_token
                    id_changed = tunnel_id and tunnel_id != current_tunnel_id
                    if token_changed or id_changed:
                        reason_parts = []
                        if token_changed:
                            reason_parts.append("token change")
                        if id_changed:
                            reason_parts.append("tunnel id change")
                        reason_text = ", ".join(reason_parts) if reason_parts else "assignment update"
                        logging.info(f"Received command to start tunnel '{tunnel_name}' ({reason_text}).")

                        _remove_existing_container(client)
                        logging.info("Starting new cloudflared tunnel container...")
                        _run_cloudflared_container(client, tunnel_name, tunnel_token)
                        current_tunnel_token = tunnel_token
                        current_tunnel_id = tunnel_id
                        current_tunnel_name = tunnel_name
                        desired_tunnel_state = "running"
                        save_tunnel_state()
                    else:
                        logging.info("Received start_tunnel command but tunnel token/id unchanged; ensuring cloudflared is running.")
                        current_tunnel_name = tunnel_name or current_tunnel_name
                        desired_tunnel_state = "running"
                        save_tunnel_state()
                        ensure_cloudflared_running(client)

                elif action == "restart_tunnel":
                    tunnel_token = cmd.get("tunnel_token")
                    tunnel_name = cmd.get("tunnel_name")
                    tunnel_id = cmd.get("tunnel_id")
                    if tunnel_token and tunnel_name and tunnel_id:
                        logging.info(f"Received command to restart tunnel '{tunnel_name}'.")
                        _remove_existing_container(client)
                        logging.info("Restarting cloudflared tunnel container...")
                        _run_cloudflared_container(client, tunnel_name, tunnel_token)
                        current_tunnel_token = tunnel_token
                        current_tunnel_id = tunnel_id
                        current_tunnel_name = tunnel_name
                        desired_tunnel_state = "running"
                        save_tunnel_state()
                    else:
                        logging.warning("Received restart_tunnel command with missing parameters.")

                elif action == "stop_tunnel":
                    logging.info("Received command to stop cloudflared tunnel container.")
                    desired_tunnel_state = "stopped"
                    save_tunnel_state()
                    _remove_existing_container(client)
                    report_event_to_master("tunnel_status", {
                        "name": current_tunnel_name,
                        "status": "stopped"
                    })
                    current_tunnel_token = None
                    current_tunnel_id = None
                    current_tunnel_name = None
                    save_tunnel_state()

                elif action == "update_tunnel_config":
                    if not current_tunnel_id:
                        logging.error("Cannot update tunnel config: no tunnel ID available.")
                        continue
                    rules = cmd.get("rules", {})
                    ingress_rules = cloudflare_api.generate_ingress_rules(rules)
                    success = cloudflare_api.update_tunnel_config(MASTER_URL, API_KEY, current_tunnel_id, ingress_rules)
                    if success:
                        logging.info("Tunnel configuration updated successfully")
                    else:
                        logging.error("Failed to update tunnel configuration")

        except requests.exceptions.RequestException as e:
            logging.error(f"Could not poll commands from master: {e}")
        except docker.errors.ImageNotFound:
            logging.error("Could not start tunnel: cloudflare/cloudflared image not found. Please pull it.")
        except Exception as e:
            logging.error(f"An error in tunnel management: {e}")
        time.sleep(30)  # Poll every 30 seconds


def tunnel_health_monitor(client):
    logging.info("Tunnel health monitor thread started.")
    while True:
        try:
            ensure_cloudflared_running(client)
        except Exception as e:
            logging.error(f"Tunnel health monitor encountered an error: {e}")
        time.sleep(30)

REPORT_INTERVAL_SECONDS = int(os.getenv("REPORT_INTERVAL_SECONDS", "30"))

def periodic_status_reporter(client):
    """
    Periodic reporter: sends heartbeat and full status_report of enabled containers.
    """
    logging.info("Status reporter thread started.")
    while True:
        if not AGENT_ID:
            time.sleep(5)
            continue
        try:

            logging.info("Sending heartbeat to master.")
            report_event_to_master("heartbeat")

            containers = []
            for container in client.containers.list():
                labels = getattr(container, 'labels', {}) or {}
                if is_dockflare_enabled(labels):
                    containers.append({
                        "id": container.id,
                        "name": container.name,
                        "labels": labels,
                        "status": getattr(container, 'status', None)
                    })

            logging.info(f"Sending status_report to master (containers={len(containers)})")
            report_event_to_master("status_report", {"containers": containers})
        except Exception as e:
            logging.error(f"Periodic reporter error: {e}")
        time.sleep(REPORT_INTERVAL_SECONDS)

def cleanup():
    """
    Gracefully shuts down the agent and its resources.
    """
    global tunnel_container, current_tunnel_version
    logging.info("Shutting down agent.")
    if tunnel_container:
        logging.info("Stopping tunnel container...")
        try:
            tunnel_container.stop()
            tunnel_container.remove()
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logging.error(f"Could not stop tunnel container: {e}")
        finally:
            tunnel_container = None
    current_tunnel_version = None
# --- Health Check HTTP Server ---
class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global last_successful_master_contact, thread_health_status

        if self.path == '/health':
            seconds_since_contact = None
            if last_successful_master_contact:
                seconds_since_contact = int((datetime.now(timezone.utc) - last_successful_master_contact).total_seconds())

            status = "unhealthy"
            if AGENT_ID:
                if seconds_since_contact is not None and seconds_since_contact < 120:
                    status = "healthy"
                elif seconds_since_contact is not None and seconds_since_contact < 300:
                    status = "degraded"

            tunnel_container_running = False
            if tunnel_container:
                try:
                    tunnel_container.reload()
                    tunnel_container_running = tunnel_container.status == 'running'
                except:
                    pass

            response_data = {
                "status": status,
                "agent_id": AGENT_ID,
                "registered": AGENT_ID is not None,
                "tunnel": {
                    "state": desired_tunnel_state,
                    "name": current_tunnel_name,
                    "id": current_tunnel_id,
                    "container_running": tunnel_container_running,
                    "version": current_tunnel_version
                },
                "master_connection": {
                    "url": MASTER_URL,
                    "last_successful_report": last_successful_master_contact.isoformat() if last_successful_master_contact else None,
                    "seconds_since_contact": seconds_since_contact
                },
                "threads": thread_health_status.copy()
            }

            http_status = 200 if status == "healthy" else 503
            self.send_response(http_status)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404 Not Found')

def run_health_check_server():
    thread_health_status["health_server"] = "running"
    try:
        with socketserver.TCPServer(('', HEALTH_CHECK_PORT), HealthCheckHandler) as httpd:
            logging.info(f"Health check server running on port {HEALTH_CHECK_PORT}")
            httpd.serve_forever()
    except Exception as e:
        logging.error(f"Health check server error: {e}")
        thread_health_status["health_server"] = "failed"

if __name__ == "__main__":
    load_agent_id()
    load_tunnel_state()
    if register_with_master():
        docker_client = docker.from_env()
        try:
            ensure_cloudflared_running(docker_client)
            tunnel_thread = Thread(target=manage_tunnels, args=(docker_client,), daemon=True)
            tunnel_thread.start()
            status_thread = Thread(target=periodic_status_reporter, args=(docker_client,), daemon=True)
            status_thread.start()
            event_threads = start_event_listeners(docker_client)
            for t in event_threads:
                t.start()
            monitor_thread = Thread(target=tunnel_health_monitor, args=(docker_client,), daemon=True)
            monitor_thread.start()
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            cleanup()
        except Exception as e:
            logging.critical(f"A critical error occurred: {e}")
            cleanup()
    else:
        logging.critical("Agent startup failed. Could not register with master.")
