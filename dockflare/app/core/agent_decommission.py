"""Durable, ownership-safe DockFlare Agent decommission orchestration."""

import copy
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from app import tunnel_state
from app.core.access_manager import delete_cloudflare_access_application
from app.core.cloudflare_api import delete_cloudflare_dns_record, delete_tunnel_via_api
from app.core.state_manager import (
    agent_decommissions,
    add_agent_key,
    agents,
    list_agent_keys,
    managed_rules,
    revoke_agent_key,
    save_state,
    state_lock,
)
from app.core.tunnel_manager import update_cloudflare_config


TERMINAL_STATES = {"completed", "forced_completed"}
RETRYABLE_STATES = {"prepare_failed", "cleanup_failed", "finalize_failed", "force_failed", "timed_out"}
FORCEABLE_STATES = {
    "waiting_for_prepare", "prepare_failed", "timed_out", "cleanup_failed",
    "waiting_for_finalize", "finalize_failed",
}
IMAGE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,254}$")


def _bounded_int_env(name, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(os.getenv(name, str(default)))))
    except (TypeError, ValueError):
        return default


DEFAULT_TIMEOUT_SECONDS = _bounded_int_env("AGENT_DECOMMISSION_TIMEOUT_SECONDS", 180, 30, 1800)


class DecommissionError(RuntimeError):
    """Stable decommission failure safe to map to an API response."""

    def __init__(self, code, http_status=409):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _utcnow():
    return datetime.now(timezone.utc)


def _iso(value=None):
    return (value or _utcnow()).isoformat()


def _deadline():
    return _iso(_utcnow() + timedelta(seconds=DEFAULT_TIMEOUT_SECONDS))


def _valid_image_reference(value):
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    return candidate if IMAGE_REFERENCE_RE.fullmatch(candidate) else None


def _agent_rules(agent_id):
    return {
        key: copy.deepcopy(rule)
        for key, rule in managed_rules.items()
        if rule.get("source") == "agent" and rule.get("agent_id") == agent_id
    }


def _tunnel_disposition(agent_id, agent, rules):
    tunnel_id = agent.get("assigned_tunnel_id")
    ownership = agent.get("assigned_tunnel_ownership", "unknown")
    if not tunnel_id or ownership != "created_exclusive":
        return "preserve_adopted" if ownership == "adopted" else "unknown"
    if tunnel_state.get("id") == tunnel_id:
        return "preserve_shared"
    if any(
        other_id != agent_id and other.get("assigned_tunnel_id") == tunnel_id
        for other_id, other in agents.items()
    ):
        return "preserve_shared"
    owned_keys = set(rules)
    if any(
        key not in owned_keys and rule.get("tunnel_id") == tunnel_id
        for key, rule in managed_rules.items()
    ):
        return "preserve_shared"
    return "delete_exclusive"


def _build_resource_plan(agent_id, agent):
    rules = _agent_rules(agent_id)
    tunnel_id = agent.get("assigned_tunnel_id")
    dns_targets = sorted({
        (rule.get("zone_id"), rule.get("hostname"))
        for rule in rules.values()
        if rule.get("zone_id") and rule.get("hostname") and not rule.get("hostname", "").startswith("*.")
    })
    return {
        "tunnel_id": tunnel_id,
        "tunnel_disposition": _tunnel_disposition(agent_id, agent, rules),
        "rule_keys": sorted(rules),
        "dns_targets": [{"zone_id": zone_id, "hostname": hostname} for zone_id, hostname in dns_targets],
        "access_app_ids": sorted({
            rule.get("access_app_id") for rule in rules.values() if rule.get("access_app_id")
        }),
    }


