"""Local, restart-safe Agent decommission primitives."""

import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from threading import Thread

import docker


TOMBSTONE_PATH = os.getenv("DECOMMISSION_TOMBSTONE_PATH", "/app/data/decommission.json")
TUNNEL_CONTAINER_NAME = "dockflare-agent-tunnel"
AGENT_CONTAINER_NAME = "dockflare-agent"
IMAGE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,254}$")


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def load_tombstone(path=TOMBSTONE_PATH):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict) or value.get("phase") not in {"prepared", "finalized"}:
            return None
        return value
    except (OSError, ValueError):
        return None


def persist_tombstone(operation_id, agent_id, phase, path=TOMBSTONE_PATH):
    existing = load_tombstone(path) or {}
    if existing and (
        existing.get("operation_id") != operation_id
        or existing.get("agent_id") != agent_id
        or (existing.get("phase") == "finalized" and phase != "finalized")
    ):
        raise ValueError("decommission_tombstone_conflict")
    now = _iso_now()
    value = {
        "schema_version": 1,
        "operation_id": operation_id,
        "agent_id": agent_id,
        "phase": phase,
        "requested_self_action": "stop",
        "prepared_at": existing.get("prepared_at") or now,
        "finalized_at": now if phase == "finalized" else None,
    }
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=directory, delete=False, encoding="utf-8") as handle:
            json.dump(value, handle)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = handle.name
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
        return value
    except Exception:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def normalized_container_image(container):
    try:
        value = (container.attrs.get("Config") or {}).get("Image")
    except (AttributeError, TypeError):
        value = None
    if isinstance(value, str):
        candidate = value.strip()
        if IMAGE_REFERENCE_RE.fullmatch(candidate):
            return candidate
    return None


def stop_tunnel_container(client):
    """Stop, but never delete, the one fixed Agent-managed tunnel container."""
    try:
        container = client.containers.get(TUNNEL_CONTAINER_NAME)
    except docker.errors.NotFound:
        return "absent", None
    if getattr(container, "name", None) != TUNNEL_CONTAINER_NAME:
        return "failed", None
    image = normalized_container_image(container)
    try:
        container.reload()
        if getattr(container, "status", None) not in {"exited", "dead", "created"}:
            container.stop(timeout=15)
        container.reload()
        return ("stopped", image) if getattr(container, "status", None) != "running" else ("failed", image)
    except docker.errors.NotFound:
        return "absent", image
    except Exception:
        return "failed", image


def resolve_self_container(client, runtime_id=None):
    candidate_id = (runtime_id or os.getenv("HOSTNAME") or "").strip()
    if not candidate_id or not re.fullmatch(r"[a-fA-F0-9]{12,64}", candidate_id):
        return None
    try:
        container = client.containers.get(candidate_id)
    except Exception:
        return None
    full_id = str(getattr(container, "id", ""))
    if not full_id.startswith(candidate_id) and not candidate_id.startswith(full_id):
        return None
    labels = getattr(container, "labels", None) or {}
    service = labels.get("com.docker.compose.service")
    name = getattr(container, "name", None)
    if service != "dockflare-agent" and name != AGENT_CONTAINER_NAME:
        return None
    return container


def self_image_reference(client, runtime_id=None):
    container = resolve_self_container(client, runtime_id)
    return normalized_container_image(container) if container else None


def schedule_self_stop(client, runtime_id=None, delay_seconds=2):
    """Schedule an explicit Docker stop after the final ack response is received."""
    container = resolve_self_container(client, runtime_id)
    if not container:
        return False

    def stop_later():
        time.sleep(delay_seconds)
        try:
            container.stop(timeout=15)
        except Exception:
            return

    Thread(target=stop_later, name="AgentSelfStop", daemon=True).start()
    return True
