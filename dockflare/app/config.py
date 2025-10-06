# app/config.py
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
#
# dockflare/app/config.py
import os
import logging 

def _get_int_env(name, default, minimum=None):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
        if minimum is not None and parsed < minimum:
            logging.warning(f"Environment variable {name} must be >= {minimum}. Using default {default}.")
            return default
        return parsed
    except ValueError:
        logging.warning(f"Environment variable {name} must be an integer. Using default {default}.")
        return default

# --- DockFlare Version ---
APP_VERSION = "v3.0.3"
# --- web: https://dockflare.app ---
# --- github: https://github.com/ChrispyBacon-dev/DockFlare ---

# --- Logging Configuration ---
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
# Set via environment variable LOG_LEVEL (default: INFO)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

MAX_CF_UPDATE_RETRIES = 3
CF_UPDATE_RETRY_DELAY = 2
CF_UPDATE_BACKOFF_FACTOR = 2

# --- Dynamic Configuration ---
# These variables are now loaded dynamically from the encrypted configuration file
# at startup. They are initialized here with default values.
CF_API_TOKEN = None
CF_ACCOUNT_ID = None
CF_ZONE_ID = None
TUNNEL_NAME = "dockflare-tunnel"
GRACE_PERIOD_SECONDS = 600
TUNNEL_DNS_SCAN_ZONE_NAMES = []
MASTER_API_KEY = os.getenv('DOCKFLARE_API_KEY')

# --- Static & Environment-Based Configuration ---
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"

CF_HEADERS = {
    "Content-Type": "application/json",
}

USE_EXTERNAL_CLOUDFLARED = os.getenv('USE_EXTERNAL_CLOUDFLARED', 'false').lower() in ['true', '1', 't', 'yes']
EXTERNAL_TUNNEL_ID = os.getenv('EXTERNAL_TUNNEL_ID')

if not USE_EXTERNAL_CLOUDFLARED:
    CLOUDFLARED_NETWORK_NAME = os.getenv('CLOUDFLARED_NETWORK_NAME', 'cloudflare-net')
    
    CLOUDFLARED_CONTAINER_NAME = os.getenv('CLOUDFLARED_CONTAINER_NAME', f"cloudflared-agent-{TUNNEL_NAME}")
else:
    CLOUDFLARED_NETWORK_NAME = None
    CLOUDFLARED_CONTAINER_NAME = None

CLOUDFLARED_IMAGE = "cloudflare/cloudflared:latest"

PRIMARY_LABEL_PREFIX = 'dockflare.'
LEGACY_LABEL_PREFIX = 'cloudflare.tunnel.'
CUSTOM_LABEL_PREFIX = os.getenv('LABEL_PREFIX')

LABEL_PREFIX = CUSTOM_LABEL_PREFIX or PRIMARY_LABEL_PREFIX

CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 60))
AGENT_STATUS_UPDATE_INTERVAL_SECONDS = int(os.getenv('AGENT_STATUS_UPDATE_INTERVAL_SECONDS', 30))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')
MAX_LOG_QUEUE_SIZE = 200
MAX_CONCURRENT_DNS_OPS = int(os.getenv('MAX_CONCURRENT_DNS_OPS', 5))
RECONCILIATION_BATCH_SIZE = int(os.getenv('RECONCILIATION_BATCH_SIZE', 5))
ACCOUNT_EMAIL_CACHE_TTL = 3600
SCAN_ALL_NETWORKS = os.getenv('SCAN_ALL_NETWORKS', 'false').lower() in ['true', '1', 't', 'yes']

# Waitress / web server tuning
WAITRESS_HOST = os.getenv('WAITRESS_HOST', '0.0.0.0')
WAITRESS_PORT = _get_int_env('WAITRESS_PORT', 5000, minimum=1)
WAITRESS_THREADS = _get_int_env('WAITRESS_THREADS', 128, minimum=1)
WAITRESS_CONNECTION_LIMIT = _get_int_env('WAITRESS_CONNECTION_LIMIT', 256, minimum=1)
WAITRESS_BACKLOG = _get_int_env('WAITRESS_BACKLOG', 2048, minimum=1)
WAITRESS_CHANNEL_TIMEOUT = _get_int_env('WAITRESS_CHANNEL_TIMEOUT', 360, minimum=1)

# If set, enables the Prometheus metrics endpoint on the specified port.
# The IP is hardcoded to 0.0.0.0 to be accessible within Docker networks.
CLOUDFLARED_METRICS_PORT = os.getenv('CLOUDFLARED_METRICS_PORT')
if CLOUDFLARED_METRICS_PORT:
    try:
        port = int(CLOUDFLARED_METRICS_PORT)
        if not (1 <= port <= 65535):
            logging.warning(f"Metrics port {port} is outside the valid range (1-65535). Disabling.")
            CLOUDFLARED_METRICS_PORT = None
    except ValueError:
        logging.warning(f"Invalid value for CLOUDFLARED_METRICS_PORT: '{CLOUDFLARED_METRICS_PORT}'. Must be a number. Disabling.")
        CLOUDFLARED_METRICS_PORT = None

# --- Auto-restore (self-heal) settings ---
# If true, the Master will attempt to recreate rules reported by Agents when the rule has been removed on Master.
AUTO_RESTORE_AGENT_RULES = os.getenv('AUTO_RESTORE_AGENT_RULES', 'true').lower() in ['true', '1', 't', 'yes']
# Cooldown (seconds) between automatic restore operations per-agent to avoid flapping/loops.
AUTO_RESTORE_COOLDOWN_SECONDS = int(os.getenv('AUTO_RESTORE_COOLDOWN_SECONDS', '60'))

# --- Multi-server / Agent support settings ---
# URL prefix for agent API endpoints (kept here for consistency; routing will use this in the Master)
AGENT_API_PREFIX = os.getenv('AGENT_API_PREFIX', '/api/v2/agents')

# Seconds without heartbeat before an agent is considered offline
AGENT_HEARTBEAT_TIMEOUT = int(os.getenv('AGENT_HEARTBEAT_TIMEOUT', 60))

# Whether agents must be manually enrolled via the UI (recommended: true)
AGENT_ENROLLMENT_REQUIRED = os.getenv('AGENT_ENROLLMENT_REQUIRED', 'true').lower() in ['true', '1', 't', 'yes']

# Optional path for storing agent API key metadata (defaults to encrypted config storage if None)
AGENT_KEY_STORAGE_PATH = os.getenv('AGENT_KEY_STORAGE_PATH', None)

# Polling interval (seconds) recommended for agents to poll the Master for commands
AGENT_COMMAND_POLL_INTERVAL = int(os.getenv('AGENT_COMMAND_POLL_INTERVAL', 10))

REDIS_DB_INDEX = int(os.getenv('REDIS_DB_INDEX', 0))

USE_REUSABLE_POLICIES = os.getenv('USE_REUSABLE_POLICIES', 'true').lower() in ['true', '1', 't', 'yes']

SYNC_ALL_CLOUDFLARE_POLICIES = os.getenv('SYNC_ALL_CLOUDFLARE_POLICIES', 'false').lower() in ['true', '1', 't', 'yes']