def preview_decommission(agent_id):
    """Return a non-mutating, secret-safe preflight view for the admin UI."""
    with state_lock:
        agent = agents.get(agent_id)
        if not agent:
            raise DecommissionError("agent_not_found", 404)
        plan = _build_resource_plan(agent_id, agent)
        return {
            "agent_id": agent_id,
            "display_name": str(agent.get("display_name") or f"agent-{agent_id[:8]}")[:128],
            "last_seen": agent.get("last_seen"),
            "assigned_tunnel_name": agent.get("assigned_tunnel_name"),
            "resource_plan": {
                "tunnel_disposition": plan["tunnel_disposition"],
                "rule_count": len(plan["rule_keys"]),
                "dns_record_count": len(plan["dns_targets"]),
                "access_app_count": len(plan["access_app_ids"]),
            },
            "remote_actions": {
                "tunnel_container": "stop_only",
                "agent_container": (
                    "stop_scheduled"
                    if "self_stop.v1" in (agent.get("capabilities") or [])
                    else "manual"
                ),
            },
            "container_names": ["dockflare-agent-tunnel", "dockflare-agent"],
            "deployment_directory": "$HOME/dockflare-agent",
            "preserve_networks": ["cloudflare-net"],
        }


def _new_operation(agent_id, agent):
    operation_id = str(uuid.uuid4())
    command_id = str(uuid.uuid4())
    now = _iso()
    return {
        "operation_id": operation_id,
        "agent_id": agent_id,
        "display_name": str(agent.get("display_name") or f"agent-{agent_id[:8]}")[:128],
        "state": "waiting_for_prepare",
        "requested_at": now,
        "updated_at": now,
        "deadline_at": _deadline(),
        "prepare_command_id": command_id,
        "finalize_command_id": None,
        "requested_self_action": "stop",
        "agent_capabilities": copy.deepcopy(agent.get("capabilities") or []),
        "remote_results": {
            "tombstone_persisted": False,
            "tunnel_container": "pending",
            "agent_container": "stop_pending",
            "host_container_removal_required": True,
        },
        "resource_plan": _build_resource_plan(agent_id, agent),
        "cleanup_results": {},
        "host_cleanup_plan": {
            "agent_container_name": "dockflare-agent",
            "tunnel_container_name": "dockflare-agent-tunnel",
            "socket_proxy_container_name": "dockflare-socket-proxy",
            "compose_services": ["docker-socket-proxy", "dockflare-init", "dockflare-agent"],
            "compose_filename": "docker-compose.yml",
            "deployment_directory": "$HOME/dockflare-agent",
            "agent_image": None,
            "cloudflared_image": None,
            "preserve_networks": ["cloudflare-net"],
        },
        "last_error_code": None,
        "retry_count": 0,
        "forced": False,
        "durable_command": {
            "action": "prepare_decommission",
            "protocol_version": 1,
            "operation_id": operation_id,
            "command_id": command_id,
            "requested_self_action": "stop",
            "expected_tunnel_id": agent.get("assigned_tunnel_id"),
            "created_at": now,
        },
        "acknowledged_commands": [],
    }


def start_decommission(agent_id):
    """Persist or return one active decommission operation for an Agent."""
    with state_lock:
        agent = agents.get(agent_id)
        if not agent:
            raise DecommissionError("agent_not_found", 404)
        for operation in agent_decommissions.values():
            if operation.get("agent_id") == agent_id and operation.get("state") not in TERMINAL_STATES:
                return copy.deepcopy(operation), False
        operation = _new_operation(agent_id, agent)
        previous_agent = copy.deepcopy(agent)
        agent_decommissions[operation["operation_id"]] = operation
        agent.update({
            "decommission_operation_id": operation["operation_id"],
            "decommission_state": operation["state"],
        })
        if not save_state():
            agent.clear()
            agent.update(previous_agent)
            agent_decommissions.pop(operation["operation_id"], None)
            raise DecommissionError("persistence_failed", 503)
        return copy.deepcopy(operation), True


def get_operation(operation_id):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        return copy.deepcopy(operation) if operation else None


def command_for_agent(agent_id):
    with state_lock:
        agent = agents.get(agent_id)
        if not agent:
            return None
        operation_id = agent.get("decommission_operation_id")
        operation = agent_decommissions.get(operation_id)
        if not operation or operation.get("state") in TERMINAL_STATES:
            return None
        command = operation.get("durable_command")
        return copy.deepcopy(command) if command else None


