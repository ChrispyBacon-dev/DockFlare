import importlib.util
import os
import pathlib
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


AGENT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGENT_ROOT / "app"))
SPEC = importlib.util.spec_from_file_location("dockflare_agent_decommission", AGENT_ROOT / "app" / "decommission.py")
decommission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(decommission)


class FakeContainer:
    def __init__(self, container_id, name, status="running", service=None, image="image:tag"):
        self.id = container_id
        self.name = name
        self.status = status
        self.labels = {"com.docker.compose.service": service} if service else {}
        self.attrs = {"Config": {"Image": image}}
        self.stop_calls = 0

    def reload(self):
        return None

    def stop(self, timeout=15):
        self.stop_calls += 1
        self.status = "exited"


class FakeContainers:
    def __init__(self, containers):
        self.by_name = {container.name: container for container in containers}
        self.by_id = {container.id: container for container in containers}

    def get(self, value):
        container = self.by_name.get(value) or self.by_id.get(value)
        if container is None:
            matches = [item for container_id, item in self.by_id.items() if container_id.startswith(value)]
            container = matches[0] if len(matches) == 1 else None
        if container is None:
            raise decommission.docker.errors.NotFound("missing")
        return container


class FakeDocker:
    def __init__(self, containers):
        self.containers = FakeContainers(containers)


class LocalDecommissionTests(unittest.TestCase):
    def test_official_compose_keeps_docker_delete_disabled(self):
        compose = (AGENT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("DELETE=0", compose)
        self.assertNotIn("DELETE=1", compose)

    def test_tombstone_is_atomic_private_and_secret_free(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "decommission.json")
            value = decommission.persist_tombstone("operation", "agent", "prepared", path)
            self.assertEqual(value["phase"], "prepared")
            self.assertEqual(decommission.load_tombstone(path)["operation_id"], "operation")
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
            self.assertNotIn("token", str(value).lower())

    def test_tombstone_cannot_change_operation_or_downgrade_finalized_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "decommission.json")
            decommission.persist_tombstone("operation", "agent", "prepared", path)
            decommission.persist_tombstone("operation", "agent", "finalized", path)
            with self.assertRaisesRegex(ValueError, "decommission_tombstone_conflict"):
                decommission.persist_tombstone("other-operation", "agent", "prepared", path)
            with self.assertRaisesRegex(ValueError, "decommission_tombstone_conflict"):
                decommission.persist_tombstone("operation", "agent", "prepared", path)

    def test_tunnel_is_stopped_but_never_removed(self):
        tunnel = FakeContainer("a" * 64, "dockflare-agent-tunnel", image="cloudflare/cloudflared:latest")
        result, image = decommission.stop_tunnel_container(FakeDocker([tunnel]))
        self.assertEqual(result, "stopped")
        self.assertEqual(image, "cloudflare/cloudflared:latest")
        self.assertEqual(tunnel.stop_calls, 1)
        self.assertFalse(hasattr(tunnel, "remove_calls"))

    def test_already_stopped_and_absent_are_idempotent(self):
        stopped = FakeContainer("b" * 64, "dockflare-agent-tunnel", status="exited")
        result, _image = decommission.stop_tunnel_container(FakeDocker([stopped]))
        self.assertEqual(result, "stopped")
        self.assertEqual(stopped.stop_calls, 0)
        result, _image = decommission.stop_tunnel_container(FakeDocker([]))
        self.assertEqual(result, "absent")

    def test_duplicate_tunnel_stop_has_no_second_stop_side_effect(self):
        tunnel = FakeContainer("f" * 64, "dockflare-agent-tunnel")
        client = FakeDocker([tunnel])
        self.assertEqual(decommission.stop_tunnel_container(client)[0], "stopped")
        self.assertEqual(decommission.stop_tunnel_container(client)[0], "stopped")
        self.assertEqual(tunnel.stop_calls, 1)

    def test_self_target_requires_runtime_id_and_expected_identity(self):
        runtime_id = "c" * 64
        expected = FakeContainer(runtime_id, "dockflare-agent", service="dockflare-agent", image="alplat/dockflare-agent:dev")
        unrelated = FakeContainer("d" * 64, "database", service="database")
        client = FakeDocker([expected, unrelated])
        self.assertIs(decommission.resolve_self_container(client, runtime_id[:12]), expected)
        self.assertIsNone(decommission.resolve_self_container(client, unrelated.id[:12]))
        self.assertIsNone(decommission.resolve_self_container(client, "dockflare-agent"))

    def test_self_stop_is_scheduled_without_delete(self):
        runtime_id = "e" * 64
        expected = FakeContainer(runtime_id, "dockflare-agent", service="dockflare-agent")
        with patch.object(decommission, "Thread") as thread:
            self.assertTrue(decommission.schedule_self_stop(FakeDocker([expected]), runtime_id[:12]))
        thread.assert_called_once()
        self.assertTrue(thread.call_args.kwargs["daemon"])


if __name__ == "__main__":
    unittest.main()
