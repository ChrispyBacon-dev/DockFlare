import unittest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from flask import render_template

from app import app
from app.core import agent_decommission
from app.core import state_manager
from app.core import service_token_manager
from app.web import api_v2_routes
from app.core.state_manager import agent_decommissions, agents, managed_rules, state_lock


class AgentDecommissionTests(unittest.TestCase):
    def setUp(self):
        self.previous_master_key = app.config.get("MASTER_API_KEY")
        with state_lock:
            agents.clear()
            managed_rules.clear()
            agent_decommissions.clear()
            agents["agent-a"] = {
                "id": "agent-a",
                "display_name": "Agent A",
                "assigned_tunnel_id": "tunnel-a",
                "assigned_tunnel_name": "agent-a",
                "assigned_tunnel_ownership": "adopted",
                "capabilities": ["decommission.v1", "tunnel_stop.v1", "self_stop.v1"],
            }

    def tearDown(self):
        app.config["MASTER_API_KEY"] = self.previous_master_key

    def _start(self):
        with patch.object(agent_decommission, "save_state", return_value=True):
            operation, created = agent_decommission.start_decommission("agent-a")
        self.assertTrue(created)
        return operation

    def _prepare_ack(self, operation):
        payload = {
            "operation_id": operation["operation_id"],
            "command_id": operation["prepare_command_id"],
            "phase": "prepared",
            "tombstone_persisted": True,
            "tunnel_container": "stopped",
            "self_stop_capability": "supported",
            "agent_image": "alplat/dockflare-agent:dev",
            "cloudflared_image": "cloudflare/cloudflared:latest",
        }
        with patch.object(agent_decommission, "save_state", return_value=True):
            return agent_decommission.record_ack("agent-a", operation["operation_id"], payload)

    def test_start_is_durable_idempotent_and_command_is_not_public(self):
        operation = self._start()
        with patch.object(agent_decommission, "save_state", return_value=True):
            repeated, created = agent_decommission.start_decommission("agent-a")
        self.assertFalse(created)
        self.assertEqual(repeated["operation_id"], operation["operation_id"])
        self.assertEqual(agent_decommission.command_for_agent("agent-a")["action"], "prepare_decommission")
        public = agent_decommission.serialize_operation(operation)
        self.assertNotIn("durable_command", public)
        self.assertNotIn("acknowledged_commands", public)

    def test_prepare_ack_is_idempotent_after_finalize_command_is_created(self):
        operation = self._start()
        _acknowledged, _ = self._prepare_ack(operation)
        original_payload = {
            "operation_id": operation["operation_id"],
            "command_id": operation["prepare_command_id"],
            "phase": "prepared",
        }
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "update_cloudflare_config", return_value=True):
            agent_decommission.run_master_cleanup(operation["operation_id"])
            duplicate, should_cleanup = agent_decommission.record_ack("agent-a", operation["operation_id"], original_payload)
        self.assertFalse(should_cleanup)
        self.assertEqual(duplicate["state"], "waiting_for_finalize")

    def test_unknown_and_adopted_tunnels_fail_closed(self):
        operation = self._start()
        self.assertEqual(operation["resource_plan"]["tunnel_disposition"], "preserve_adopted")
        with state_lock:
            agents["agent-a"]["assigned_tunnel_ownership"] = "unknown"
            agents["agent-a"].pop("decommission_operation_id", None)
            agent_decommissions.clear()
        operation = self._start()
        self.assertEqual(operation["resource_plan"]["tunnel_disposition"], "unknown")

    def test_shared_tunnel_is_never_planned_for_deletion(self):
        with state_lock:
            agents["agent-a"]["assigned_tunnel_ownership"] = "created_exclusive"
            agents["agent-b"] = {"assigned_tunnel_id": "tunnel-a"}
        operation = self._start()
        self.assertEqual(operation["resource_plan"]["tunnel_disposition"], "preserve_shared")

    def test_exclusive_tunnel_is_deleted_only_after_prepare(self):
        with state_lock:
            agents["agent-a"]["assigned_tunnel_ownership"] = "created_exclusive"
        operation = self._start()
        self.assertEqual(operation["resource_plan"]["tunnel_disposition"], "delete_exclusive")
        self._prepare_ack(operation)
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "delete_tunnel_via_api", return_value=True) as delete_tunnel:
            waiting = agent_decommission.run_master_cleanup(operation["operation_id"])
        delete_tunnel.assert_called_once_with("tunnel-a")
        self.assertEqual(waiting["cleanup_results"]["tunnel"], "deleted")

    def test_shared_access_application_is_preserved(self):
        with state_lock:
            managed_rules["agent.example.com|/"] = {
                "source": "agent", "agent_id": "agent-a", "tunnel_id": "tunnel-a",
                "zone_id": "zone-a", "hostname": "agent.example.com", "access_app_id": "shared-app",
            }
            managed_rules["manual.example.com|/"] = {
                "source": "manual", "tunnel_id": "master-tunnel",
                "zone_id": "zone-a", "hostname": "manual.example.com", "access_app_id": "shared-app",
            }
        operation = self._start()
        self._prepare_ack(operation)
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "delete_cloudflare_access_application") as delete_access, \
             patch.object(agent_decommission, "delete_cloudflare_dns_record", return_value=True), \
             patch.object(agent_decommission, "update_cloudflare_config", return_value=True):
            agent_decommission.run_master_cleanup(operation["operation_id"])
        delete_access.assert_not_called()

    def test_prepare_cleanup_finalize_order_and_cleanup_commands(self):
        with state_lock:
            managed_rules["app.example.com|/"] = {
                "source": "agent",
                "agent_id": "agent-a",
                "tunnel_id": "tunnel-a",
                "zone_id": "zone-a",
                "hostname": "app.example.com",
                "access_app_id": "app-a",
            }
        operation = self._start()
        acknowledged, should_cleanup = self._prepare_ack(operation)
        self.assertTrue(should_cleanup)
        self.assertEqual(acknowledged["state"], "remote_prepared")
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "delete_cloudflare_access_application", return_value=True) as delete_access, \
             patch.object(agent_decommission, "delete_cloudflare_dns_record", return_value=True) as delete_dns, \
             patch.object(agent_decommission, "delete_tunnel_via_api") as delete_tunnel, \
             patch.object(agent_decommission, "update_cloudflare_config", return_value=True):
            waiting = agent_decommission.run_master_cleanup(operation["operation_id"])
        delete_access.assert_called_once_with("app-a")
        delete_dns.assert_called_once_with("zone-a", "app.example.com", "tunnel-a")
        delete_tunnel.assert_not_called()
        self.assertEqual(waiting["state"], "waiting_for_finalize")
        self.assertNotIn("app.example.com|/", managed_rules)

        final_payload = {
            "operation_id": operation["operation_id"],
            "command_id": waiting["finalize_command_id"],
            "phase": "shutdown_scheduled",
            "self_stop_capability": "supported",
        }
        with patch.object(agent_decommission, "save_state", return_value=True):
            scheduled, should_cleanup = agent_decommission.record_ack("agent-a", operation["operation_id"], final_payload)
        self.assertFalse(should_cleanup)
        self.assertEqual(scheduled["state"], "shutdown_scheduled")
        with patch.object(agent_decommission, "list_agent_keys", return_value={"secret-token": {"bound_agent_id": "agent-a"}}), \
             patch.object(agent_decommission, "revoke_agent_key", return_value=True) as revoke, \
             patch.object(agent_decommission, "save_state", return_value=True):
            completed = agent_decommission.complete_finalization(operation["operation_id"])
        revoke.assert_called_once_with("secret-token")
        self.assertNotIn("agent-a", agents)
        public = agent_decommission.serialize_operation(completed)
        self.assertEqual(public["state"], "completed")
        self.assertNotIn("secret-token", str(public))
        self.assertIn("cloudflare-net", public["host_cleanup_plan"]["preserve_networks"])
        self.assertIn('rm -rf -- ./dockflare-agent', public["cleanup_commands"]["deployment_files"])
        self.assertNotIn("cloudflare-net", public["cleanup_commands"]["docker"])

    def test_prepare_persistence_failure_rolls_back_in_memory_state(self):
        operation = self._start()
        payload = {
            "operation_id": operation["operation_id"],
            "command_id": operation["prepare_command_id"],
            "phase": "prepared",
            "tombstone_persisted": True,
            "tunnel_container": "stopped",
            "self_stop_capability": "manual",
            "cloudflared_image": "cloudflare/cloudflared:latest",
        }
        with patch.object(agent_decommission, "save_state", return_value=False):
            with self.assertRaisesRegex(agent_decommission.DecommissionError, "persistence_failed"):
                agent_decommission.record_ack("agent-a", operation["operation_id"], payload)
        stored = agent_decommissions[operation["operation_id"]]
        self.assertEqual(stored["state"], "waiting_for_prepare")
        self.assertEqual(agents["agent-a"]["decommission_state"], "waiting_for_prepare")

    def test_wrong_command_ack_is_rejected_without_side_effects(self):
        operation = self._start()
        payload = {
            "operation_id": operation["operation_id"],
            "command_id": "wrong-command",
            "phase": "prepared",
        }
        with self.assertRaisesRegex(agent_decommission.DecommissionError, "stale_command"):
            agent_decommission.record_ack("agent-a", operation["operation_id"], payload)
        self.assertEqual(agent_decommissions[operation["operation_id"]]["state"], "waiting_for_prepare")

    def test_timeout_is_persisted_without_external_cleanup(self):
        operation = self._start()
        with state_lock:
            agent_decommissions[operation["operation_id"]]["deadline_at"] = (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            ).isoformat()
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "delete_tunnel_via_api") as delete_tunnel:
            changed = agent_decommission.expire_due_operations()
        self.assertEqual(changed, [operation["operation_id"]])
        self.assertEqual(agent_decommissions[operation["operation_id"]]["state"], "timed_out")
        delete_tunnel.assert_not_called()

    def test_cleanup_failure_retains_agent_key_rules_and_retry_state(self):
        with state_lock:
            managed_rules["app.example.com|/"] = {
                "source": "agent", "agent_id": "agent-a", "tunnel_id": "tunnel-a",
                "zone_id": "zone-a", "hostname": "app.example.com", "access_app_id": "app-a",
            }
        operation = self._start()
        self._prepare_ack(operation)
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "delete_cloudflare_access_application", return_value=False), \
             patch.object(agent_decommission, "revoke_agent_key") as revoke:
            with self.assertRaisesRegex(agent_decommission.DecommissionError, "access_cleanup_failed"):
                agent_decommission.run_master_cleanup(operation["operation_id"])
        self.assertIn("agent-a", agents)
        self.assertIn("app.example.com|/", managed_rules)
        self.assertEqual(agent_decommissions[operation["operation_id"]]["state"], "cleanup_failed")
        revoke.assert_not_called()

    def test_force_cleanup_revokes_key_before_external_cleanup(self):
        operation = self._start()
        order = []
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "list_agent_keys", return_value={"secret-token": {"bound_agent_id": "agent-a"}}), \
             patch.object(agent_decommission, "revoke_agent_key", side_effect=lambda _token: order.append("revoke") or True), \
             patch.object(agent_decommission, "update_cloudflare_config", side_effect=lambda _tunnel: order.append("tunnel") or True):
            completed = agent_decommission.force_cleanup(operation["operation_id"])
        self.assertEqual(order, ["revoke", "tunnel"])
        self.assertEqual(completed["state"], "forced_completed")
        self.assertTrue(completed["remote_results"]["remote_host_cleanup_required"])
        self.assertNotIn("agent-a", agents)

    def test_final_persistence_failure_restores_agent_and_active_key(self):
        operation = self._start()
        self._prepare_ack(operation)
        with patch.object(agent_decommission, "save_state", return_value=True), \
             patch.object(agent_decommission, "update_cloudflare_config", return_value=True):
            waiting = agent_decommission.run_master_cleanup(operation["operation_id"])
        payload = {
            "operation_id": operation["operation_id"],
            "command_id": waiting["finalize_command_id"],
            "phase": "shutdown_scheduled",
            "self_stop_capability": "supported",
        }
        with patch.object(agent_decommission, "save_state", return_value=True):
            agent_decommission.record_ack("agent-a", operation["operation_id"], payload)
        metadata = {"bound_agent_id": "agent-a", "status": "active"}
        with patch.object(agent_decommission, "list_agent_keys", return_value={"agent-token": metadata}), \
             patch.object(agent_decommission, "revoke_agent_key", return_value=True), \
             patch.object(agent_decommission, "add_agent_key") as restore_key, \
             patch.object(agent_decommission, "save_state", return_value=False):
            with self.assertRaisesRegex(agent_decommission.DecommissionError, "persistence_failed"):
                agent_decommission.complete_finalization(operation["operation_id"])
        self.assertIn("agent-a", agents)
        restore_key.assert_called_once_with("agent-token", metadata)

    def test_generated_compose_explicitly_disables_delete(self):
        token = {"client_id": "client", "client_secret": "secret"}
        with patch.object(service_token_manager, "get_agent_service_token", return_value=token):
            compose = service_token_manager.generate_compose_content("key", "https://master.example.com")
        self.assertIn("DELETE=0", compose)
        self.assertNotIn("DELETE=1", compose)

    def test_admin_routes_start_preview_and_retain_durable_command(self):
        app.config["MASTER_API_KEY"] = "master-test-key"
        headers = {"Authorization": "Bearer master-test-key"}
        client = app.test_client()
        preview = client.get("/api/v2/agents/agent-a/decommission-preview", headers=headers)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.get_json()["preview"]["resource_plan"]["tunnel_disposition"], "preserve_adopted")
        self.assertEqual(client.get("/api/v2/agents/agent-a/decommission-preview").status_code, 401)
        with patch.object(agent_decommission, "save_state", return_value=True):
            started = client.post("/api/v2/agents/agent-a/decommission", headers=headers)
            repeated = client.post("/api/v2/agents/agent-a/remove", headers=headers)
        self.assertEqual(started.status_code, 202)
        self.assertEqual(repeated.status_code, 202)
        first = started.get_json()["operation"]["operation_id"]
        self.assertEqual(repeated.get_json()["operation"]["operation_id"], first)
        self.assertNotIn("rule_keys", started.get_json()["operation"]["resource_plan"])
        self.assertIsNotNone(agent_decommission.command_for_agent("agent-a"))

    def test_command_route_repeats_durable_command_and_rejects_stale_session(self):
        with state_lock:
            agents["agent-a"].update({
                "protocol_version": 2,
                "agent_session_id": "current-session",
                "commands": [],
            })
        operation = self._start()
        client = app.test_client()
        headers = {"Authorization": "Bearer agent-test-key"}
        key_info = {"bound_agent_id": "agent-a", "status": "active"}
        with patch.object(api_v2_routes, "get_agent_key_info", return_value=key_info), \
             patch.object(api_v2_routes, "find_agent_id_by_key", return_value="agent-a"), \
             patch.object(api_v2_routes, "add_agent_key"), \
             patch.object(api_v2_routes, "update_agent"):
            first = client.get("/api/v2/agents/agent-a/commands", headers=headers)
            second = client.get("/api/v2/agents/agent-a/commands", headers=headers)
            stale = client.post(
                f"/api/v2/agents/agent-a/decommission/{operation['operation_id']}/ack",
                headers=headers,
                json={
                    "operation_id": operation["operation_id"],
                    "command_id": operation["prepare_command_id"],
                    "phase": "prepared",
                    "agent_session_id": "stale-session",
                },
            )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.get_json()["commands"], second.get_json()["commands"])
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["code"], "registration_required")

    def test_lost_final_ack_response_can_be_retried_with_revoked_key(self):
        operation = self._start()
        with state_lock:
            stored = agent_decommissions[operation["operation_id"]]
            stored["state"] = "completed"
            stored["acknowledged_commands"] = ["final-command"]
            agents.pop("agent-a")
        client = app.test_client()
        with patch.object(api_v2_routes, "get_agent_key_info", return_value={
            "bound_agent_id": "agent-a", "status": "revoked",
        }):
            response = client.post(
                f"/api/v2/agents/agent-a/decommission/{operation['operation_id']}/ack",
                headers={"Authorization": "Bearer revoked-agent-key"},
                json={
                    "operation_id": operation["operation_id"],
                    "command_id": "final-command",
                    "phase": "shutdown_scheduled",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["code"], "acknowledged")

    def test_operation_round_trips_independently_from_agent_record(self):
        operation = self._start()
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            with patch.object(state_manager.config, "STATE_FILE_PATH", str(state_path)):
                self.assertTrue(state_manager.save_state())
                with state_lock:
                    agents.clear()
                    agent_decommissions.clear()
                state_manager.load_state()
        self.assertIn(operation["operation_id"], agent_decommissions)
        self.assertEqual(agent_decommissions[operation["operation_id"]]["state"], "waiting_for_prepare")

    def test_agents_page_renders_decommission_workflow_without_internal_spec(self):
        with app.test_request_context("/agents"):
            rendered = render_template("agents.html")
        self.assertIn("modal-decommission-agent", rendered)
        self.assertIn("confirm-agent-data-delete", rendered)
        self.assertIn("confirm-agent-files-delete", rendered)
        self.assertNotIn("AGENT_DECOMMISSION_SPEC", rendered)


if __name__ == "__main__":
    unittest.main()
