import copy
import itertools
import logging
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit


EVENT_DEFINITIONS = {
    "rule.activated": ("rule_activated", "success", False),
    "rule.restored": ("rule_restored", "success", False),
    "rule.pending_deletion": ("rule_pending_deletion", "warning", False),
    "rule.deleted": ("rule_deleted", "info", True),
    "cloudflare.tunnel_failure": ("cloudflare_tunnel_failure", "failure", True),
    "cloudflare.dns_failure": ("cloudflare_dns_failure", "failure", True),
    "cloudflare.access_failure": ("cloudflare_access_failure", "failure", True),
    "docker.listener_failure": ("docker_listener_failure", "failure", True),
    "agent.offline": ("agent_offline", "failure", True),
    "agent.online": ("agent_online", "success", True),
    "agent.enrolled": ("agent_enrolled", "success", True),
    "agent.enrollment_failed": ("agent_enrollment_failed", "failure", True),
    "agent.decommission_started": ("agent_decommission_started", "warning", False),
    "agent.decommission_completed": ("agent_decommission_completed", "success", True),
    "agent.decommission_failed": ("agent_decommission_failed", "failure", True),
    "agent.decommission_stalled": ("agent_decommission_stalled", "warning", True),
    "tunnel.down": ("tunnel_down", "failure", True),
    "tunnel.recovered": ("tunnel_recovered", "success", True),
    "access.policy_created": ("access_policy_created", "success", False),
    "access.policy_updated": ("access_policy_updated", "info", False),
    "access.policy_deleted": ("access_policy_deleted", "info", False),
}

DEFAULT_NOTIFICATION_CONFIG = {
    "enabled": False,
    "urls": [],
    "events": {definition[0]: definition[2] for definition in EVENT_DEFINITIONS.values()},
    "failure_cooldown_seconds": 900,
}

BOOTSTRAP_SUPPRESSED_EVENTS = {
    "rule.activated",
    "rule.restored",
    "rule.pending_deletion",
    "rule.deleted",
    "agent.online",
    "agent.enrolled",
    "agent.decommission_started",
    "agent.decommission_completed",
    "tunnel.recovered",
    "access.policy_created",
    "access.policy_updated",
    "access.policy_deleted",
}

COOLDOWN_EVENTS = {
    "cloudflare.tunnel_failure",
    "cloudflare.dns_failure",
    "cloudflare.access_failure",
    "docker.listener_failure",
    "agent.offline",
    "agent.enrollment_failed",
    "agent.decommission_failed",
    "agent.decommission_stalled",
    "tunnel.down",
}

RECOVERY_PAIRS = {
    "agent.online": "agent.offline",
    "tunnel.recovered": "tunnel.down",
}

TITLE_MAP = {
    "rule.activated": "✅ DockFlare — Rule activated",
    "rule.restored": "✅ DockFlare — Rule restored",
    "rule.pending_deletion": "⚠️ DockFlare — Rule scheduled for deletion",
    "rule.deleted": "ℹ️ DockFlare — Rule deleted",
    "cloudflare.tunnel_failure": "❌ DockFlare — Tunnel update failed",
    "cloudflare.dns_failure": "❌ DockFlare — DNS operation failed",
    "cloudflare.access_failure": "❌ DockFlare — Access operation failed",
    "docker.listener_failure": "❌ DockFlare — Docker listener stopped",
    "agent.offline": "🔴 DockFlare — Agent offline",
    "agent.online": "🟢 DockFlare — Agent recovered",
    "agent.enrolled": "✅ DockFlare — Agent enrolled",
    "agent.enrollment_failed": "❌ DockFlare — Agent enrollment failed",
    "agent.decommission_started": "⚠️ DockFlare — Agent decommission started",
    "agent.decommission_completed": "✅ DockFlare — Agent decommission completed",
    "agent.decommission_failed": "❌ DockFlare — Agent decommission failed",
    "agent.decommission_stalled": "⚠️ DockFlare — Agent decommission stalled",
    "tunnel.down": "🔴 DockFlare — Tunnel down",
    "tunnel.recovered": "🟢 DockFlare — Tunnel recovered",
    "access.policy_created": "✅ DockFlare — Access Policy created",
    "access.policy_updated": "ℹ️ DockFlare — Access Policy updated",
    "access.policy_deleted": "ℹ️ DockFlare — Access Policy deleted",
    "notification.test": "🔔 DockFlare — Test notification",
}