def _set_failure(operation_id, state, code):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation:
            return
        previous_operation = copy.deepcopy(operation)
        operation["state"] = state
        operation["last_error_code"] = code
        operation["updated_at"] = _iso()
        agent = agents.get(operation.get("agent_id"))
        previous_agent = copy.deepcopy(agent) if agent else None
        if agent:
            agent["decommission_state"] = state
        if not save_state():
            operation.clear()
            operation.update(previous_operation)
            if agent is not None and previous_agent is not None:
                agent.clear()
                agent.update(previous_agent)
            logging.error("AGENT_DECOMMISSION: failed to persist %s for %s", state, operation_id)


def _transition_to_finalize(operation_id, cleanup_results):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation:
            raise DecommissionError("operation_not_found", 404)
        previous_operation = copy.deepcopy(operation)
        agent = agents.get(operation["agent_id"])
        previous_agent = copy.deepcopy(agent) if agent else None
        final_command_id = operation.get("finalize_command_id") or str(uuid.uuid4())
        command = {
            "action": "finalize_decommission",
            "protocol_version": 1,
            "operation_id": operation_id,
            "command_id": final_command_id,
            "requested_self_action": "stop",
        }
        operation.update({
            "state": "waiting_for_finalize",
            "updated_at": _iso(),
            "deadline_at": _deadline(),
            "finalize_command_id": final_command_id,
            "durable_command": command,
            "cleanup_results": cleanup_results,
            "last_error_code": None,
        })
        if agent:
            agent["decommission_state"] = "waiting_for_finalize"
        if not save_state():
            operation.clear()
            operation.update(previous_operation)
            if agent is not None and previous_agent is not None:
                agent.clear()
                agent.update(previous_agent)
            raise DecommissionError("persistence_failed", 503)


def _cleanup_snapshot(operation_id):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation:
            raise DecommissionError("operation_not_found", 404)
        if operation.get("state") not in {"remote_prepared", "cleanup_failed", "force_cleanup"}:
            raise DecommissionError("operation_busy")
        agent_id = operation["agent_id"]
        agent = agents.get(agent_id)
        if not agent:
            raise DecommissionError("agent_not_found", 404)
        previous_operation = copy.deepcopy(operation)
        previous_agent = copy.deepcopy(agent)
        rules = _agent_rules(agent_id)
        plan = _build_resource_plan(agent_id, agent)
        operation["state"] = "master_cleanup"
        operation["resource_plan"] = plan
        operation["updated_at"] = _iso()
        agent["decommission_state"] = "master_cleanup"
        if not save_state():
            operation.clear()
            operation.update(previous_operation)
            agent.clear()
            agent.update(previous_agent)
            raise DecommissionError("persistence_failed", 503)
        return agent_id, rules, plan


def _assert_cleanup_current(operation_id, agent_id):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        agent = agents.get(agent_id)
        if (
            not operation
            or operation.get("state") != "master_cleanup"
            or not agent
            or agent.get("decommission_operation_id") != operation_id
        ):
            raise DecommissionError("operation_changed")


def _cleanup_access_apps(operation_id, agent_id, owned_rules, app_ids):
    deleted = 0
    for app_id in app_ids:
        _assert_cleanup_current(operation_id, agent_id)
        with state_lock:
            shared = any(
                key not in owned_rules and rule.get("access_app_id") == app_id
                for key, rule in managed_rules.items()
            )
        if shared:
            continue
        if not delete_cloudflare_access_application(app_id):
            raise DecommissionError("access_cleanup_failed")
        deleted += 1
    return deleted


def _cleanup_dns_records(operation_id, agent_id, tunnel_id, targets):
    deleted = 0
    for target in targets:
        _assert_cleanup_current(operation_id, agent_id)
        with state_lock:
            still_owned = any(
                rule.get("source") == "agent"
                and rule.get("agent_id") == agent_id
                and rule.get("zone_id") == target["zone_id"]
                and rule.get("hostname") == target["hostname"]
                and rule.get("tunnel_id") == tunnel_id
                for rule in managed_rules.values()
            )
            shared_hostname = any(
                rule.get("agent_id") != agent_id
                and rule.get("zone_id") == target["zone_id"]
                and rule.get("hostname") == target["hostname"]
                for rule in managed_rules.values()
            )
        if not still_owned or shared_hostname:
            continue
        if not delete_cloudflare_dns_record(target["zone_id"], target["hostname"], tunnel_id):
            raise DecommissionError("dns_cleanup_failed")
        deleted += 1
    return deleted


