import threading
import json
import pathlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core import tunnel_manager
from app.core import docker_handler
from app.core import reconciler
from app.core import cloudflare_api
from app.core.state_manager import (
    agent_inventory_contains_rule,
    find_container_rule,
    managed_rules,
    restore_rule_lifecycle,
    state_lock,
)
from app.core import state_manager
from app.core.utils import get_source_rule_key
from app import app as flask_app
from app.web import routes as web_routes


class RuleLifecycleTests(unittest.TestCase):
    def setUp(self):
        with state_lock:
            self.snapshot = dict(managed_rules)
            managed_rules.clear()

    def tearDown(self):
        with state_lock:
            managed_rules.clear()
            managed_rules.update(self.snapshot)

    def test_restore_reactivates_without_changing_configuration(self):
        deadline = datetime.now(timezone.utc) + timedelta(minutes=5)
        rule = {
            "container_id": "old",
            "status": "pending_deletion",
            "delete_at": deadline,
            "service": "https://ui-owned:443",
            "rule_ui_override": True,
            "lifecycle_generation": 4,
        }
        changed, reactivated = restore_rule_lifecycle(rule, "replacement")
        self.assertTrue(changed)
        self.assertTrue(reactivated)
        self.assertEqual(rule["container_id"], "replacement")
        self.assertEqual(rule["status"], "active")
        self.assertIsNone(rule["delete_at"])
        self.assertEqual(rule["service"], "https://ui-owned:443")
        self.assertEqual(rule["lifecycle_generation"], 5)

    def test_container_refresh_is_not_reactivation_and_is_idempotent(self):
        rule = {"container_id": "old", "status": "active", "delete_at": None}
        self.assertEqual(restore_rule_lifecycle(rule, "new"), (True, False))
        self.assertEqual(restore_rule_lifecycle(rule, "new"), (False, False))

    def test_ingress_eligibility_honors_grace_deadline(self):
        now = datetime(2026, 8, 21, tzinfo=timezone.utc)
        self.assertTrue(tunnel_manager.is_rule_ingress_eligible({"status": "active"}, now))
        self.assertTrue(tunnel_manager.is_rule_ingress_eligible({
            "status": "pending_deletion", "delete_at": now + timedelta(seconds=1)
        }, now))
        self.assertFalse(tunnel_manager.is_rule_ingress_eligible({
            "status": "pending_deletion", "delete_at": now
        }, now))
        self.assertFalse(tunnel_manager.is_rule_ingress_eligible({
            "status": "pending_deletion", "delete_at": "invalid"
        }, now))

    def test_source_key_is_canonical_and_preserves_wildcard(self):
        self.assertEqual(
            get_source_rule_key("EXAMPLE.COM.", "  /api  "),
            get_source_rule_key("example.com", "/api"),
        )
        self.assertNotEqual(
            get_source_rule_key("*.example.com", None),
            get_source_rule_key("example.com", None),
        )

    def test_lookup_uses_unique_source_identity_and_agent_owner(self):
        with state_lock:
            managed_rules["edited.example.com|"] = {
                "source": "agent",
                "agent_id": "agent-a",
                "source_rule_key": "source.example.com|",
            }
            key, rule = find_container_rule("source.example.com|", "agent", "agent-a")
            self.assertEqual(key, "edited.example.com|")
            self.assertIsNotNone(rule)
            self.assertEqual(find_container_rule("source.example.com|", "agent", "agent-b"), (None, None))

    def test_ambiguous_source_identity_fails_closed(self):
        with state_lock:
            for key in ("first.example.com|", "second.example.com|"):
                managed_rules[key] = {
                    "source": "docker",
                    "source_rule_key": "source.example.com|",
                }
            with self.assertRaisesRegex(ValueError, "Ambiguous container rule identity"):
                find_container_rule("source.example.com|", "docker")

    def test_agent_inventory_must_contain_current_rule_binding(self):
        rule = {
            "container_id": "replacement",
            "source_rule_key": "app.example.com|/api",
        }
        current = [{
            "id": "replacement",
            "labels": {
                "dockflare.0.hostname": "app.example.com",
                "dockflare.0.path": "/api",
            },
        }]
        stale = [{
            "id": "previous",
            "labels": {
                "dockflare.0.hostname": "app.example.com",
                "dockflare.0.path": "/api",
            },
        }]

        self.assertTrue(agent_inventory_contains_rule(current, rule))
        self.assertFalse(agent_inventory_contains_rule(stale, rule))
        self.assertFalse(agent_inventory_contains_rule(None, rule))
        self.assertFalse(agent_inventory_contains_rule([{
            "id": "replacement",
            "labels": {"dockflare.hostname": "invalid hostname"},
        }], rule))

    def test_agent_revert_does_not_require_local_docker_socket(self):
        with state_lock:
            managed_rules["app.example.com|"] = {
                "source": "agent",
                "agent_id": "agent-a",
                "rule_ui_override": True,
                "lifecycle_generation": 2,
            }

        with flask_app.test_request_context(
            "/ui/docker-rules/revert",
            method="POST",
            data={"rule_key": "app.example.com|"},
        ), patch.object(web_routes, "docker_client", None), patch.object(
            web_routes, "save_state", return_value=True
        ), patch.object(web_routes, "get_agent", return_value=None):
            response = web_routes.ui_revert_docker_rule_route()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(managed_rules["app.example.com|"]["rule_ui_override"])
        self.assertIn("Waiting for the next Agent report", web_routes.cloudflared_agent_state["last_action_status"])

    def test_docker_revert_still_requires_local_docker_socket(self):
        with state_lock:
            managed_rules["app.example.com|"] = {
                "source": "docker",
                "rule_ui_override": True,
                "lifecycle_generation": 2,
            }

        with flask_app.test_request_context(
            "/ui/docker-rules/revert",
            method="POST",
            data={"rule_key": "app.example.com|"},
        ), patch.object(web_routes, "docker_client", None):
            response = web_routes.ui_revert_docker_rule_route()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(managed_rules["app.example.com|"]["rule_ui_override"])
        self.assertEqual(web_routes.cloudflared_agent_state["last_action_status"], "Error: Docker client unavailable.")

    def test_tunnel_lock_registry_is_stable_per_tunnel(self):
        first = tunnel_manager.get_tunnel_operation_lock(" tunnel-a ")
        second = tunnel_manager.get_tunnel_operation_lock("tunnel-a")
        other = tunnel_manager.get_tunnel_operation_lock("tunnel-b")
        self.assertIs(first, second)
        self.assertIsNot(first, other)
        self.assertIsInstance(first, type(threading.RLock()))

    def test_schema_v2_lifecycle_fields_round_trip(self):
        deadline = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            state_path = pathlib.Path(directory) / "state.json"
            with state_lock:
                managed_rules["app.example.com|"] = {
                    "hostname": "app.example.com",
                    "source": "docker",
                    "status": "active",
                    "source_rule_key": "app.example.com|",
                    "tunnel_sync_pending": True,
                    "tunnel_sync_last_attempt_at": deadline,
                    "tunnel_sync_attempts": 2,
                    "lifecycle_generation": 7,
                    "extension": {"preserved": True},
                }
            with patch.object(state_manager.config, "STATE_FILE_PATH", str(state_path)):
                self.assertTrue(state_manager.save_state())
                persisted = json.loads(state_path.read_text())
                self.assertEqual(persisted["state_schema_version"], 2)
                self.assertEqual(persisted["managed_rules"]["app.example.com|"]["extension"], {"preserved": True})
                with state_lock:
                    managed_rules.clear()
                state_manager.load_state()
            restored = managed_rules["app.example.com|"]
            self.assertEqual(restored["source_rule_key"], "app.example.com|")
            self.assertTrue(restored["tunnel_sync_pending"])
            self.assertEqual(restored["tunnel_sync_last_attempt_at"], deadline)
            self.assertEqual(restored["lifecycle_generation"], 7)

    def test_future_schema_is_not_rewritten_or_downgraded(self):
        raw = b'{"state_schema_version":999,"managed_rules":{"future":{"extension":true}}}\n'
        with tempfile.TemporaryDirectory() as directory:
            state_path = pathlib.Path(directory) / "state.json"
            state_path.write_bytes(raw)
            try:
                with patch.object(state_manager.config, "STATE_FILE_PATH", str(state_path)):
                    state_manager.load_state()
                    self.assertEqual(state_path.read_bytes(), raw)
                    self.assertFalse(state_manager.save_state())
                    self.assertEqual(state_path.read_bytes(), raw)
            finally:
                state_manager._state_write_blocked_reason = None

    def test_local_override_reactivation_does_not_resolve_zone_or_apply_labels(self):
        class Container:
            id = "replacement-container"
            name = "app"
            labels = {
                "dockflare.enable": "true",
                "dockflare.hostname": "app.example.com",
                "dockflare.service": "http://label-owned:8080",
            }

            def reload(self):
                return None

        with state_lock:
            managed_rules["app.example.com|"] = {
                "hostname": "app.example.com",
                "path": None,
                "service": "https://ui-owned:443",
                "container_id": "old-container",
                "status": "pending_deletion",
                "delete_at": datetime.now(timezone.utc) + timedelta(minutes=5),
                "zone_id": "zone-1",
                "source": "docker",
                "rule_ui_override": True,
                "tunnel_id": "master-tunnel",
            }
        with patch.object(docker_handler, "get_account_zone_inventory", side_effect=AssertionError("zone lookup must not run")), \
             patch.object(docker_handler, "save_state", return_value=True), \
             patch.object(docker_handler, "publish_state_event"), \
             patch.object(docker_handler, "update_cloudflare_config", return_value=True), \
             patch.object(docker_handler, "create_cloudflare_dns_record", return_value="dns-id"), \
             patch.dict(docker_handler.tunnel_state, {"id": "master-tunnel", "name": "Master"}, clear=False):
            docker_handler.process_container_start(Container())
        rule = managed_rules["app.example.com|"]
        self.assertEqual(rule["status"], "active")
        self.assertIsNone(rule["delete_at"])
        self.assertEqual(rule["container_id"], "replacement-container")
        self.assertEqual(rule["service"], "https://ui-owned:443")

    def test_local_container_id_refresh_does_not_rewrite_tunnel_configuration(self):
        class Container:
            id = "replacement-container"
            name = "app"
            labels = {
                "dockflare.enable": "true",
                "dockflare.hostname": "app.example.com",
                "dockflare.service": "http://app:8080",
            }

            def reload(self):
                return None

        with state_lock:
            managed_rules["app.example.com|"] = {
                "hostname": "app.example.com", "path": None, "service": "http://app:8080",
                "container_id": "old-container", "status": "active", "delete_at": None,
                "zone_id": "zone-1", "zone_name": "example.com", "zone_resolution_source": "hostname",
                "source": "docker", "tunnel_id": "master-tunnel", "tunnel_name": "Master",
                "source_rule_key": "app.example.com|", "no_tls_verify": False,
                "http2_origin": False, "disable_chunked_encoding": False, "match_sni_to_host": False,
            }
        inventory = {"zones": [{"id": "zone-1", "name": "example.com"}], "status": "complete", "error": None}
        with patch.object(docker_handler, "get_account_zone_inventory", return_value=inventory), \
             patch.object(docker_handler, "save_state", return_value=True), \
             patch.object(docker_handler, "publish_state_event"), \
             patch.object(docker_handler, "handle_access_policy_from_labels", return_value=False), \
             patch.object(docker_handler, "update_cloudflare_config") as update_tunnel, \
             patch.dict(docker_handler.tunnel_state, {"id": "master-tunnel", "name": "Master"}, clear=False):
            docker_handler.process_container_start(Container())
        self.assertEqual(managed_rules["app.example.com|"]["container_id"], "replacement-container")
        update_tunnel.assert_not_called()

    def test_cleanup_isolated_by_effective_tunnel(self):
        now = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        with state_lock:
            for suffix, tunnel_id in (("a", "tunnel-a"), ("b", "tunnel-b")):
                managed_rules[f"{suffix}.example.com|"] = {
                    "hostname": f"{suffix}.example.com",
                    "zone_id": "zone",
                    "status": "pending_deletion",
                    "delete_at": now - timedelta(seconds=1),
                    "source": "agent",
                    "agent_id": f"agent-{suffix}",
                    "container_id": suffix,
                    "tunnel_id": tunnel_id,
                    "lifecycle_generation": 1,
                }
        updates = []
        with patch.object(reconciler, "update_cloudflare_config", side_effect=lambda tunnel: updates.append(tunnel) or tunnel == "tunnel-a"), \
             patch.object(reconciler, "delete_cloudflare_dns_record", return_value=True), \
             patch.object(reconciler, "delete_cloudflare_access_application", return_value=True), \
             patch.object(reconciler, "save_state", return_value=True), \
             patch.object(reconciler, "publish_state_event"):
            self.assertEqual(reconciler.cleanup_expired_rules_once(now), 1)
        self.assertEqual(updates, ["tunnel-a", "tunnel-b"])
        self.assertNotIn("a.example.com|", managed_rules)
        self.assertIn("b.example.com|", managed_rules)

    def test_pending_tunnel_retry_clears_only_after_success(self):
        now = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
        with state_lock:
            managed_rules["app.example.com|"] = {
                "source": "agent",
                "tunnel_id": "agent-tunnel",
                "tunnel_sync_pending": True,
                "tunnel_sync_attempts": 0,
                "lifecycle_generation": 1,
            }
        with patch.object(reconciler, "update_cloudflare_config", return_value=False), \
             patch.object(reconciler, "save_state", return_value=True), \
             patch.object(reconciler, "publish_state_event"):
            reconciler.retry_pending_tunnel_sync(now, force=True)
        self.assertTrue(managed_rules["app.example.com|"]["tunnel_sync_pending"])
        self.assertEqual(managed_rules["app.example.com|"]["tunnel_sync_attempts"], 1)
        with patch.object(reconciler, "update_cloudflare_config", return_value=True), \
             patch.object(reconciler, "save_state", return_value=True), \
             patch.object(reconciler, "publish_state_event"):
            reconciler.retry_pending_tunnel_sync(now + timedelta(seconds=60), force=True)
        self.assertFalse(managed_rules["app.example.com|"]["tunnel_sync_pending"])
        self.assertEqual(managed_rules["app.example.com|"]["tunnel_sync_attempts"], 0)

    def test_dns_delete_requires_expected_tunnel_target(self):
        with patch.object(cloudflare_api, "find_dns_record_id", return_value=("record-id", False)), \
             patch.object(cloudflare_api, "cf_api_request") as api_request:
            self.assertFalse(cloudflare_api.delete_cloudflare_dns_record("zone", "app.example.com", "expected-tunnel"))
        api_request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
