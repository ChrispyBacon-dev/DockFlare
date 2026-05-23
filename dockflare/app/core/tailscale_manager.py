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
# dockflare/app/core/tailscale_manager.py
import json
import logging
import os
import re
import subprocess
import threading
import time
from typing import Dict, List, Optional

import requests

from app import config


class TailscaleCLIError(Exception):
    def __init__(self, message, returncode=None, stderr=None):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class TailscaleSocketError(TailscaleCLIError):
    pass


class TailscaleUntaggedNodeError(TailscaleCLIError):
    pass


class TailscaleFunnelACLError(TailscaleCLIError):
    pass


_oauth_lock = threading.Lock()
_oauth_token: Optional[str] = None
_oauth_token_expiry: float = 0.0


def _is_untagged_node_error(text: str) -> bool:
    return "tagged node" in text.lower() or "acl tag" in text.lower() or "must have at least one tag" in text.lower()


def _is_config_conflict_error(text: str) -> bool:
    return "conflict" in text.lower() or "already exists" in text.lower()


def _is_not_found_error(text: str) -> bool:
    return "not found" in text.lower() or "no such" in text.lower()


def _is_funnel_acl_error(text: str) -> bool:
    return "funnel" in text.lower() and ("acl" in text.lower() or "policy" in text.lower() or "not allowed" in text.lower())


def _tailscale_cmd(*args, timeout: int = None) -> str:
    effective_timeout = timeout or config.TAILSCALE_CLI_TIMEOUT
    socket_path = config.TAILSCALE_SOCKET
    cmd = ["tailscale", f"--socket={socket_path}"] + list(args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=effective_timeout
        )
    except FileNotFoundError:
        raise TailscaleCLIError("tailscale binary not found in PATH")
    except subprocess.TimeoutExpired:
        raise TailscaleCLIError(f"tailscale command timed out after {effective_timeout}s: {' '.join(args)}")

    if result.returncode != 0:
        stderr = result.stderr.strip()
        combined = (result.stdout + " " + stderr).strip()

        if "unix" in stderr.lower() and ("connect" in stderr.lower() or "no such file" in stderr.lower()):
            raise TailscaleSocketError(f"Cannot connect to tailscaled socket at {socket_path}: {stderr}", returncode=result.returncode, stderr=stderr)

        if _is_untagged_node_error(combined):
            raise TailscaleUntaggedNodeError(f"Node must be tagged: {combined}", returncode=result.returncode, stderr=stderr)

        if _is_funnel_acl_error(combined):
            raise TailscaleFunnelACLError(f"Funnel ACL policy error: {combined}", returncode=result.returncode, stderr=stderr)

        raise TailscaleCLIError(f"tailscale {args[0]} failed (rc={result.returncode}): {combined}", returncode=result.returncode, stderr=stderr)

    return result.stdout


def _strip_to_json(output: str) -> str:
    lines = output.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('{') or stripped.startswith('['):
            return '\n'.join(lines[i:])
    return output


def detect_version_mismatch() -> Optional[str]:
    try:
        out = _tailscale_cmd("version")
        match = re.search(r'TS_DEBUG_FAKE_IPC_VERSION=v?(\S+)', out)
        if match:
            return match.group(1)
        return None
    except TailscaleCLIError:
        return None


def get_node_info() -> Optional[Dict]:
    try:
        out = _tailscale_cmd("status", "--json")
        data = json.loads(_strip_to_json(out))
        self_node = data.get("Self", {})
        if not self_node:
            return None
        return {
            "machine_name": self_node.get("HostName") or self_node.get("DNSName", "").split(".")[0],
            "tailnet": data.get("MagicDNSSuffix", ""),
            "online": self_node.get("Online", False),
            "version": self_node.get("TailscaleIPs", []),
            "node_key": self_node.get("PublicKey"),
            "tags": self_node.get("Tags", []),
        }
    except (TailscaleCLIError, json.JSONDecodeError, KeyError) as e:
        logging.warning("TAILSCALE: get_node_info failed: %s", e)
        return None


