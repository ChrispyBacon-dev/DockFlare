import copy
import unittest
from unittest.mock import patch

from app import app
from app.core.state_manager import agents, managed_rules, state_lock
from app.web import api_v2_routes


class AgentProtocolTests(unittest.TestCase):
    def setUp(self):
        with state_lock:
            self.agents_snapshot = copy.deepcopy(agents)
            self.rules_snapshot = copy.deepcopy(managed_rules)
            agents.clear()
            managed_rules.clear()

    def tearDown(self):
        with state_lock:
            agents.clear()
            agents.update(self.agents_snapshot)
            managed_rules.clear()
            managed_rules.update(self.rules_snapshot)

    def test_master_creates_identity_and_v2_session(self):
        request_data = {
            "agent_id": "caller-selected",
            "supported_protocol_versions": [1, 2],
            "agent_version": "1.1.0",
        }
        with app.test_request_context("/api/v2/agents/register", method="POST", json=request_data), \
             patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "get_agent_key_info", return_value={"status": "active"}), \
             patch.object(api_v2_routes, "save_state", return_value=True), \
             patch.object(api_v2_routes, "add_agent_key"):
            response, status = api_v2_routes._register_agent_request()
        body = response.get_json()
        self.assertEqual(status, 201)
        self.assertEqual(body["code"], "registered")
        self.assertEqual(body["protocol_version"], 2)
        self.assertNotEqual(body["agent_id"], "caller-selected")
        self.assertTrue(body["agent_session_id"])

    def test_v2_sequence_duplicate_and_stale_are_deterministic(self):
        with state_lock:
            agents["agent-a"] = {
                "id": "agent-a",
                "protocol_version": 2,
                "agent_session_id": "session",
                "last_event_sequence": 4,
                "last_report_sequence": 0,
            }
        base = {
            "type": "heartbeat",
            "protocol_version": 2,
            "agent_session_id": "session",
        }
        with patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "_ensure_agent_api_key", return_value=True):
            with app.test_request_context("/events", method="POST", json={**base, "event_sequence": 4}):
                response, status = api_v2_routes._handle_agent_event_request("agent-a")
                self.assertEqual((status, response.get_json()["code"]), (200, "duplicate_sequence"))
            with app.test_request_context("/events", method="POST", json={**base, "event_sequence": 3}):
                response, status = api_v2_routes._handle_agent_event_request("agent-a")
                self.assertEqual((status, response.get_json()["code"]), (409, "stale_sequence"))

    def test_complete_empty_report_marks_only_own_rules_pending(self):
        with state_lock:
            agents["agent-a"] = {
                "id": "agent-a", "protocol_version": 2, "agent_session_id": "session",
                "last_report_sequence": 0, "last_event_sequence": 0,
            }
            managed_rules["a.example.com|"] = {
                "source": "agent", "agent_id": "agent-a", "status": "active",
                "container_id": "a", "source_rule_key": "a.example.com|",
            }
            managed_rules["b.example.com|"] = {
                "source": "agent", "agent_id": "agent-b", "status": "active",
                "container_id": "b", "source_rule_key": "b.example.com|",
            }
        payload = {
            "type": "status_report", "protocol_version": 2,
            "agent_session_id": "session", "report_sequence": 1,
            "inventory_complete": True, "inventory_scope": "dockflare_enabled_running",
            "containers": [],
        }
        with app.test_request_context("/events", method="POST", json=payload), \
             patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "_ensure_agent_api_key", return_value=True), \
             patch.object(api_v2_routes, "save_state", return_value=True), \
             patch.object(api_v2_routes, "publish_state_event"):
            response, status = api_v2_routes._handle_agent_event_request("agent-a")
        self.assertEqual((status, response.get_json()["code"]), (200, "accepted"))
        self.assertEqual(managed_rules["a.example.com|"]["status"], "pending_deletion")
        self.assertEqual(managed_rules["b.example.com|"]["status"], "active")

    def test_label_filter_drops_unrelated_namespaces(self):
        result = api_v2_routes.filter_reportable_labels({
            "dockflare.enable": "true",
            "cloudflare.tunnel.hostname": "legacy.example.com",
            "compose.project": "private",
            "secret": "DO_NOT_STORE",
        })
        self.assertEqual(set(result), {"dockflare.enable", "cloudflare.tunnel.hostname"})

    def test_report_plans_are_coalesced_per_agent_tunnel(self):
        plans = api_v2_routes._coalesce_agent_start_plans([
            {
                "agent_id": "agent-a", "tunnel_id": "tunnel-a", "state_changed": True,
                "needs_tunnel_config_update": True, "policy_jobs": [("one", {})],
                "dns_targets": {"one.example.com": {"zone_id": "zone"}},
            },
            {
                "agent_id": "agent-a", "tunnel_id": "tunnel-a", "state_changed": False,
                "needs_tunnel_config_update": True, "policy_jobs": [("two", {})],
                "dns_targets": {"two.example.com": {"zone_id": "zone"}},
            },
        ])
        self.assertEqual(len(plans), 1)
        self.assertEqual(len(plans[0]["policy_jobs"]), 2)
        self.assertEqual(set(plans[0]["dns_targets"]), {"one.example.com", "two.example.com"})

    def test_malformed_entry_consumes_report_as_incomplete_without_negative_reconciliation(self):
        with state_lock:
            agents["agent-a"] = {
                "id": "agent-a", "protocol_version": 2, "agent_session_id": "session",
                "last_report_sequence": 0, "last_event_sequence": 0,
            }
            managed_rules["kept.example.com|"] = {
                "source": "agent", "agent_id": "agent-a", "status": "active",
                "container_id": "kept", "source_rule_key": "kept.example.com|",
            }
        payload = {
            "type": "status_report", "protocol_version": 2,
            "agent_session_id": "session", "report_sequence": 1,
            "inventory_complete": True, "inventory_scope": "dockflare_enabled_running",
            "containers": [{"name": "missing-id", "labels": {}}],
        }
        with app.test_request_context("/events", method="POST", json=payload), \
             patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "_ensure_agent_api_key", return_value=True), \
             patch.object(api_v2_routes, "save_state", return_value=True), \
             patch.object(api_v2_routes, "publish_state_event"):
            response, status = api_v2_routes._handle_agent_event_request("agent-a")
        self.assertEqual((status, response.get_json()["code"]), (202, "inventory_incomplete"))
        self.assertEqual(agents["agent-a"]["last_report_sequence"], 1)
        self.assertEqual(managed_rules["kept.example.com|"]["status"], "active")

    def test_degraded_report_without_containers_is_valid_and_never_negative(self):
        with state_lock:
            agents["agent-a"] = {
                "id": "agent-a", "protocol_version": 2, "agent_session_id": "session",
                "last_report_sequence": 0, "last_event_sequence": 0,
            }
        payload = {
            "type": "status_report", "protocol_version": 2,
            "agent_session_id": "session", "report_sequence": 1,
            "inventory_complete": False, "inventory_scope": "dockflare_enabled_running",
        }
        with app.test_request_context("/events", method="POST", json=payload), \
             patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "_ensure_agent_api_key", return_value=True), \
             patch.object(api_v2_routes, "save_state", return_value=True), \
             patch.object(api_v2_routes, "publish_state_event"):
            response, status = api_v2_routes._handle_agent_event_request("agent-a")
        self.assertEqual((status, response.get_json()["code"]), (202, "inventory_incomplete"))

    def test_bound_key_cannot_rebind_to_different_cached_identity(self):
        with state_lock:
            agents["agent-a"] = {"id": "agent-a"}
        with app.test_request_context("/register", method="POST", json={
            "agent_id": "agent-b", "supported_protocol_versions": [2, 1],
        }), patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", "agent-a")), \
             patch.object(api_v2_routes, "get_agent_key_info", return_value={"status": "active", "bound_agent_id": "agent-a"}):
            response, status = api_v2_routes._register_agent_request()
        self.assertEqual((status, response.get_json()["code"]), (403, "agent_key_mismatch"))

    def test_persistence_failure_rolls_back_event_and_sequence(self):
        with state_lock:
            agents["agent-a"] = {
                "id": "agent-a", "protocol_version": 2, "agent_session_id": "session",
                "last_report_sequence": 0, "last_event_sequence": 0,
            }
            managed_rules["app.example.com|"] = {
                "source": "agent", "agent_id": "agent-a", "status": "active",
                "container_id": "container-a", "source_rule_key": "app.example.com|",
            }
        payload = {
            "type": "container_stop", "protocol_version": 2,
            "agent_session_id": "session", "event_sequence": 1,
            "container": {"id": "container-a", "name": "app", "labels": {}},
        }
        with app.test_request_context("/events", method="POST", json=payload), \
             patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "_ensure_agent_api_key", return_value=True), \
             patch.object(api_v2_routes, "save_state", return_value=False), \
             patch.object(api_v2_routes, "publish_state_event") as publish:
            response, status = api_v2_routes._handle_agent_event_request("agent-a")
        self.assertEqual((status, response.get_json()["code"]), (503, "persistence_failed"))
        self.assertEqual(managed_rules["app.example.com|"]["status"], "active")
        self.assertEqual(agents["agent-a"]["last_event_sequence"], 0)
        publish.assert_not_called()

    def test_persistence_failure_rolls_back_complete_inventory(self):
        previous_inventory = [{"id": "container-a", "name": "app", "labels": {}}]
        with state_lock:
            agents["agent-a"] = {
                "id": "agent-a", "protocol_version": 2, "agent_session_id": "session",
                "last_report_sequence": 0, "last_event_sequence": 0,
                "last_complete_containers": copy.deepcopy(previous_inventory),
            }
            managed_rules["app.example.com|"] = {
                "source": "agent", "agent_id": "agent-a", "status": "active",
                "container_id": "container-a", "source_rule_key": "app.example.com|",
            }
        payload = {
            "type": "status_report", "protocol_version": 2,
            "agent_session_id": "session", "report_sequence": 1,
            "inventory_complete": True, "inventory_scope": "dockflare_enabled_running",
            "containers": [],
        }
        with app.test_request_context("/events", method="POST", json=payload), \
             patch.object(api_v2_routes, "_authenticate_agent_request", return_value=("key", None)), \
             patch.object(api_v2_routes, "_ensure_agent_api_key", return_value=True), \
             patch.object(api_v2_routes, "save_state", return_value=False), \
             patch.object(api_v2_routes, "publish_state_event") as publish:
            response, status = api_v2_routes._handle_agent_event_request("agent-a")

        self.assertEqual((status, response.get_json()["code"]), (503, "persistence_failed"))
        self.assertEqual(managed_rules["app.example.com|"]["status"], "active")
        self.assertEqual(agents["agent-a"]["last_report_sequence"], 0)
        self.assertEqual(agents["agent-a"]["last_complete_containers"], previous_inventory)
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
