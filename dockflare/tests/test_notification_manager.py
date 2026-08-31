import logging
import threading
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.notification_manager import (
    DEFAULT_NOTIFICATION_CONFIG,
    NotificationManager,
    normalize_notification_config,
    public_resource_url,
    redact_destination,
    sanitize_service,
)


class FakeNotifyType:
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


class FakeAppriseAsset:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeApprise:
    instances = []
    result = True
    error = None

    def __init__(self, asset=None):
        self.asset = asset
        self.urls = []
        self.calls = []
        self.__class__.instances.append(self)

    def add(self, url):
        if url.startswith("invalid://"):
            return False
        self.urls.append(url)
        return True

    def notify(self, **kwargs):
        self.calls.append(kwargs)
        if self.__class__.error:
            raise self.__class__.error
        return self.__class__.result

    def __len__(self):
        return len(self.urls)


class FakeAppriseModule:
    Apprise = FakeApprise
    AppriseAsset = FakeAppriseAsset
    NotifyType = FakeNotifyType


def enabled_config(**overrides):
    value = {
        "enabled": True,
        "urls": ["json://example.test/path?token=super-secret"],
        "events": dict(DEFAULT_NOTIFICATION_CONFIG["events"]),
        "failure_cooldown_seconds": 900,
    }
    value["events"].update({key: True for key in value["events"]})
    value.update(overrides)
    return value


class NotificationConfigurationTests(unittest.TestCase):
    def setUp(self):
        FakeApprise.instances.clear()
        FakeApprise.result = True
        FakeApprise.error = None

    def test_defaults_are_disabled_and_failure_events_default_on(self):
        config = normalize_notification_config(None)
        self.assertFalse(config["enabled"])
        self.assertTrue(config["events"]["cloudflare_dns_failure"])
        self.assertFalse(config["events"]["rule_activated"])
        self.assertEqual(config["failure_cooldown_seconds"], 900)

    def test_urls_are_trimmed_deduplicated_and_limited(self):
        urls = [" json://one.test ", "json://one.test"] + [f"json://{index}.test" for index in range(40)]
        config = normalize_notification_config({"urls": urls})
        self.assertEqual(config["urls"][0], "json://one.test")
        self.assertEqual(len(config["urls"]), 32)

    def test_invalid_cooldown_uses_default(self):
        self.assertEqual(normalize_notification_config({"failure_cooldown_seconds": 59})["failure_cooldown_seconds"], 900)
        self.assertEqual(normalize_notification_config({"failure_cooldown_seconds": True})["failure_cooldown_seconds"], 900)

    def test_destination_and_service_redaction_remove_secrets(self):
        secret_url = "discord://user:password@example.test/webhook-token?token=query-secret#fragment"
        self.assertEqual(redact_destination(secret_url), "discord://configured destination")
        sanitized = sanitize_service("https://user:password@example.test:8443/path?token=query-secret#fragment")
        self.assertEqual(sanitized, "https://example.test:8443/path")
        self.assertNotIn("password", sanitized)
        self.assertNotIn("query-secret", sanitized)

    def test_public_resource_url_is_clickable_and_rejects_unsafe_hosts(self):
        self.assertEqual(
            public_resource_url("uat-agent-a.dockflare.app", "/status"),
            "https://uat-agent-a.dockflare.app/status",
        )
        self.assertIsNone(public_resource_url("*.dockflare.app", None))
        self.assertIsNone(public_resource_url("user@example.com", None))

    def test_validation_reports_only_line_and_scheme(self):
        manager = NotificationManager()
        with patch.object(manager, "_load_apprise", return_value=FakeAppriseModule):
            valid, invalid = manager.validate_urls(["invalid://do-not-echo-secret"])
        self.assertFalse(valid)
        self.assertEqual(invalid, [(1, "invalid")])


