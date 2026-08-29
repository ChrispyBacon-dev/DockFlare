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
    def __init__(self, values, missing_ids=None):
        self.values = values
        self.by_id = {container.id: container for container in values}
        self.missing_ids = set(missing_ids or [])

    def list(self):
        return list(self.values)

    def get(self, container_id):
        if container_id in self.missing_ids or container_id not in self.by_id:
            raise agent.docker.errors.NotFound("container not found")
        return self.by_id[container_id]


class FakeDocker:
    def __init__(self, values, events=None, missing_ids=None):
        self.containers = FakeContainers(values, missing_ids)
        self.event_values = list(events or [])

    def events(self, **_kwargs):
        return iter(self.event_values)


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

    def test_event_container_id_prefers_canonical_actor_shape(self):
        event = {
            "Actor": {"ID": "actor-id"},
            "id": "legacy-id",
        }
        self.assertEqual(agent.get_docker_event_container_id(event), "actor-id")
        self.assertEqual(agent.get_docker_event_container_id({"id": "legacy-id"}), "legacy-id")
        self.assertIsNone(agent.get_docker_event_container_id({"Actor": {"Attributes": {}}}))

    def test_start_event_uses_actor_id(self):
        container = FakeContainer("container-id", "service", {
            "dockflare.enable": "true",
            "dockflare.hostname": "service.example.com",
        })
        client = FakeDocker([container], events=[{
            "Type": "container",
            "Action": "start",
            "Actor": {"ID": "container-id", "Attributes": {"name": "service"}},
        }])

        with patch.object(agent, "report_event_to_master") as report:
            agent.listen_for_docker_events(client, "dockflare.", initial_scan=False)

        report.assert_called_once_with("container_start", {
            "id": "container-id",
            "name": "service",
            "labels": container.labels,
        })

    def test_stop_and_die_not_found_events_use_actor_fallback(self):
        for action in ("stop", "die"):
            with self.subTest(action=action):
                client = FakeDocker([], missing_ids={"removed-id"}, events=[{
                    "Type": "container",
                    "Action": action,
                    "Actor": {
                        "ID": "removed-id",
                        "Attributes": {
                            "name": "removed-service",
                            "dockflare.enable": "true",
                            "private.label": "do-not-send",
                        },
                    },
                }])

                with patch.object(agent, "report_event_to_master") as report:
                    agent.listen_for_docker_events(client, "dockflare.", initial_scan=False)

                report.assert_called_once_with("container_stop", {
                    "id": "removed-id",
                    "name": "removed-service",
                    "labels": {"dockflare.enable": "true"},
                })

    def test_missing_event_id_is_ignored_without_payload_logging(self):
        client = FakeDocker([], events=[{
            "Type": "container",
            "Action": "start",
            "Actor": {"Attributes": {"name": "service", "secret": "do-not-log"}},
        }])

        with patch.object(agent, "report_event_to_master") as report, \
             patch.object(agent.logging, "warning") as warning:
            agent.listen_for_docker_events(client, "dockflare.", initial_scan=False)

        report.assert_not_called()
        warning.assert_called_once()
        self.assertNotIn("secret", " ".join(str(value) for value in warning.call_args.args))


if __name__ == "__main__":
    unittest.main()