def _cleanup_tunnel(operation_id, agent_id, tunnel_id):
    _assert_cleanup_current(operation_id, agent_id)
    with state_lock:
        agent = agents.get(agent_id)
        disposition = _tunnel_disposition(agent_id, agent, _agent_rules(agent_id)) if agent else "unknown"
    if not tunnel_id or disposition != "delete_exclusive":
        return disposition
    if not delete_tunnel_via_api(tunnel_id):
        raise DecommissionError("tunnel_cleanup_failed")
    return "deleted"


def _remove_agent_rules(operation_id, agent_id):
    _assert_cleanup_current(operation_id, agent_id)
    with state_lock:
        current_rules = _agent_rules(agent_id)
        previous_rules = {key: managed_rules.get(key) for key in current_rules}
        for key in current_rules:
            managed_rules.pop(key, None)
        if not save_state():
            managed_rules.update({key: rule for key, rule in previous_rules.items() if rule is not None})
            raise DecommissionError("persistence_failed", 503)
    return len(current_rules), previous_rules


def _restore_rules(previous_rules):
    with state_lock:
        managed_rules.update({key: rule for key, rule in previous_rules.items() if rule is not None})
        save_state()


def run_master_cleanup(operation_id):
    """Delete only resources still proven to belong exclusively to this Agent."""
    agent_id, rules, plan = _cleanup_snapshot(operation_id)
    results = {"access_apps_deleted": 0, "dns_records_deleted": 0, "rules_removed": 0, "tunnel": "preserved"}
    try:
        tunnel_id = plan.get("tunnel_id")
        results["access_apps_deleted"] = _cleanup_access_apps(
            operation_id, agent_id, rules, plan["access_app_ids"]
        )
        results["dns_records_deleted"] = _cleanup_dns_records(
            operation_id, agent_id, tunnel_id, plan["dns_targets"]
        )
        results["tunnel"] = _cleanup_tunnel(operation_id, agent_id, tunnel_id)
        results["rules_removed"], previous_rules = _remove_agent_rules(operation_id, agent_id)
        if tunnel_id and results["tunnel"] != "deleted" and not update_cloudflare_config(tunnel_id):
            _restore_rules(previous_rules)
            raise DecommissionError("tunnel_sync_failed")
        _transition_to_finalize(operation_id, results)
        return get_operation(operation_id)
    except DecommissionError as error:
        _set_failure(operation_id, "cleanup_failed", error.code)
        raise
    except Exception:
        logging.exception("AGENT_DECOMMISSION: cleanup failed for %s", operation_id)
        _set_failure(operation_id, "cleanup_failed", "cleanup_failed")
        raise DecommissionError("cleanup_failed")


def _validate_ack(operation, agent_id, payload):
    if operation.get("agent_id") != agent_id:
        raise DecommissionError("operation_agent_mismatch", 403)
    command = operation.get("durable_command") or {}
    if payload.get("command_id") != command.get("command_id"):
        raise DecommissionError("stale_command")
    if payload.get("operation_id") != operation.get("operation_id"):
        raise DecommissionError("stale_operation")