STATUS_MAP = {
    "agent.offline": "Offline",
    "agent.online": "Online",
    "tunnel.down": "Down",
    "tunnel.recovered": "Running",
    "agent.enrolled": "Enrolled",
    "agent.enrollment_failed": "Enrollment failed",
    "agent.decommission_started": "In progress",
    "agent.decommission_completed": "Completed",
    "agent.decommission_failed": "Failed",
    "agent.decommission_stalled": "Timed out",
    "access.policy_created": "Created",
    "access.policy_updated": "Updated",
    "access.policy_deleted": "Deleted",
}


def normalize_notification_config(value):
    normalized = copy.deepcopy(DEFAULT_NOTIFICATION_CONFIG)
    if not isinstance(value, dict):
        return normalized

    normalized["enabled"] = bool(value.get("enabled", False))
    urls = value.get("urls", [])
    if isinstance(urls, list):
        seen = set()
        valid_shape = []
        for item in urls:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if not item or len(item.encode("utf-8")) > 4096 or item in seen:
                continue
            seen.add(item)
            valid_shape.append(item)
            if len(valid_shape) == 32:
                break
        normalized["urls"] = valid_shape

    supplied_events = value.get("events", {})
    if isinstance(supplied_events, dict):
        for event_key in normalized["events"]:
            if event_key in supplied_events:
                normalized["events"][event_key] = bool(supplied_events[event_key])

    cooldown = value.get("failure_cooldown_seconds", 900)
    if isinstance(cooldown, int) and not isinstance(cooldown, bool) and 60 <= cooldown <= 86400:
        normalized["failure_cooldown_seconds"] = cooldown
    return normalized


