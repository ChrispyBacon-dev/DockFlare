import copy
import json
import unittest
from unittest.mock import patch

from app import app, tunnel_state
from app.core.state_manager import managed_rules, state_lock
from app.web import api_v2_routes


class OverviewApiTests(unittest.TestCase):
    def setUp(self):
        with state_lock:
            self.rules_snapshot = copy.deepcopy(managed_rules)
            self.tunnel_snapshot = copy.deepcopy(tunnel_state)
            managed_rules.clear()
            tunnel_state.clear()

    def tearDown(self):
        with state_lock:
            managed_rules.clear()
            managed_rules.update(self.rules_snapshot)
            tunnel_state.clear()
            tunnel_state.update(self.tunnel_snapshot)

    def test_overview_is_read_only_and_excludes_stored_secrets(self):
        tunnel_secret = "tunnel-secret-must-not-leak"
        agent_secret = "agent-secret-must-not-leak"
        session_secret = "session-secret-must-not-leak"
        status_secret = "status-secret-must-not-leak"
        key_token = "agent-key-must-not-leak"
        with state_lock:
            tunnel_state.update({
                "id": "tunnel-a", "name": "primary", "token": tunnel_secret,
            })
            managed_rules["app.example.com|"] = {
                "hostname": "app.example.com", "source": "manual",
                "status": "active", "tunnel_id": None,
            }
            expected_rules = copy.deepcopy(managed_rules)

        agent_record = {
            "id": "agent-a", "display_name": "Agent A", "status": "enrolled",
            "api_key": agent_secret, "agent_session_id": session_secret,
            "last_complete_containers": [{"labels": {"secret": "inventory-secret"}}],
            "last_action_status": status_secret,
        }
        key_metadata = {
            "owner": "Agent A", "status": "active", "created_at": "2026-01-01T00:00:00+00:00",
        }
        tunnel_inventory = [{
            "id": "tunnel-a", "name": "primary", "status": "healthy",
            "token": "cloudflare-tunnel-secret",
        }]

        with app.test_request_context("/api/v2/overview"), \
             patch.object(api_v2_routes, "list_agents", return_value={"agent-a": agent_record}), \
             patch.object(api_v2_routes, "list_agent_keys", return_value={key_token: key_metadata}), \
             patch.object(api_v2_routes, "get_all_account_cloudflare_tunnels", return_value=tunnel_inventory), \
             patch.object(api_v2_routes, "save_state") as save_state, \
             patch.object(api_v2_routes, "list_account_zones") as list_zones:
            response = api_v2_routes.get_overview_data()

        body = response.get_json()
        serialized = json.dumps(body, sort_keys=True)
        for secret in (
            tunnel_secret, agent_secret, session_secret, status_secret,
            key_token, "inventory-secret", "cloudflare-tunnel-secret",
        ):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("display_token", body)
        self.assertIn(api_v2_routes._agent_key_reference(key_token), body["agent_keys"])
        self.assertEqual(body["agents"]["agent-a"]["display_name"], "Agent A")
        self.assertEqual(body["all_account_tunnels"][0]["name"], "primary")
        with state_lock:
            self.assertEqual(managed_rules, expected_rules)
        save_state.assert_not_called()
        list_zones.assert_not_called()

    def test_public_key_reference_resolves_without_exposing_token(self):
        key_token = "private-agent-key"
        reference = api_v2_routes._agent_key_reference(key_token)
        with patch.object(api_v2_routes, "list_agent_keys", return_value={key_token: {"status": "active"}}):
            self.assertEqual(api_v2_routes._resolve_agent_key_identifier(reference), key_token)
            self.assertEqual(api_v2_routes._resolve_agent_key_identifier(key_token), key_token)

    def test_key_reference_can_be_used_for_revoke_action(self):
        key_token = "private-agent-key"
        reference = api_v2_routes._agent_key_reference(key_token)
        with app.test_request_context(
            "/api/v2/agents/revoke-key", method="POST", json={"key": reference},
        ), patch.object(
            api_v2_routes, "list_agent_keys", return_value={key_token: {"status": "active"}},
        ), patch.object(
            api_v2_routes, "revoke_agent_key", return_value=True,
        ) as revoke, patch.object(
            api_v2_routes, "list_agents", return_value={},
        ):
            response, status = api_v2_routes.agents_revoke_key()

        self.assertEqual((status, response.get_json()["status"]), (200, "success"))
        revoke.assert_called_once_with(key_token)


if __name__ == "__main__":
    unittest.main()