def record_ack(agent_id, operation_id, payload):
    """Persist an Agent acknowledgement, returning whether cleanup should run."""
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation:
            raise DecommissionError("operation_not_found", 404)
        command_id = payload.get("command_id")
        if not command_id:
            raise DecommissionError("invalid_payload", 400)
        if command_id in operation.get("acknowledged_commands", []):
            return copy.deepcopy(operation), False
        _validate_ack(operation, agent_id, payload)

        previous_operation = copy.deepcopy(operation)
        agent = agents.get(agent_id)
        previous_agent = copy.deepcopy(agent) if agent else None
        phase = payload.get("phase")
        if phase == "prepared":
            if operation.get("state") not in {"waiting_for_prepare", "prepare_failed", "timed_out"}:
                raise DecommissionError("invalid_operation_state")
            tunnel_result = payload.get("tunnel_container")
            if payload.get("tombstone_persisted") is not True or tunnel_result not in {"stopped", "absent"}:
                operation["state"] = "prepare_failed"
                operation["last_error_code"] = str(payload.get("error_code") or "prepare_failed")[:64]
                operation["updated_at"] = _iso()
                if not save_state():
                    operation.clear()
                    operation.update(previous_operation)
                    if agent is not None and previous_agent is not None:
                        agent.clear()
                        agent.update(previous_agent)
                    raise DecommissionError("persistence_failed", 503)
                raise DecommissionError(operation["last_error_code"])
            cloudflared_image = _valid_image_reference(payload.get("cloudflared_image"))
            agent_image = _valid_image_reference(payload.get("agent_image"))
            self_stop_capability = payload.get("self_stop_capability")
            if not cloudflared_image or (self_stop_capability == "supported" and not agent_image):
                raise DecommissionError("invalid_image_reference", 400)
            operation["remote_results"].update({
                "tombstone_persisted": True,
                "tunnel_container": tunnel_result,
                "self_stop_capability": self_stop_capability if self_stop_capability in {"supported", "manual"} else "manual",
            })
            operation["host_cleanup_plan"]["agent_image"] = agent_image
            operation["host_cleanup_plan"]["cloudflared_image"] = cloudflared_image
            operation["state"] = "remote_prepared"
            should_cleanup = True
        elif phase == "shutdown_scheduled":
            if operation.get("state") not in {"waiting_for_finalize", "finalize_failed", "timed_out"}:
                raise DecommissionError("invalid_operation_state")
            self_stop_capability = payload.get("self_stop_capability")
            operation["remote_results"]["self_stop_capability"] = (
                "supported" if self_stop_capability == "supported" else "manual"
            )
            operation["remote_results"]["agent_container"] = (
                "stop_scheduled" if self_stop_capability == "supported" else "manual_required"
            )
            operation["state"] = "shutdown_scheduled"
            should_cleanup = False
        else:
            raise DecommissionError("invalid_ack_phase", 400)

        operation.setdefault("acknowledged_commands", []).append(command_id)
        operation["durable_command"] = None
        operation["last_error_code"] = None
        operation["updated_at"] = _iso()
        if agent:
            agent["decommission_state"] = operation["state"]
        if not save_state():
            operation.clear()
            operation.update(previous_operation)
            if agent is not None and previous_agent is not None:
                agent.clear()
                agent.update(previous_agent)
            raise DecommissionError("persistence_failed", 503)
        return copy.deepcopy(operation), should_cleanup


def _revoke_bound_key(agent_id):
    receipts = []
    for token, metadata in list_agent_keys().items():
        if metadata.get("bound_agent_id") != agent_id or metadata.get("status") == "revoked":
            continue
        if not revoke_agent_key(token):
            _restore_bound_key(receipts)
            return False, []
        receipts.append((token, copy.deepcopy(metadata)))
    return True, receipts


def _restore_bound_key(revocation_receipt):
    for token, metadata in revocation_receipt or []:
        add_agent_key(token, metadata)


def complete_finalization(operation_id):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation or operation.get("state") != "shutdown_scheduled":
            raise DecommissionError("invalid_operation_state")
        agent_id = operation["agent_id"]
    key_revoked, revocation_receipt = _revoke_bound_key(agent_id)
    if not key_revoked:
        _set_failure(operation_id, "finalize_failed", "key_revocation_failed")
        raise DecommissionError("key_revocation_failed")
    with state_lock:
        operation = agent_decommissions[operation_id]
        previous_agent = agents.pop(agent_id, None)
        operation.update({"state": "completed", "updated_at": _iso(), "last_error_code": None})
        if not save_state():
            if previous_agent is not None:
                agents[agent_id] = previous_agent
            _restore_bound_key(revocation_receipt)
            operation["state"] = "finalize_failed"
            operation["last_error_code"] = "persistence_failed"
            raise DecommissionError("persistence_failed", 503)
        return copy.deepcopy(operation)