def get_current_serve_state() -> Dict[str, Dict]:
    try:
        out = _tailscale_cmd("serve", "status", "--json")
        raw = out.strip()
        if not raw or raw in ("null", "{}"):
            return {}
        data = json.loads(_strip_to_json(raw))
        services = data.get("Services") or {}
        result = {}
        for svc_name, svc_data in services.items():
            for port_str, port_data in (svc_data.get("Ports") or {}).items():
                key = f"{svc_name}:{port_str}"
                result[key] = {
                    "svc_name": svc_name,
                    "port": port_str,
                    "handlers": port_data,
                }
        return result
    except (TailscaleCLIError, json.JSONDecodeError) as e:
        logging.warning("TAILSCALE: get_current_serve_state failed: %s", e)
        return {}


def get_current_funnel_state() -> Dict[str, bool]:
    try:
        out = _tailscale_cmd("funnel", "status", "--json")
        raw = out.strip()
        if not raw or raw in ("null", "{}"):
            return {}
        data = json.loads(_strip_to_json(raw))
        return data.get("AllowFunnel") or {}
    except (TailscaleCLIError, json.JSONDecodeError) as e:
        logging.warning("TAILSCALE: get_current_funnel_state failed: %s", e)
        return {}


def _build_svc_name(name: str) -> str:
    prefix = config.TAILSCALE_SERVICE_PREFIX or ""
    return f"svc:{prefix}{name}"


def add_service(name: str, port: int, protocol: str, destination: str) -> bool:
    full_name = _build_svc_name(name)
    proto_flag = f"--{protocol}={port}"
    try:
        _tailscale_cmd("serve", "--bg", f"--service={full_name}", proto_flag, destination)
        logging.info("TAILSCALE: Added service %s -> %s://%s", full_name, protocol, destination)
        return True
    except TailscaleUntaggedNodeError:
        raise
    except TailscaleCLIError as e:
        if _is_config_conflict_error(str(e)):
            logging.warning("TAILSCALE: Conflict adding %s, clearing and retrying", full_name)
            try:
                _clear_service_by_full_name(full_name)
                _tailscale_cmd("serve", "--bg", f"--service={full_name}", proto_flag, destination)
                logging.info("TAILSCALE: Added service %s after conflict clear", full_name)
                return True
            except TailscaleCLIError as retry_err:
                logging.error("TAILSCALE: Retry failed for %s: %s", full_name, retry_err)
                raise
        raise


def _clear_service_by_full_name(full_name: str) -> None:
    try:
        _tailscale_cmd("serve", f"--service={full_name}", "--yes", "reset")
    except TailscaleCLIError as e:
        if not _is_not_found_error(str(e)):
            raise


def clear_service(name: str) -> None:
    _clear_service_by_full_name(_build_svc_name(name))


def _remove_service_by_full_name(full_name: str) -> bool:
    if not full_name.startswith("svc:"):
        logging.error("TAILSCALE: Refusing to remove service without svc: prefix: %s", full_name)
        return False
    try:
        _tailscale_cmd("serve", f"--service={full_name}", "--yes", "reset")
        logging.info("TAILSCALE: Removed service %s", full_name)
        return True
    except TailscaleCLIError as e:
        if _is_not_found_error(str(e)):
            logging.debug("TAILSCALE: Service %s already absent", full_name)
            return True
        logging.error("TAILSCALE: Failed to remove service %s: %s", full_name, e)
        return False


def remove_service(name: str) -> bool:
    return _remove_service_by_full_name(_build_svc_name(name))


def enable_funnel(funnel_port: int, protocol: str, destination: str, path: str = "") -> bool:
    proto_flag = f"--{protocol}={funnel_port}"
    dest = destination + (path or "")
    try:
        _tailscale_cmd("funnel", "--bg", proto_flag, dest)
        logging.info("TAILSCALE: Enabled funnel %s:%s -> %s", protocol, funnel_port, dest)
        return True
    except TailscaleFunnelACLError:
        raise
    except TailscaleCLIError as e:
        logging.error("TAILSCALE: Failed to enable funnel %s:%s: %s", protocol, funnel_port, e)
        return False