class NotificationManagerTests(unittest.TestCase):
    def setUp(self):
        FakeApprise.instances.clear()
        FakeApprise.result = True
        FakeApprise.error = None
        self.manager = NotificationManager(queue_size=4, max_body_chars=512, resource_limit=2)
        self.apprise_patch = patch.object(self.manager, "_load_apprise", return_value=FakeAppriseModule)
        self.apprise_patch.start()
        self.manager.configure(enabled_config())
        self.manager.end_bootstrap()

    def tearDown(self):
        self.manager.stop(0.1)
        self.apprise_patch.stop()

    def test_configure_exposes_redacted_status_only(self):
        status = self.manager.get_public_status()
        serialized = str(status)
        self.assertTrue(status["available"])
        self.assertEqual(status["configured_destination_count"], 1)
        self.assertNotIn("super-secret", serialized)
        self.assertEqual(status["destinations"][0]["summary"], "json://configured destination")

    def test_worker_delivers_mapped_type_and_truncated_resource_list(self):
        stop_event = threading.Event()
        self.manager.start(stop_event)
        accepted = self.manager.emit(
            "rule.activated",
            "container-a",
            {
                "resources": [
                    {"hostname": "one.example.test"},
                    {"hostname": "two.example.test"},
                    {"hostname": "three.example.test"},
                ]
            },
        )
        self.assertTrue(accepted)
        self.manager._queue.join()
        call = FakeApprise.instances[-1].calls[-1]
        self.assertEqual(call["notify_type"], "success")
        self.assertIn("https://one.example.test", call["body"])
        self.assertIn("and 1 more", call["body"])
        self.assertNotIn("three.example.test", call["body"])
        stop_event.set()

    def test_single_rule_notification_prioritizes_service_and_groups_ids(self):
        title, body = self.manager._render({
            "event_type": "rule.activated",
            "context": {
                "source": "agent",
                "container_name": "uat-agent-a-nginx",
                "container_id": "container-short",
                "agent_id": "agent-short",
                "tunnel_name": "tunnel1",
                "tunnel_id": "tunnel-short",
                "resources": [{"hostname": "uat-agent-a.dockflare.app"}],
                "public_url": "https://unstable.dockflare.app/",
            },
        })
        self.assertEqual(title, "✅ DockFlare — Rule activated")
        self.assertTrue(body.startswith("Service: https://uat-agent-a.dockflare.app\nSource: Agent"))
        self.assertIn("\n\nTechnical details\nContainer ID: container-short", body)
        self.assertTrue(body.endswith("Dashboard: https://unstable.dockflare.app/"))

    def test_health_and_failure_events_have_actionable_status(self):
        title, body = self.manager._render({
            "event_type": "agent.offline",
            "context": {"agent_name": "Edge A", "agent_id": "agent-a"},
        })
        self.assertEqual(title, "🔴 DockFlare — Agent offline")
        self.assertIn("Status: Offline", body)
        self.assertIn("Agent: Edge A", body)

        title, body = self.manager._render({
            "event_type": "cloudflare.dns_failure",
            "context": {"hostname": "app.example.com", "operation": "create", "source": "docker"},
        })
        self.assertEqual(title, "❌ DockFlare — DNS operation failed")
        self.assertTrue(body.startswith("Service: https://app.example.com\nOperation: create\nSource: Docker"))

    def test_bootstrap_suppresses_routine_events_but_allows_failures(self):
        self.manager.begin_bootstrap()
        self.assertFalse(self.manager.emit("rule.activated", "rule-a", {}))
        self.assertTrue(self.manager.emit("cloudflare.dns_failure", "rule-a", {"hostname": "a.example.test"}))

    def test_disabled_and_event_preferences_suppress_before_queueing(self):
        self.manager.configure(enabled_config(enabled=False))
        self.assertFalse(self.manager.emit("cloudflare.dns_failure", "dns-a", {}))
        self.manager.configure(enabled_config(events={key: False for key in DEFAULT_NOTIFICATION_CONFIG["events"]}))
        self.assertFalse(self.manager.emit("cloudflare.dns_failure", "dns-a", {}))
        self.assertEqual(self.manager.get_public_status()["queue_depth"], 0)

    def test_failure_cooldown_and_correlated_recovery(self):
        self.assertTrue(self.manager.emit("agent.offline", "agent-a", {}))
        self.assertFalse(self.manager.emit("agent.offline", "agent-a", {}))
        self.assertTrue(self.manager.emit("agent.online", "agent-a", {}))
        self.assertFalse(self.manager.emit("agent.online", "agent-a", {}))
        self.assertTrue(self.manager.emit("agent.offline", "agent-a", {}))

    def test_queue_full_drops_without_blocking(self):
        for index in range(4):
            self.assertTrue(self.manager.emit("rule.activated", f"rule-{index}", {}))
        self.assertFalse(self.manager.emit("rule.activated", "rule-overflow", {}))
        self.assertEqual(self.manager.get_public_status()["dropped_events"], 1)

    def test_test_job_bypasses_event_preferences(self):
        self.manager.configure(enabled_config(events={key: False for key in DEFAULT_NOTIFICATION_CONFIG["events"]}))
        job_id, accepted = self.manager.send_test()
        self.assertTrue(accepted)
        self.assertEqual(self.manager.get_test_status(job_id)["status"], "pending")

    def test_delivery_exception_does_not_log_secret_exception_text(self):
        FakeApprise.error = RuntimeError("super-secret upstream response")
        stop_event = threading.Event()
        with self.assertLogs(level=logging.ERROR) as captured:
            self.manager.start(stop_event)
            self.assertTrue(self.manager.emit("cloudflare.dns_failure", "dns-a", {}))
            self.manager._queue.join()
        output = "\n".join(captured.output)
        self.assertIn("RuntimeError", output)
        self.assertNotIn("super-secret upstream response", output)
        stop_event.set()

    def test_worker_continues_after_delivery_exception(self):
        stop_event = threading.Event()
        self.manager.start(stop_event)
        FakeApprise.error = RuntimeError("first delivery fails")
        self.assertTrue(self.manager.emit("cloudflare.dns_failure", "dns-a", {}))
        self.manager._queue.join()
        FakeApprise.error = None
        self.assertTrue(self.manager.emit("cloudflare.dns_failure", "dns-b", {}))
        self.manager._queue.join()
        self.assertEqual(len(FakeApprise.instances[-1].calls), 2)
        self.assertIsNotNone(self.manager.get_public_status()["last_success_at"])
        stop_event.set()

    def test_agent_health_establishes_baseline_then_emits_outage_and_recovery(self):
        events = []
        self.manager.emit = lambda event_type, resource_id, context=None, notify_type=None: events.append((event_type, resource_id)) or True
        now = datetime.now(timezone.utc)
        online = {"agent-a": {"status": "enrolled", "display_name": "A", "last_seen": now.isoformat()}}
        offline = {"agent-a": {"status": "enrolled", "display_name": "A", "last_seen": (now - timedelta(minutes=5)).isoformat()}}
        self.manager.check_agent_health(online, 60, now=now)
        self.manager.check_agent_health(offline, 60, now=now)
        self.manager.check_agent_health(online, 60, now=now)
        self.assertEqual(events, [("agent.offline", "agent-a"), ("agent.online", "agent-a")])

    def test_tunnel_health_requires_two_failed_checks(self):
        events = []
        self.manager.emit = lambda event_type, resource_id, context=None, notify_type=None: events.append((event_type, resource_id)) or True
        self.manager.check_tunnel_health("tunnel-a", "running")
        self.manager.check_tunnel_health("tunnel-a", "exited")
        self.assertEqual(events, [])
        self.manager.check_tunnel_health("tunnel-a", "exited")
        self.manager.check_tunnel_health("tunnel-a", "running")
        self.assertEqual(events, [("tunnel.down", "tunnel-a"), ("tunnel.recovered", "tunnel-a")])

    def test_intentional_tunnel_stop_and_agent_decommission_are_suppressed(self):
        events = []
        self.manager.emit = lambda event_type, resource_id, context=None, notify_type=None: events.append((event_type, resource_id)) or True
        self.manager.check_tunnel_health("tunnel-a", "running")
        self.manager.suppress_tunnel_health("tunnel-a", 60)
        self.manager.check_tunnel_health("tunnel-a", "exited")
        self.manager.check_tunnel_health("tunnel-a", "exited")

        now = datetime.now(timezone.utc)
        online = {"agent-a": {"status": "enrolled", "last_seen": now.isoformat()}}
        offline = {"agent-a": {"status": "enrolled", "last_seen": (now - timedelta(minutes=5)).isoformat()}}
        self.manager.check_agent_health(online, 60, now=now)
        self.manager.check_agent_health(offline, 60, now=now, decommissioning_ids={"agent-a"})
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()