def retry_operation(operation_id):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation:
            raise DecommissionError("operation_not_found", 404)
        if operation.get("state") not in RETRYABLE_STATES:
            raise DecommissionError("operation_not_retryable")
        previous_operation = copy.deepcopy(operation)
        agent = agents.get(operation["agent_id"])
        previous_agent = copy.deepcopy(agent) if agent else None
        operation["retry_count"] = int(operation.get("retry_count") or 0) + 1
        operation["last_error_code"] = None
        operation["updated_at"] = _iso()
        retry_force = False
        if operation["state"] == "force_failed":
            if not save_state():
                operation.clear()
                operation.update(previous_operation)
                raise DecommissionError("persistence_failed", 503)
            retry_force = True
            rerun_cleanup = False
        elif operation["state"] == "cleanup_failed":
            if not save_state():
                operation.clear()
                operation.update(previous_operation)
                raise DecommissionError("persistence_failed", 503)
            rerun_cleanup = True
        else:
            command = "prepare_decommission" if not operation.get("finalize_command_id") else "finalize_decommission"
            command_id = str(uuid.uuid4())
            operation["durable_command"] = {
                "action": command,
                "protocol_version": 1,
                "operation_id": operation_id,
                "command_id": command_id,
                "requested_self_action": "stop",
            }
            if command == "prepare_decommission":
                operation["prepare_command_id"] = command_id
                operation["state"] = "waiting_for_prepare"
            else:
                operation["finalize_command_id"] = command_id
                operation["state"] = "waiting_for_finalize"
            operation["deadline_at"] = _deadline()
            if agent:
                agent["decommission_state"] = operation["state"]
            if not save_state():
                operation.clear()
                operation.update(previous_operation)
                if agent is not None and previous_agent is not None:
                    agent.clear()
                    agent.update(previous_agent)
                raise DecommissionError("persistence_failed", 503)
            rerun_cleanup = False
            retry_force = False
    if retry_force:
        return force_cleanup(operation_id)
    return run_master_cleanup(operation_id) if rerun_cleanup else get_operation(operation_id)


def force_cleanup(operation_id):
    with state_lock:
        operation = agent_decommissions.get(operation_id)
        if not operation:
            raise DecommissionError("operation_not_found", 404)
        if operation.get("state") in TERMINAL_STATES:
            return copy.deepcopy(operation)
        if operation.get("state") not in FORCEABLE_STATES and operation.get("state") != "force_failed":
            raise DecommissionError("operation_not_forceable")
        previous_operation = copy.deepcopy(operation)
        operation["forced"] = True
        operation["state"] = "force_cleanup"
        operation["updated_at"] = _iso()
        if not save_state():
            operation.clear()
            operation.update(previous_operation)
            raise DecommissionError("persistence_failed", 503)
        agent_id = operation["agent_id"]
    key_revoked, _ = _revoke_bound_key(agent_id)
    if not key_revoked:
        _set_failure(operation_id, "force_failed", "key_revocation_failed")
        raise DecommissionError("key_revocation_failed")
    try:
        run_master_cleanup(operation_id)
    except DecommissionError:
        _set_failure(operation_id, "force_failed", "force_cleanup_failed")
        raise
    with state_lock:
        operation = agent_decommissions[operation_id]
        previous_operation = copy.deepcopy(operation)
        previous_agent = agents.get(agent_id)
        operation.update({
            "state": "forced_completed",
            "updated_at": _iso(),
            "durable_command": None,
            "last_error_code": None,
        })
        operation["remote_results"]["remote_host_cleanup_required"] = True
        agents.pop(agent_id, None)
        if not save_state():
            operation.clear()
            operation.update(previous_operation)
            if previous_agent is not None:
                agents[agent_id] = previous_agent
                previous_agent["decommission_state"] = "force_failed"
            operation["state"] = "force_failed"
            operation["last_error_code"] = "persistence_failed"
            raise DecommissionError("persistence_failed", 503)
        return copy.deepcopy(operation)


