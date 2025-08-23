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
# app/config.py
import os
import sys
import logging 

# --- DockFlare Version ---
APP_VERSION = "v2.1.4"
# --- web: https://dockflare.app ---
# --- github: https://github.com/ChrispyBacon-dev/DockFlare ---

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
AGENT_STATUS_UPDATE_INTERVAL_SECONDS = int(os.getenv('AGENT_STATUS_UPDATE_INTERVAL_SECONDS', 10))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')
MAX_LOG_QUEUE_SIZE = 200
MAX_CONCURRENT_DNS_OPS = int(os.getenv('MAX_CONCURRENT_DNS_OPS', 3))
RECONCILIATION_BATCH_SIZE = int(os.getenv('RECONCILIATION_BATCH_SIZE', 3))
ACCOUNT_EMAIL_CACHE_TTL = 3600
SCAN_ALL_NETWORKS = os.getenv('SCAN_ALL_NETWORKS', 'false').lower() in ['true', '1', 't', 'yes']

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
