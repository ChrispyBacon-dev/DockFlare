import copy
import unittest
from unittest.mock import patch

from app import app
from app.core.notification_manager import normalize_notification_config
from app.web import routes


class NotificationRouteTests(unittest.TestCase):
    def setUp(self):
        self.config_snapshot = {
            key: copy.deepcopy(app.config.get(key))
            for key in (
                "TESTING", "WTF_CSRF_ENABLED", "DOCKFLARE_USERNAME",
                "NOTIFICATION_CONFIG", "TUNNEL_DNS_SCAN_ZONE_NAMES",
            )
        }
        self.configured_snapshot = getattr(app, "is_configured", False)
        app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            DOCKFLARE_USERNAME="notification-admin",
            NOTIFICATION_CONFIG=normalize_notification_config(None),
            TUNNEL_DNS_SCAN_ZONE_NAMES=[],
        )
        app.is_configured = True
        self.client = app.test_client()

    def tearDown(self):
        for key, value in self.config_snapshot.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value
        app.is_configured = self.configured_snapshot

    def _authenticate(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = "notification-admin"
            session["_fresh"] = True

    @staticmethod
    def _form(**overrides):
        values = {
            "notifications-failure_cooldown_seconds": "900",
            "notifications-cloudflare_tunnel_failure": "y",
            "notifications-cloudflare_dns_failure": "y",
            "notifications-cloudflare_access_failure": "y",
            "notifications-docker_listener_failure": "y",
            "notifications-agent_offline": "y",
            "notifications-agent_online": "y",
            "notifications-tunnel_down": "y",
            "notifications-tunnel_recovered": "y",
        }
        values.update(overrides)
        return values

    def test_notification_api_requires_login(self):
        response = self.client.get("/api/v2/notifications/status")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_notification_write_requires_csrf(self):
        self._authenticate()
        app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post("/api/v2/notifications/test", json={})
        self.assertEqual(response.status_code, 400)

    def test_settings_html_never_contains_saved_url(self):
        self._authenticate()
        secret = "sentinel-secret-must-not-reach-browser"
        app.config["NOTIFICATION_CONFIG"] = normalize_notification_config({
            "enabled": True,
            "urls": [f"json://user:{secret}@notify.example/private?token={secret}"],
        })
        public_status = {
            "enabled": True,
            "available": True,
            "configured_destination_count": 1,
            "destinations": [{"summary": "json://configured destination"}],
        }
        with patch.object(routes, "get_all_account_cloudflare_tunnels", return_value=[]), \
             patch.object(routes.notification_manager, "get_public_status", return_value=public_status):
            response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(secret.encode(), response.data)
        self.assertNotIn(b"notify.example", response.data)

    def test_blank_replacement_retains_urls_and_unknown_fields(self):
        self._authenticate()
        secret_url = "json://user:secret@example.invalid/path"
        stored = {
            "notification_config": {
                "enabled": False,
                "urls": [secret_url],
                "events": {"future_event": True},
                "failure_cooldown_seconds": 120,
                "future_option": "keep-me",
            },
            "unrelated": "keep-this-too",
        }

        def apply_runtime(flask_app, config_data):
            flask_app.config["NOTIFICATION_CONFIG"] = normalize_notification_config(
                config_data["notification_config"]
            )

        with patch.object(
            routes.config_loader, "load_encrypted_config_with_cipher",
            return_value=(stored, object()),
        ), patch.object(
            routes.config_loader, "save_encrypted_config", return_value=True,
        ) as save_config, patch.object(
            routes.config_loader, "apply_config_to_app", side_effect=apply_runtime,
        ), patch.object(routes.notification_manager, "configure") as configure:
            response = self.client.post(
                "/settings/notifications",
                data=self._form(**{"notifications-enabled": "y"}),
            )

        self.assertEqual(response.status_code, 302)
        saved = save_config.call_args.args[0]
        self.assertEqual(saved["notification_config"]["urls"], [secret_url])
        self.assertEqual(saved["notification_config"]["future_option"], "keep-me")
        self.assertTrue(saved["notification_config"]["events"]["future_event"])
        self.assertEqual(saved["unrelated"], "keep-this-too")
        configure.assert_called_once_with(app.config["NOTIFICATION_CONFIG"])

    def test_enabled_without_destination_is_rejected(self):
        self._authenticate()
        stored = {"notification_config": normalize_notification_config(None)}
        with patch.object(
            routes.config_loader, "load_encrypted_config_with_cipher",
            return_value=(stored, object()),
        ), patch.object(routes.config_loader, "save_encrypted_config") as save_config:
            response = self.client.post(
                "/settings/notifications",
                data=self._form(**{"notifications-enabled": "y"}),
            )
        self.assertEqual(response.status_code, 302)
        save_config.assert_not_called()

    def test_invalid_replacement_does_not_persist_or_reload(self):
        self._authenticate()
        stored = {"notification_config": {"urls": ["json://saved.invalid/path"]}}
        with patch.object(
            routes.config_loader, "load_encrypted_config_with_cipher",
            return_value=(stored, object()),
        ), patch.object(
            routes.notification_manager, "validate_urls",
            return_value=(False, [(1, "discord")]),
        ), patch.object(
            routes.config_loader, "save_encrypted_config",
        ) as save_config, patch.object(routes.notification_manager, "configure") as configure:
            response = self.client.post(
                "/settings/notifications",
                data=self._form(**{
                    "notifications-enabled": "y",
                    "notifications-replacement_urls": "discord://sentinel-secret",
                }),
            )
        self.assertEqual(response.status_code, 302)
        save_config.assert_not_called()
        configure.assert_not_called()

    def test_test_endpoint_is_rate_limited(self):
        self._authenticate()
        status = {"enabled": True, "available": True}
        with patch.object(routes.notification_manager, "get_public_status", return_value=status), \
             patch.object(routes.notification_manager, "send_test", return_value=("job", True)):
            responses = [
                self.client.post(
                    "/api/v2/notifications/test",
                    json={},
                    environ_overrides={"REMOTE_ADDR": "192.0.2.77"},
                )
                for _ in range(6)
            ]
        self.assertEqual([response.status_code for response in responses[:5]], [202] * 5)
        self.assertEqual(responses[5].status_code, 429)

    def test_test_job_routes_return_only_opaque_status(self):
        self._authenticate()
        status = {"enabled": True, "available": True}
        with patch.object(routes.notification_manager, "get_public_status", return_value=status), \
             patch.object(routes.notification_manager, "send_test", return_value=("opaque-job-id", True)):
            response = self.client.post("/api/v2/notifications/test", json={})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.get_json(), {"status": "accepted", "job_id": "opaque-job-id"})

        with patch.object(routes.notification_manager, "get_test_status", return_value={
            "status": "failure",
            "completed_at": "2026-01-01T00:00:00+00:00",
        }):
            response = self.client.get("/api/v2/notifications/test/opaque-job-id")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("url", str(response.get_json()).lower())
        self.assertEqual(response.get_json()["status"], "failure")

        with patch.object(routes.notification_manager, "get_test_status", return_value=None):
            response = self.client.get("/api/v2/notifications/test/missing")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
