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
# dockflare/app/core/service_token_manager.py

import logging
from urllib.parse import urlparse

from app import config
from app.core import agent_key_store
from app.core.cloudflare_api import cf_api_request
from app.core.state_manager import get_agent_cf_token, set_agent_cf_token, clear_agent_cf_token


def _account_id():
    return config.CF_ACCOUNT_ID


def _parse_hostname(public_url):
    parsed = urlparse(public_url)
    return parsed.hostname


def ensure_agent_service_token(public_url):
    existing = get_agent_cf_token()
    existing_secret = agent_key_store.get_service_token_secret()
    if existing and existing_secret:
        return {**existing, "client_secret": existing_secret}

    account_id = _account_id()
    if not account_id:
        raise ValueError("CF_ACCOUNT_ID not configured")

    hostname = _parse_hostname(public_url)
    if not hostname:
        raise ValueError("Invalid DOCKFLARE_PUBLIC_URL")

    token_resp = cf_api_request(
        "POST",
        f"/accounts/{account_id}/access/service_tokens",
        json_data={"name": "dockflare-agents"}
    )
    token_result = token_resp.get("result", {})
    client_id = token_result.get("client_id")
    client_secret = token_result.get("client_secret")
    token_id = token_result.get("id")

    if not client_id or not client_secret or not token_id:
        raise RuntimeError("CF API did not return expected service token fields")

    app_resp = cf_api_request(
        "POST",
        f"/accounts/{account_id}/access/apps",
        json_data={
            "name": "DockFlare Agent API",
            "domain": f"{hostname}/api/v2/agents/",
            "type": "self_hosted",
            "session_duration": "24h",
            "app_launcher_visible": False,
        }
    )
    app_result = app_resp.get("result", {})
    app_uuid = app_result.get("id") or app_result.get("uid")

    if not app_uuid:
        raise RuntimeError("CF API did not return Access App UUID")

    policy_resp = cf_api_request(
        "POST",
        f"/accounts/{account_id}/access/apps/{app_uuid}/policies",
        json_data={
            "name": "DockFlare Agents",
            "decision": "non_identity",
            "precedence": 1,
            "include": [{"service_token": {"token_id": token_id}}]
        }
    )
    policy_result = policy_resp.get("result", {})
    policy_id = policy_result.get("id")

    bypass_resp = cf_api_request(
        "POST",
        f"/accounts/{account_id}/access/apps/{app_uuid}/policies",
        json_data={
            "name": "DockFlare Admin Bypass",
            "decision": "bypass",
            "precedence": 2,
            "include": [{"everyone": {}}]
        }
    )
    bypass_policy_id = bypass_resp.get("result", {}).get("id")

    agent_key_store.store_service_token_secret(client_secret)

    token_data = {
        "client_id": client_id,
        "token_id": token_id,
        "app_uuid": app_uuid,
        "policy_id": policy_id,
        "bypass_policy_id": bypass_policy_id,
    }
    set_agent_cf_token(token_data)

    return {**token_data, "client_secret": client_secret}


def get_agent_service_token():
    data = get_agent_cf_token()
    if not data:
        return None
    secret = agent_key_store.get_service_token_secret()
    if not secret:
        return None
    return {**data, "client_secret": secret}


def delete_agent_service_token():
    data = get_agent_cf_token()
    account_id = _account_id()

    if data and account_id:
        app_uuid = data.get("app_uuid")
        token_id = data.get("token_id")

        if app_uuid:
            try:
                cf_api_request("DELETE", f"/accounts/{account_id}/access/apps/{app_uuid}")
            except Exception as e:
                logging.warning("Failed to delete CF Access App %s: %s", app_uuid, e)

        if token_id:
            try:
                cf_api_request("DELETE", f"/accounts/{account_id}/access/service_tokens/{token_id}")
            except Exception as e:
                logging.warning("Failed to delete CF Service Token %s: %s", token_id, e)

    agent_key_store.clear_service_token_secret()
    clear_agent_cf_token()


def generate_compose_content(key_id, public_url, cloudflared_image="cloudflare/cloudflared:latest"):
    token_data = get_agent_service_token()
    if not token_data:
        raise ValueError("CF Service Token not configured")

    client_id = token_data["client_id"]
    client_secret = token_data["client_secret"]

    return f"""services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: dockflare-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - INFO=1
      - EXEC=1
      - DELETE=0
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_agent_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    environment:
      - DOCKFLARE_MASTER_URL={public_url}
      - DOCKFLARE_API_KEY={key_id}
      - CF_ACCESS_CLIENT_ID={client_id}
      - CF_ACCESS_CLIENT_SECRET={client_secret}
      - CLOUDFLARED_IMAGE={cloudflared_image}
      - DOCKER_HOST=tcp://dockflare-socket-proxy:2375
    volumes:
      - dockflare_agent_data:/app/data
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
"""


def generate_deploy_script(key_id, public_url, cloudflared_image="cloudflare/cloudflared:latest"):
    compose_content = generate_compose_content(key_id, public_url, cloudflared_image)

    return f"""#!/usr/bin/env bash
set -e

if ! docker compose version > /dev/null 2>&1 && ! docker-compose version > /dev/null 2>&1; then
  echo "Error: docker compose is not available. Please install Docker Compose." >&2
  exit 1
fi

COMPOSE_CMD="docker compose"
if ! docker compose version > /dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
fi

if ! docker network ls --format '{{{{.Name}}}}' | grep -q '^cloudflare-net$'; then
  echo "Creating external Docker network: cloudflare-net"
  docker network create cloudflare-net
fi

DEPLOY_DIR="$HOME/dockflare-agent"
mkdir -p "$DEPLOY_DIR"

cat > "$DEPLOY_DIR/docker-compose.yml" <<'COMPOSE'
{compose_content}COMPOSE

cd "$DEPLOY_DIR"
$COMPOSE_CMD up -d
echo "DockFlare Agent deployed successfully."
"""