def expire_due_operations(now=None):
    """Persist bounded prepare/finalize timeouts without triggering force cleanup."""
    current = now or _utcnow()
    changed = []
    with state_lock:
        previous_operations = {}
        previous_agents = {}
        for operation_id, operation in agent_decommissions.items():
            if operation.get("state") not in {"waiting_for_prepare", "waiting_for_finalize"}:
                continue
            try:
                deadline = datetime.fromisoformat(str(operation.get("deadline_at")).replace("Z", "+00:00"))
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            if deadline > current:
                continue
            previous_operations[operation_id] = copy.deepcopy(operation)
            agent = agents.get(operation.get("agent_id"))
            if agent:
                previous_agents[operation["agent_id"]] = copy.deepcopy(agent)
                agent["decommission_state"] = "timed_out"
            operation["state"] = "timed_out"
            operation["last_error_code"] = "agent_timeout"
            operation["updated_at"] = _iso(current)
            changed.append(operation_id)
        if changed and not save_state():
            for operation_id, previous in previous_operations.items():
                agent_decommissions[operation_id].clear()
                agent_decommissions[operation_id].update(previous)
            for agent_id, previous in previous_agents.items():
                agents[agent_id].clear()
                agents[agent_id].update(previous)
            return []
    return changed


def prune_completed_operations(now=None, retention_days=30):
    current = now or _utcnow()
    removed = {}
    with state_lock:
        for operation_id, operation in list(agent_decommissions.items()):
            if operation.get("state") not in TERMINAL_STATES:
                continue
            try:
                updated = datetime.fromisoformat(str(operation.get("updated_at")).replace("Z", "+00:00"))
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            if current - updated < timedelta(days=retention_days):
                continue
            removed[operation_id] = agent_decommissions.pop(operation_id)
        if removed and not save_state():
            agent_decommissions.update(removed)
            return []
    return sorted(removed)


def timeout_worker(stop_event, interval_seconds=5):
    while not stop_event.is_set():
        try:
            expire_due_operations()
            prune_completed_operations()
        except Exception:
            logging.exception("AGENT_DECOMMISSION: timeout worker failed")
        stop_event.wait(interval_seconds)


def serialize_operation(operation):
    """Return a public, secret-safe operation representation."""
    if not operation:
        return None
    allowed = {
        "operation_id", "agent_id", "display_name", "state", "requested_at", "updated_at",
        "deadline_at", "requested_self_action", "remote_results", "resource_plan",
        "cleanup_results", "host_cleanup_plan", "last_error_code", "retry_count", "forced",
    }
    result = {key: copy.deepcopy(value) for key, value in operation.items() if key in allowed}
    plan = operation.get("resource_plan") or {}
    result["resource_plan"] = {
        "tunnel_disposition": plan.get("tunnel_disposition", "unknown"),
        "rule_count": len(plan.get("rule_keys") or []),
        "dns_record_count": len(plan.get("dns_targets") or []),
        "access_app_count": len(plan.get("access_app_ids") or []),
    }
    if operation.get("state") in TERMINAL_STATES:
        plan = operation.get("host_cleanup_plan") or {}
        images = [
            _valid_image_reference(plan.get("agent_image")),
            "tecnativa/docker-socket-proxy:v0.4.1",
            "alpine:3.20",
            _valid_image_reference(plan.get("cloudflared_image")),
        ]
        image_args = " ".join(value for value in images if value)
        result["cleanup_commands"] = {
            "docker": "\n".join([
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'DEPLOY_DIR="${HOME:?}/dockflare-agent"',
                'if docker compose version >/dev/null 2>&1; then COMPOSE_CMD=(docker compose);',
                'elif docker-compose version >/dev/null 2>&1; then COMPOSE_CMD=(docker-compose);',
                'else echo "Error: Docker Compose is not available." >&2; exit 1; fi',
                "docker stop dockflare-agent-tunnel >/dev/null 2>&1 || true",
                "docker rm dockflare-agent-tunnel >/dev/null 2>&1 || true",
                'cd "$DEPLOY_DIR"',
                '"${COMPOSE_CMD[@]}" -f ./docker-compose.yml down --volumes',
                f"docker image rm {image_args} || true",
            ]),
            "deployment_files": 'cd "${HOME:?}" && rm -rf -- ./dockflare-agent',
        }
    return result