def sanitize_service(value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if not parsed.scheme:
        return value[:256] if all(char not in value for char in ("?", "#", "@")) else None
    try:
        hostname = parsed.hostname
        port_value = parsed.port
    except ValueError:
        return parsed.scheme[:32] if parsed.scheme else None
    if not hostname:
        return parsed.scheme
    port = f":{port_value}" if port_value else ""
    return urlunsplit((parsed.scheme, f"{hostname}{port}", parsed.path or "", "", ""))[:256]


def redact_destination(url):
    if not isinstance(url, str):
        return "configured destination"
    try:
        scheme = urlsplit(url.strip()).scheme.lower()
    except ValueError:
        scheme = ""
    if not scheme or not scheme.replace("+", "").replace("-", "").isalnum():
        return "configured destination"
    return f"{scheme}://configured destination"


def public_resource_url(hostname, path=None):
    """Return a safe HTTPS URL for a public rule hostname, if it is linkable."""
    if not isinstance(hostname, str):
        return None
    hostname = hostname.strip()
    if not hostname or hostname.startswith("*.") or any(char in hostname for char in ("@", "?", "#", "/")):
        return None
    try:
        parsed = urlsplit(f"https://{hostname}")
        if not parsed.hostname or parsed.username or parsed.password:
            return None
        # Reject values that urlsplit normalized into something other than a host[:port].
        if parsed.netloc.lower() != hostname.lower():
            return None
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return None
    except (TypeError, ValueError):
        return None
    safe_path = str(path or "").strip()
    if safe_path and not safe_path.startswith("/"):
        safe_path = f"/{safe_path}"
    if any(char in safe_path for char in ("?", "#", "\r", "\n")):
        return None
    return urlunsplit(("https", hostname, safe_path, "", ""))[:768]


class NotificationManager:
    def __init__(self, queue_size=100, max_body_chars=4000, resource_limit=10):
        self._queue_size = max(1, int(queue_size))
        self._max_body_chars = max(256, int(max_body_chars))
        self._resource_limit = max(1, int(resource_limit))
        self._queue = queue.PriorityQueue(maxsize=self._queue_size)
        self._sequence = itertools.count()
        self._lock = threading.RLock()
        self._config = normalize_notification_config(None)
        self._apprise = None
        self._available = False
        self._invalid_destination_count = 0
        self._stop_event = None
        self._worker = None
        self._accepting = True
        self._bootstrap = True
        self._cooldowns = {}
        self._outages_emitted = set()
        self._test_jobs = {}
        self._dropped_events = 0
        self._last_drop_log_at = 0.0
        self._last_attempt_at = None
        self._last_success_at = None
        self._last_failure_at = None
        self._agent_health = {}
        self._tunnel_health = {}
        self._intentional_tunnels = {}

    @staticmethod
    def _load_apprise():
        import apprise
        return apprise

    def _build_apprise(self, urls, reject_invalid=False):
        try:
            apprise_module = self._load_apprise()
            asset = apprise_module.AppriseAsset(
                app_id="DockFlare",
                app_desc="DockFlare Notifications",
                app_url="https://dockflare.app",
                secure_logging=True,
            )
            instance = apprise_module.Apprise(asset=asset)
        except Exception as exc:
            logging.error("NOTIFY_CONFIG: Apprise unavailable (%s).", type(exc).__name__)
            return None, [(0, "unavailable")]

        invalid = []
        for index, url in enumerate(urls, 1):
            try:
                if not instance.add(url):
                    invalid.append((index, self._safe_scheme(url)))
            except Exception:
                invalid.append((index, self._safe_scheme(url)))
        if reject_invalid and invalid:
            return None, invalid
        return instance if len(instance) else None, invalid

    @staticmethod
    def _safe_scheme(url):
        try:
            scheme = urlsplit(url).scheme.lower()
        except (TypeError, ValueError):
            return "unknown"
        return scheme if scheme and scheme.replace("+", "").replace("-", "").isalnum() else "unknown"

    def validate_urls(self, urls):
        if not isinstance(urls, list) or len(urls) > 32:
            return False, [(0, "invalid")]
        for index, url in enumerate(urls, 1):
            if not isinstance(url, str) or not url.strip() or len(url.strip().encode("utf-8")) > 4096:
                return False, [(index, self._safe_scheme(url))]
        normalized = normalize_notification_config({"urls": urls})["urls"]
        _instance, invalid = self._build_apprise(normalized, reject_invalid=True)
        return not invalid, invalid

    def configure(self, value):
        normalized = normalize_notification_config(value)
        instance = None
        invalid = []
        if normalized["urls"]:
            instance, invalid = self._build_apprise(normalized["urls"])
        with self._lock:
            self._config = normalized
            self._apprise = instance
            self._invalid_destination_count = len(invalid)
            self._available = instance is not None and len(instance) > 0
        if invalid:
            logging.warning("NOTIFY_CONFIG: Skipped %s invalid destination(s).", len(invalid))
        logging.info(
            "NOTIFY_CONFIG: enabled=%s configured=%s valid=%s",
            normalized["enabled"],
            len(normalized["urls"]),
            len(instance) if instance is not None else 0,
        )
        return self.get_public_status()

    def start(self, stop_event):
        with self._lock:
            if self._worker and self._worker.is_alive():
                return self._worker
            self._stop_event = stop_event
            self._accepting = True
            self._worker = threading.Thread(target=self._run, name="NotificationWorker", daemon=True)
            self._worker.start()
            logging.info("NOTIFY_WORKER: Started.")
            return self._worker

    def stop(self, timeout_seconds=5):
        with self._lock:
            self._accepting = False
            worker = self._worker
        try:
            self._queue.put_nowait((-1, next(self._sequence), None))
        except queue.Full:
            pass
        if worker and worker.is_alive():
            worker.join(timeout=max(0, timeout_seconds))

    def begin_bootstrap(self):
        with self._lock:
            self._bootstrap = True

    def end_bootstrap(self):
        with self._lock:
            self._bootstrap = False

    def emit(self, event_type, resource_id, context=None, notify_type=None):
        return self._enqueue(event_type, resource_id, context, notify_type, False, None, 10)

    def send_test(self):
        job_id = str(uuid.uuid4())
        with self._lock:
            self._expire_test_jobs_locked()
            self._test_jobs[job_id] = {
                "status": "pending",
                "created_at": time.time(),
                "completed_at": None,
            }
        accepted = self._enqueue(
            "notification.test",
            "test",
            {"message": "DockFlare notification delivery is configured correctly."},
            "info",
            True,
            job_id,
            0,
        )
        if not accepted:
            with self._lock:
                self._test_jobs[job_id].update({"status": "failure", "completed_at": self._utc_now()})
        return job_id, accepted

    def get_test_status(self, job_id):
        with self._lock:
            self._expire_test_jobs_locked()
            value = self._test_jobs.get(job_id)
            return copy.deepcopy(value) if value else None

    def _expire_test_jobs_locked(self):
        cutoff = time.time() - 600
        for job_id in [key for key, value in self._test_jobs.items() if value["created_at"] < cutoff]:
            self._test_jobs.pop(job_id, None)

    def _enqueue(self, event_type, resource_id, context, notify_type, is_test, job_id, priority):
        if event_type != "notification.test" and event_type not in EVENT_DEFINITIONS:
            return False
        safe_resource = str(resource_id or "unknown")[:512]
        now = time.monotonic()
        cooldown_key = None
        outage_key = None
        with self._lock:
            config_snapshot = copy.deepcopy(self._config)
            if not self._accepting or not config_snapshot["enabled"] or not self._available:
                return False
            if not is_test:
                setting_key, default_type, _default_enabled = EVENT_DEFINITIONS[event_type]
                if not config_snapshot["events"].get(setting_key, False):
                    return False
                if self._bootstrap and event_type in BOOTSTRAP_SUPPRESSED_EVENTS:
                    logging.info("NOTIFY_SUPPRESSED: %s during bootstrap.", event_type)
                    return False
                notify_type = notify_type or default_type
                cooldown_key = f"{event_type}:{safe_resource}"
                if event_type in COOLDOWN_EVENTS:
                    last = self._cooldowns.get(cooldown_key)
                    if last is not None and now - last < config_snapshot["failure_cooldown_seconds"]:
                        logging.info("NOTIFY_SUPPRESSED: %s cooldown active.", event_type)
                        return False
                recovery_for = RECOVERY_PAIRS.get(event_type)
                if recovery_for:
                    outage_key = f"{recovery_for}:{safe_resource}"
                    if outage_key not in self._outages_emitted:
                        return False

        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "resource_id": safe_resource,
            "occurred_at": self._utc_now(),
            "notify_type": notify_type or "info",
            "context": self._sanitize_context(context or {}),
            "is_test": is_test,
            "job_id": job_id,
        }
        try:
            self._queue.put_nowait((priority, next(self._sequence), event))
            with self._lock:
                if cooldown_key and event_type in COOLDOWN_EVENTS:
                    self._cooldowns[cooldown_key] = now
                    self._outages_emitted.add(cooldown_key)
                if outage_key:
                    self._outages_emitted.discard(outage_key)
                    self._cooldowns.pop(outage_key, None)
            logging.info("NOTIFY_QUEUED: %s event_id=%s", event_type, event["event_id"])
            return True
        except queue.Full:
            with self._lock:
                self._dropped_events += 1
                if now - self._last_drop_log_at >= 60:
                    logging.warning("NOTIFY_DROPPED: Notification queue is full.")
                    self._last_drop_log_at = now
            return False

    def _run(self):
        while True:
            stop_requested = self._stop_event is not None and self._stop_event.is_set()
            if stop_requested and self._queue.empty():
                break
            try:
                _priority, _sequence, event = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if event is None:
                self._queue.task_done()
                if stop_requested or not self._accepting:
                    break
                continue
            try:
                self._deliver(event)
            except Exception as exc:
                logging.error(
                    "NOTIFY_FAILED: event_type=%s event_id=%s error=%s",
                    event["event_type"], event["event_id"], type(exc).__name__,
                )
                self._record_delivery(event, False)
            finally:
                self._queue.task_done()
        logging.info("NOTIFY_WORKER: Stopped.")

    def _deliver(self, event):
        with self._lock:
            instance = self._apprise
        if instance is None:
            self._record_delivery(event, False)
            return
        title, body = self._render(event)
        notify_type = self._resolve_notify_type(event["notify_type"])
        started = time.monotonic()
        success = bool(instance.notify(title=title, body=body, notify_type=notify_type))
        duration = time.monotonic() - started
        self._record_delivery(event, success)
        log_method = logging.info if success else logging.error
        log_method(
            "%s: event_type=%s event_id=%s destinations=%s duration=%.2fs",
            "NOTIFY_DELIVERED" if success else "NOTIFY_FAILED",
            event["event_type"],
            event["event_id"],
            len(instance),
            duration,
        )

    def _resolve_notify_type(self, value):
        try:
            apprise_module = self._load_apprise()
            return {
                "info": apprise_module.NotifyType.INFO,
                "success": apprise_module.NotifyType.SUCCESS,
                "warning": apprise_module.NotifyType.WARNING,
                "failure": apprise_module.NotifyType.FAILURE,
            }.get(value, apprise_module.NotifyType.INFO)
        except Exception:
            return value

    def _record_delivery(self, event, success):
        completed_at = self._utc_now()
        with self._lock:
            self._last_attempt_at = completed_at
            if success:
                self._last_success_at = completed_at
            else:
                self._last_failure_at = completed_at
            job_id = event.get("job_id")
            if job_id and job_id in self._test_jobs:
                self._test_jobs[job_id].update({
                    "status": "success" if success else "failure",
                    "completed_at": completed_at,
                })

    def _render(self, event):
        event_type = event["event_type"]
        context = event["context"]
        title = TITLE_MAP.get(event_type, "🔔 DockFlare — Notification")
        resources = context.get("resources") if isinstance(context.get("resources"), list) else []
        if len(resources) > 1 and event_type.startswith("rule."):
            title = title.replace("Rule ", f"{len(resources)} rules ")

        lines = []
        message = context.get("message")
        if message:
            lines.append(str(message))

        if resources:
            rendered_resources = []
            for resource in resources[: self._resource_limit]:
                if not isinstance(resource, dict):
                    continue
                hostname = str(resource.get("hostname") or resource.get("key") or "resource")[:255]
                path = str(resource.get("path") or "")[:255]
                clickable_url = public_resource_url(hostname, path)
                rendered_resources.append(clickable_url or f"{hostname}{path}")
            if len(rendered_resources) == 1:
                lines.append(f"Service: {rendered_resources[0]}")
            elif rendered_resources:
                lines.append("Affected services:")
                lines.extend(f"- {resource}" for resource in rendered_resources)
            omitted = len(resources) - self._resource_limit
            if omitted > 0:
                lines.append(f"- ... and {omitted} more")

        if not resources and context.get("hostname"):
            service_url = public_resource_url(context["hostname"], context.get("path"))
            if service_url:
                lines.append(f"Service: {service_url}")
            else:
                lines.append(f"Hostname: {context['hostname']}")

        if context.get("operation"):
            lines.append(f"Operation: {context['operation']}")
        if event_type in STATUS_MAP:
            lines.append(f"Status: {STATUS_MAP[event_type]}")
        if context.get("source"):
            source = str(context["source"])
            lines.append(f"Source: {source[:1].upper()}{source[1:]}")
        for key, label in (("container_name", "Container"), ("agent_name", "Agent"), ("tunnel_name", "Tunnel")):
            if context.get(key) not in (None, ""):
                lines.append(f"{label}: {context[key]}")

        if context.get("policy_name"):
            lines.append(f"Access Policy: {context['policy_name']}")
        if context.get("policy_type"):
            lines.append(f"Policy type: {context['policy_type']}")
        if context.get("identity_provider_count"):
            lines.append(f"Identity providers: {context['identity_provider_count']}")
        if context.get("rules_count"):
            rules_label = "Managed rules" if event_type.startswith("agent.decommission_") else "Policy rules"
            lines.append(f"{rules_label}: {context['rules_count']}")
        if context.get("affected_service_count"):
            lines.append(f"Affected services: {context['affected_service_count']}")

        if context.get("delete_at"):
            lines.append(f"Deletion deadline: {context['delete_at']}")
        if context.get("grace_period_seconds"):
            lines.append(f"Grace period: {context['grace_period_seconds']} seconds")
        if context.get("retry_count"):
            lines.append(f"Retry count: {context['retry_count']}")
        if context.get("service"):
            origin = sanitize_service(context["service"])
            if origin:
                lines.append(f"Origin: {origin}")

        technical_fields = [
            (label, context[key])
            for key, label in (
                ("container_id", "Container ID"), ("agent_id", "Agent ID"),
                ("tunnel_id", "Tunnel ID"), ("operation_id", "Operation ID"),
                ("policy_id", "Policy ID"),
            )
            if context.get(key) not in (None, "")
        ]
        if technical_fields:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append("Technical details")
            lines.extend(f"{label}: {value}" for label, value in technical_fields)

        if context.get("public_url"):
            public_url = sanitize_service(context["public_url"])
            if public_url:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(f"Dashboard: {public_url}")
        if not lines:
            lines.append(f"Event: {event_type}")
        body = "\n".join(lines)
        if len(body) > self._max_body_chars:
            body = body[: self._max_body_chars - 16].rstrip() + "\n[truncated]"
        return title, body

    def _sanitize_context(self, context):
        allowed = {
            "message", "operation", "hostname", "path", "service", "source",
            "container_name", "container_id", "agent_name", "agent_id",
            "tunnel_name", "tunnel_id", "delete_at", "grace_period_seconds",
            "retry_count", "resources", "public_url", "operation_id",
            "policy_name", "policy_id", "policy_type", "identity_provider_count",
            "rules_count", "affected_service_count",
        }
        sanitized = {}
        for key in allowed:
            value = context.get(key)
            if value is None:
                continue
            if key == "resources" and isinstance(value, list):
                sanitized[key] = [
                    {
                        field: str(item[field])[:512]
                        for field in ("key", "hostname", "path", "source")
                        if isinstance(item, dict) and field in item and item[field] is not None
                    }
                    for item in value[:1000]
                    if isinstance(item, dict)
                ]
            elif isinstance(value, (str, int, float, bool)):
                sanitized[key] = str(value)[:2048]
        return sanitized

    def get_public_status(self):
        with self._lock:
            self._expire_test_jobs_locked()
            urls = list(self._config["urls"])
            return {
                "enabled": self._config["enabled"],
                "available": self._available,
                "configured_destination_count": len(urls),
                "valid_destination_count": max(0, len(urls) - self._invalid_destination_count),
                "destinations": [
                    {"index": index, "scheme": self._safe_scheme(url), "summary": redact_destination(url)}
                    for index, url in enumerate(urls, 1)
                ],
                "events": copy.deepcopy(self._config["events"]),
                "failure_cooldown_seconds": self._config["failure_cooldown_seconds"],
                "queue_depth": self._queue.qsize(),
                "queue_capacity": self._queue_size,
                "dropped_events": self._dropped_events,
                "last_attempt_at": self._last_attempt_at,
                "last_success_at": self._last_success_at,
                "last_failure_at": self._last_failure_at,
                "bootstrap": self._bootstrap,
            }

    def check_agent_health(self, agents_snapshot, heartbeat_timeout, now=None, decommissioning_ids=None):
        now = now or datetime.now(timezone.utc)
        decommissioning_ids = set(decommissioning_ids or [])
        for agent_id, agent in (agents_snapshot or {}).items():
            if not isinstance(agent, dict) or agent.get("status") != "enrolled" or agent_id in decommissioning_ids:
                continue
            online = False
            try:
                last_seen = datetime.fromisoformat(str(agent.get("last_seen", "")).replace("Z", "+00:00"))
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                online = (now - last_seen.astimezone(timezone.utc)).total_seconds() <= heartbeat_timeout
            except (TypeError, ValueError):
                online = False
            previous = self._agent_health.get(agent_id)
            self._agent_health[agent_id] = online
            if previous is None:
                continue
            context = {
                "agent_name": agent.get("display_name") or f"agent-{agent_id[:8]}",
                "agent_id": agent_id[:12],
            }
            if previous and not online:
                self.emit("agent.offline", agent_id, context)
            elif not previous and online:
                self.emit("agent.online", agent_id, context)

    def check_tunnel_health(self, tunnel_id, status, context=None, intentional=False):
        if not tunnel_id:
            return
        now = time.monotonic()
        with self._lock:
            intentional_until = self._intentional_tunnels.get(tunnel_id, 0)
            if intentional_until and intentional_until <= now:
                self._intentional_tunnels.pop(tunnel_id, None)
                intentional_until = 0
        intentional = intentional or intentional_until > now
        healthy = str(status or "").lower() == "running"
        state = self._tunnel_health.setdefault(tunnel_id, {"healthy": None, "unhealthy_checks": 0})
        previous = state["healthy"]
        if healthy:
            state["healthy"] = True
            state["unhealthy_checks"] = 0
            if previous is False:
                self.emit("tunnel.recovered", tunnel_id, context or {})
            return
        if intentional:
            state["healthy"] = False
            state["unhealthy_checks"] = 0
            return
        state["unhealthy_checks"] += 1
        if previous is None:
            state["healthy"] = False
            return
        if previous is True and state["unhealthy_checks"] >= 2:
            state["healthy"] = False
            self.emit("tunnel.down", tunnel_id, context or {})

    def suppress_tunnel_health(self, tunnel_id, seconds=120):
        if not tunnel_id:
            return
        with self._lock:
            self._intentional_tunnels[tunnel_id] = time.monotonic() + max(1, int(seconds))

    @staticmethod
    def _utc_now():
        return datetime.now(timezone.utc).isoformat()