def disable_funnel(funnel_port: int, protocol: str) -> bool:
    proto_flag = f"--{protocol}={funnel_port}"
    try:
        _tailscale_cmd("funnel", proto_flag, "off")
        logging.info("TAILSCALE: Disabled funnel %s:%s", protocol, funnel_port)
        return True
    except TailscaleCLIError as e:
        if _is_not_found_error(str(e)):
            return True
        logging.error("TAILSCALE: Failed to disable funnel %s:%s: %s", protocol, funnel_port, e)
        return False


def _get_oauth_token() -> str:
    global _oauth_token, _oauth_token_expiry

    with _oauth_lock:
        now = time.time()
        if _oauth_token and now < (_oauth_token_expiry - 300):
            return _oauth_token

        client_id = config.TAILSCALE_OAUTH_CLIENT_ID
        client_secret = config.TAILSCALE_OAUTH_CLIENT_SECRET

        if not client_id or not client_secret:
            raise TailscaleCLIError("Tailscale OAuth credentials not configured")

        resp = requests.post(
            "https://api.tailscale.com/api/v2/oauth/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            timeout=15,
        )
        resp.raise_for_status()
        token_data = resp.json()
        _oauth_token = token_data["access_token"]
        _oauth_token_expiry = now + token_data.get("expires_in", 3600)
        return _oauth_token


def sync_service_definition(name: str, endpoints: List[Dict]) -> bool:
    full_name = _build_svc_name(name)
    tailnet = config.TAILSCALE_TAILNET or "-"
    try:
        token = _get_oauth_token()
        url = f"https://api.tailscale.com/api/v2/tailnet/{tailnet}/services/{full_name}"
        resp = requests.put(
            url,
            json={"endpoints": endpoints},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        logging.info("TAILSCALE: Synced service definition for %s", full_name)
        return True
    except Exception as e:
        logging.error("TAILSCALE: Failed to sync service definition for %s: %s", full_name, e)
        return False


def initialize_tailscale() -> bool:
    from app import tailscale_state

    socket_path = config.TAILSCALE_SOCKET
    if not os.path.exists(socket_path):
        msg = f"tailscaled socket not found at {socket_path}"
        logging.warning("TAILSCALE: %s", msg)
        tailscale_state["last_error"] = msg
        return False

    try:
        _tailscale_cmd("version")
    except TailscaleCLIError as e:
        msg = f"tailscale binary check failed: {e}"
        logging.error("TAILSCALE: %s", msg)
        tailscale_state["last_error"] = msg
        return False

    mismatch = detect_version_mismatch()
    tailscale_state["version_mismatch"] = mismatch is not None
    if mismatch:
        logging.warning("TAILSCALE: Version mismatch detected (fake IPC version: %s)", mismatch)

    node = get_node_info()
    if node:
        tailscale_state["node"] = node
        tailscale_state["last_error"] = None
        logging.info("TAILSCALE: Initialized. Node: %s, online: %s", node.get("machine_name"), node.get("online"))
    else:
        tailscale_state["last_error"] = "Could not retrieve node info"
        logging.warning("TAILSCALE: Node info unavailable after init")

    return True


def cleanup_all_tailscale_services() -> int:
    removed = 0
    try:
        current = get_current_serve_state()
        seen_svcs = set()
        for key, svc_data in current.items():
            svc_name = svc_data.get("svc_name", "")
            if svc_name.startswith("svc:") and svc_name not in seen_svcs:
                seen_svcs.add(svc_name)
                if _remove_service_by_full_name(svc_name):
                    removed += 1
    except Exception as e:
        logging.error("TAILSCALE: cleanup_all_tailscale_services failed: %s", e)
    return removed
