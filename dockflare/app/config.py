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

from dotenv import load_dotenv

load_dotenv()

MAX_CF_UPDATE_RETRIES = 3
CF_UPDATE_RETRY_DELAY = 2
CF_UPDATE_BACKOFF_FACTOR = 2

CF_API_TOKEN = os.getenv('CF_API_TOKEN')
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_ZONE_ID = os.getenv('CF_ZONE_ID')
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4"

if CF_API_TOKEN:
    CF_HEADERS = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
else:
    CF_HEADERS = {
        "Content-Type": "application/json",
    }

USE_EXTERNAL_CLOUDFLARED = os.getenv('USE_EXTERNAL_CLOUDFLARED', 'false').lower() in ['true', '1', 't', 'yes']
EXTERNAL_TUNNEL_ID = os.getenv('EXTERNAL_TUNNEL_ID')
TUNNEL_NAME = os.getenv("TUNNEL_NAME", "dockflared-tunnel")

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

# DEPRECATED: This will be removed in a future version.
LABEL_PREFIX = CUSTOM_LABEL_PREFIX or PRIMARY_LABEL_PREFIX

GRACE_PERIOD_SECONDS = int(os.getenv('GRACE_PERIOD_SECONDS', 28800))
CLEANUP_INTERVAL_SECONDS = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 60))
AGENT_STATUS_UPDATE_INTERVAL_SECONDS = int(os.getenv('AGENT_STATUS_UPDATE_INTERVAL_SECONDS', 10))
STATE_FILE_PATH = os.getenv('STATE_FILE_PATH', '/app/data/state.json')
MAX_LOG_QUEUE_SIZE = 200
MAX_CONCURRENT_DNS_OPS = int(os.getenv('MAX_CONCURRENT_DNS_OPS', 3))
RECONCILIATION_BATCH_SIZE = int(os.getenv('RECONCILIATION_BATCH_SIZE', 3))
ACCOUNT_EMAIL_CACHE_TTL = 3600
SCAN_ALL_NETWORKS = os.getenv('SCAN_ALL_NETWORKS', 'false').lower() in ['true', '1', 't', 'yes']
TUNNEL_DNS_SCAN_ZONE_NAMES_STR = os.getenv('TUNNEL_DNS_SCAN_ZONE_NAMES', '')
TUNNEL_DNS_SCAN_ZONE_NAMES = [name.strip() for name in TUNNEL_DNS_SCAN_ZONE_NAMES_STR.split(',') if name.strip()]

REQUIRED_VARS_BASE = ["CF_API_TOKEN", "CF_ACCOUNT_ID"]
missing_vars = []

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

if not USE_EXTERNAL_CLOUDFLARED:
    if not TUNNEL_NAME:
        REQUIRED_VARS_BASE.append("TUNNEL_NAME")
else:
    if not EXTERNAL_TUNNEL_ID:
        REQUIRED_VARS_BASE.append("EXTERNAL_TUNNEL_ID")

for var_name in REQUIRED_VARS_BASE:
    if not globals().get(var_name):
        missing_vars.append(var_name)

if missing_vars:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    logging.error(f"FATAL: Missing required environment variables ({', '.join(missing_vars)})")
    sys.exit(1)

if not CF_ZONE_ID:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    logging.warning("CF_ZONE_ID not set. DNS management requires the 'zonename' label on containers or manual zone specification.")