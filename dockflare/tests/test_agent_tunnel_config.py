import copy
import unittest
from unittest.mock import patch

from app import app
from app.core import tunnel_manager
from app.core.state_manager import agents, managed_rules, state_lock
from app.web import api_v2_routes


class AgentTunnelConfigTests(unittest.TestCase):
    def setUp(self):
        with state_lock:
            self.rules_snapshot = copy.deepcopy(managed_rules)
            self.agents_snapshot = copy.deepcopy(agents)
            managed_rules.clear()
            agents.clear()

    def tearDown(self):
        with state_lock:
            managed_rules.clear()
            managed_rules.update(self.rules_snapshot)
            agents.clear()
            agents.update(self.agents_snapshot)

    def test_agent_event_preserves_manual_rules_on_the_same_tunnel(self):
        with state_lock:
            agents["agent-1"] = {
                "id": "agent-1",
                "assigned_tunnel_id": "agent-tunnel",
                "assigned_tunnel_name": "Agent Tunnel"
            }
            managed_rules["plex.example.com|"] = {
                "hostname": "plex.example.com",
                "service": "https://192.0.2.10:32400",
                "status": "active",
                "source": "manual",
                "tunnel_id": "agent-tunnel",
                "no_tls_verify": True
            }
            managed_rules["other.example.com|"] = {
                "hostname": "other.example.com",
                "service": "http://192.0.2.20:8080",
                "status": "active",
                "source": "manual",
                "tunnel_id": "other-tunnel"
            }

        payload = {
            "container": {
                "id": "container-1",
                "name": "sonarr",
                "labels": {
                    "dockflare.enable": "true",
                    "dockflare.hostname": "sonarr.example.com",
                    "dockflare.service": "http://sonarr:8989"
                }
            }
        }
        requests = []

        def capture_request(method, endpoint, json_data=None, **kwargs):
            requests.append((method, endpoint, json_data))
            return {"success": True}

        with app.app_context():
            with patch.dict(app.config, {"CF_ZONE_ID": "zone-1"}):
                with patch.object(api_v2_routes, "save_state"), \
                     patch.object(api_v2_routes, "publish_state_event"), \
                     patch.object(api_v2_routes, "create_cloudflare_dns_record"), \
                     patch.object(api_v2_routes, "handle_access_policy_from_labels", return_value=False), \
                     patch.object(tunnel_manager.cloudflare_api, "get_current_cf_config", return_value={"ingress": []}), \
                     patch.object(tunnel_manager.cloudflare_api, "cf_api_request", side_effect=capture_request):
                    api_v2_routes.process_agent_container_start(payload, "agent-1")

        self.assertEqual(len(requests), 1)
        method, endpoint, body = requests[0]
        self.assertEqual(method, "PUT")
        self.assertIn("/agent-tunnel/configurations", endpoint)

        ingress = body["config"]["ingress"]
        entries = {entry.get("hostname"): entry for entry in ingress if entry.get("hostname")}
        self.assertEqual(set(entries), {"plex.example.com", "sonarr.example.com"})
        self.assertEqual(entries["plex.example.com"]["originRequest"], {"noTLSVerify": True})
        self.assertEqual(ingress[-1], {"service": "http_status:404"})

    def test_agent_tunnel_builder_excludes_other_tunnels_and_inactive_rules(self):
        with state_lock:
            agents["agent-1"] = {"assigned_tunnel_id": "agent-tunnel"}
            agents["agent-2"] = {"assigned_tunnel_id": "other-tunnel"}
            managed_rules["agent.example.com|"] = {
                "hostname": "agent.example.com",
                "service": "http://agent:8080",
                "status": "active",
                "source": "agent",
                "agent_id": "agent-1",
                "tunnel_id": "agent-tunnel"
            }
            managed_rules["inactive.example.com|"] = {
                "hostname": "inactive.example.com",
                "service": "http://inactive:8080",
                "status": "pending_deletion",
                "source": "agent",
                "agent_id": "agent-1",
                "tunnel_id": "agent-tunnel"
            }
            managed_rules["other.example.com|"] = {
                "hostname": "other.example.com",
                "service": "http://other:8080",
                "status": "active",
                "source": "agent",
                "agent_id": "agent-2",
                "tunnel_id": "other-tunnel"
            }

        ingress = tunnel_manager._build_ingress_entries_for_tunnel("agent-tunnel", "master-tunnel")
        hostnames = [entry.get("hostname") for entry in ingress if entry.get("hostname")]

        self.assertEqual(hostnames, ["agent.example.com"])
        self.assertEqual(ingress[-1], {"service": "http_status:404"})


if __name__ == "__main__":
    unittest.main()
