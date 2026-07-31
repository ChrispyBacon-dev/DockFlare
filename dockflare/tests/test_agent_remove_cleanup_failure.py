from flask import Flask

from app.core import state_manager
from app.web import api_v2_routes


def make_app():
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        MASTER_API_KEY="master-test-key",
        CF_ZONE_ID="zone-primary",
        TUNNEL_DNS_SCAN_ZONE_NAMES=[],
    )
    app.register_blueprint(api_v2_routes.api_v2_bp)
    return app


def reset_state():
    with state_manager.state_lock:
        state_manager.agents.clear()
        state_manager.managed_rules.clear()


def test_remove_agent_preserves_record_when_cloudflare_tunnel_cleanup_fails(monkeypatch):
    reset_state()
    with state_manager.state_lock:
        state_manager.agents["agent-1"] = {
            "id": "agent-1",
            "display_name": "edge-1",
            "status": "enrolled",
            "assigned_tunnel_id": "tunnel-1",
            "assigned_tunnel_name": "edge-tunnel",
        }
        state_manager.managed_rules["app.example.com|"] = {
            "source": "agent",
            "agent_id": "agent-1",
            "hostname": "app.example.com",
        }

    monkeypatch.setattr(api_v2_routes, "get_all_account_cloudflare_tunnels", lambda: [{"id": "tunnel-1"}])
    monkeypatch.setattr(api_v2_routes, "delete_tunnel_via_api", lambda tunnel_id: False)
    monkeypatch.setattr(api_v2_routes, "get_dns_records_for_tunnel", lambda zone_id, tunnel_id: [])

    app = make_app()
    response = app.test_client().post(
        "/api/v2/agents/agent-1/remove",
        headers={"Authorization": "Bearer master-test-key"},
    )

    assert response.status_code == 502
    assert response.get_json()["status"] == "error"
    assert state_manager.get_agent("agent-1") is not None
    assert "app.example.com|" in state_manager.managed_rules