def _runtime_int(name, default, minimum):
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


notification_manager = NotificationManager(
    queue_size=_runtime_int("NOTIFICATION_QUEUE_SIZE", 100, 1),
    max_body_chars=_runtime_int("NOTIFICATION_MAX_BODY_CHARS", 4000, 256),
    resource_limit=_runtime_int("NOTIFICATION_RESOURCE_LIST_LIMIT", 10, 1),
)


def configure(value):
    return notification_manager.configure(value)


def start(stop_event):
    return notification_manager.start(stop_event)


def stop(timeout_seconds=5):
    return notification_manager.stop(timeout_seconds)


def begin_bootstrap():
    return notification_manager.begin_bootstrap()


def end_bootstrap():
    return notification_manager.end_bootstrap()


def emit(event_type, resource_id, context=None, notify_type=None):
    return notification_manager.emit(event_type, resource_id, context, notify_type)


def send_test():
    return notification_manager.send_test()


def get_test_status(job_id):
    return notification_manager.get_test_status(job_id)


def get_public_status():
    return notification_manager.get_public_status()


def validate_urls(urls):
    return notification_manager.validate_urls(urls)


def check_agent_health(agents_snapshot, heartbeat_timeout, now=None, decommissioning_ids=None):
    return notification_manager.check_agent_health(agents_snapshot, heartbeat_timeout, now, decommissioning_ids)


def check_tunnel_health(tunnel_id, status, context=None, intentional=False):
    return notification_manager.check_tunnel_health(tunnel_id, status, context, intentional)


def suppress_tunnel_health(tunnel_id, seconds=120):
    return notification_manager.suppress_tunnel_health(tunnel_id, seconds)
