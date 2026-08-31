import copy
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core import docker_handler, reconciler
from app.core.state_manager import managed_rules, state_lock


class _Container:
    id = "notification-container"
    name = "notification-app"
    labels = {
        "dockflare.enable": "true",
        "dockflare.hostname": "notify.example.com",
        "dockflare.service": "http://notification-app:8080",
    }

    def reload(self):
        return None


class NotificationEventBoundaryTests(unittest.TestCase):
    def setUp(self):
        with state_lock:
            self.rules_snapshot = copy.deepcopy(managed_rules)
            managed_rules.clear()

    def tearDown(self):
        with state_lock:
            managed_rules.clear()
            managed_rules.update(self.rules_snapshot)

    @staticmethod
    def _inventory():
        return {
            "zones": [{"id": "zone-1", "name": "example.com"}],
            "status": "complete",
            "error": None,
        }

    def _process_start(self, tunnel_success=True):
        emitted = []

        def capture(event_type, resource_id, context=None, notify_type=None):
            if hasattr(state_lock, "_is_owned"):
                self.assertFalse(state_lock._is_owned())
            emitted.append((event_type, resource_id, context or {}))
            return True

        with patch.object(docker_handler, "get_account_zone_inventory", return_value=self._inventory()), \
             patch.object(docker_handler, "save_state", return_value=True), \
             patch.object(docker_handler, "publish_state_event"), \
             patch.object(docker_handler, "handle_access_policy_from_labels", return_value=False), \
             patch.object(docker_handler, "update_cloudflare_config", return_value=tunnel_success), \
             patch.object(docker_handler, "create_cloudflare_dns_record", return_value="dns-id"), \
             patch.object(docker_handler.notification_manager, "emit", side_effect=capture), \
             patch.dict(docker_handler.tunnel_state, {"id": "master-tunnel", "name": "Master"}, clear=False):
            docker_handler.process_container_start(_Container())
        return emitted

    def test_new_rule_emits_activation_only_after_remote_success(self):
        emitted = self._process_start(tunnel_success=True)
        self.assertEqual([event[0] for event in emitted].count("rule.activated"), 1)
        self.assertNotIn("cloudflare.tunnel_failure", [event[0] for event in emitted])

    def test_tunnel_failure_emits_failure_and_not_activation(self):
        emitted = self._process_start(tunnel_success=False)
        event_types = [event[0] for event in emitted]
        self.assertIn("cloudflare.tunnel_failure", event_types)
        self.assertNotIn("rule.activated", event_types)

    def test_cleanup_notifies_only_committed_rules(self):
        now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
        with state_lock:
            for name, tunnel_id in (("deleted", "tunnel-ok"), ("retained", "tunnel-failed")):
                managed_rules[f"{name}.example.com|"] = {
                    "hostname": f"{name}.example.com",
                    "zone_id": "zone-1",
                    "status": "pending_deletion",
                    "delete_at": now - timedelta(seconds=1),
                    "source": "docker",
                    "container_id": name,
                    "tunnel_id": tunnel_id,
                    "lifecycle_generation": 1,
                }
        emitted = []
        with patch.object(
            reconciler, "update_cloudflare_config",
            side_effect=lambda tunnel_id: tunnel_id == "tunnel-ok",
        ), patch.object(reconciler, "delete_cloudflare_dns_record", return_value=True), \
             patch.object(reconciler, "save_state", return_value=True), \
             patch.object(reconciler, "publish_state_event"), \
             patch.object(
                 reconciler.notification_manager, "emit",
                 side_effect=lambda event_type, resource_id, context=None, notify_type=None:
                 emitted.append((event_type, context or {})),
             ):
            committed = reconciler.cleanup_expired_rules_once(now)

        self.assertEqual(committed, 1)
        deleted_event = next(context for event_type, context in emitted if event_type == "rule.deleted")
        self.assertEqual(
            [resource["hostname"] for resource in deleted_event["resources"]],
            ["deleted.example.com"],
        )
        self.assertIn("cloudflare.tunnel_failure", [event_type for event_type, _ in emitted])
        self.assertIn("retained.example.com|", managed_rules)


if __name__ == "__main__":
    unittest.main()
