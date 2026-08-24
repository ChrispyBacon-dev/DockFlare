import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch


AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT / "app"))
SPEC = importlib.util.spec_from_file_location("dockflare_agent_main", AGENT_ROOT / "app" / "main.py")
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class FakeContainer:
    def __init__(self, container_id, name, labels, status="running"):
        self.id = container_id
        self.name = name
        self.labels = labels
        self.status = status


class FakeContainers:
    def __init__(self, values):
        self.values = values

    def list(self):
        return list(self.values)


class FakeDocker:
    def __init__(self, values):
        self.containers = FakeContainers(values)


class AgentProducerProtocolTests(unittest.TestCase):
    def setUp(self):
        agent.AGENT_ID = None
        agent.PROTOCOL_VERSION = None
        agent.AGENT_SESSION_ID = None
        agent._event_sequence = 0
        agent._report_sequence = 0

    def test_registration_context_requires_v2_session_and_resets_sequences(self):
        self.assertFalse(agent.apply_registration_response({
            "agent_id": "agent-a", "protocol_version": 2,
        }))
        agent._event_sequence = 9
        self.assertTrue(agent.apply_registration_response({
            "agent_id": "agent-a", "protocol_version": 2, "agent_session_id": "master-session",
        }))
        self.assertEqual(agent.next_event_sequence(), 1)
        self.assertEqual(agent.next_report_sequence(), 1)

    def test_inventory_is_complete_filtered_and_deduplicated_by_scan(self):
        docker_client = FakeDocker([
            FakeContainer("one", "one", {
                "dockflare.enable": "true",
                "dockflare.hostname": "one.example.com",
                "compose.project": "private",
            }),
            FakeContainer("two", "two", {"app.enabled": "true"}),
        ])
        inventory = agent.collect_complete_inventory(docker_client)
        self.assertEqual(len(inventory), 1)
        self.assertEqual(inventory[0]["labels"], {
            "dockflare.enable": "true",
            "dockflare.hostname": "one.example.com",
        })

    def test_status_report_uses_top_level_v2_shape(self):
        agent.apply_registration_response({
            "agent_id": "agent-a", "protocol_version": 2, "agent_session_id": "master-session",
        })
        captured = []
        with patch.object(agent, "_post_agent_payload", side_effect=lambda payload: captured.append(payload) or True):
            self.assertTrue(agent.send_status_report([], True))
        self.assertEqual(captured[0]["containers"], [])
        self.assertEqual(captured[0]["inventory_scope"], "dockflare_enabled_running")
        self.assertTrue(captured[0]["inventory_complete"])
        self.assertNotIn("container", captured[0])

    def test_event_filters_labels_and_allocates_sequence(self):
        agent.apply_registration_response({
            "agent_id": "agent-a", "protocol_version": 2, "agent_session_id": "master-session",
        })
        captured = []
        with patch.object(agent, "_post_agent_payload", side_effect=lambda payload: captured.append(payload) or True):
            agent.report_event_to_master("container_start", {
                "id": "container", "name": "service",
                "labels": {"dockflare.enable": "true", "secret": "DO_NOT_SEND"},
            })
        self.assertEqual(captured[0]["event_sequence"], 1)
        self.assertNotIn("secret", captured[0]["container"]["labels"])

    def test_docker_event_types_are_normalized(self):
        self.assertEqual(agent.normalize_docker_event_type("start"), "container_start")
        self.assertEqual(agent.normalize_docker_event_type("stop"), "container_stop")
        self.assertEqual(agent.normalize_docker_event_type("die"), "container_stop")
        self.assertIsNone(agent.normalize_docker_event_type("destroy"))


if __name__ == "__main__":
    unittest.main()
