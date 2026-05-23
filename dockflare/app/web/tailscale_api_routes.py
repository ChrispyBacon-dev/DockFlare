# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# dockflare/app/web/tailscale_api_routes.py
import copy
import logging
import secrets
import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, current_app

from app import config, tailscale_state
from app.core.state_manager import list_tailscale_rules, remove_tailscale_rule, tailscale_rules, state_lock, save_state

tailscale_api_bp = Blueprint('tailscale_api', __name__, url_prefix='/api/v2/tailscale')


def _extract_bearer_token():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return request.headers.get('X-Api-Key') or request.args.get('api_key')


@tailscale_api_bp.before_request
def _enforce_api_key():
    if request.method == 'OPTIONS':
        return
    expected_key = current_app.config.get('MASTER_API_KEY') or config.MASTER_API_KEY
    if not expected_key:
        return jsonify({"status": "error", "message": "master_api_key_not_configured"}), 503
    provided = _extract_bearer_token()
    if provided and secrets.compare_digest(provided, expected_key):
        return
    return jsonify({"status": "error", "message": "unauthorized"}), 401


def _serialize_ts_rule(rule_key, rule_data):
    if not rule_data:
        return {"id": rule_key}
    serialized = copy.deepcopy(rule_data)
    delete_at = serialized.get("delete_at")
    if isinstance(delete_at, datetime):
        dt_utc = delete_at.astimezone(timezone.utc) if delete_at.tzinfo else delete_at.replace(tzinfo=timezone.utc)
        serialized["delete_at"] = dt_utc.isoformat().replace('+00:00', 'Z')
    serialized["id"] = rule_key
    return serialized


@tailscale_api_bp.route('/status', methods=['GET'])
def ts_get_status():
    if not config.TAILSCALE_ENABLED:
        return jsonify({
            "status": "success",
            "enabled": False,
            "node": None,
            "version_mismatch": False,
            "last_error": None,
            "service_count": 0,
        })

    return jsonify({
        "status": "success",
        "enabled": True,
        "node": tailscale_state.get("node"),
        "version_mismatch": tailscale_state.get("version_mismatch", False),
        "last_error": tailscale_state.get("last_error"),
        "service_count": len(list_tailscale_rules()),
        "socket": config.TAILSCALE_SOCKET,
        "tailnet": config.TAILSCALE_TAILNET,
        "service_prefix": config.TAILSCALE_SERVICE_PREFIX,
    })


@tailscale_api_bp.route('/services', methods=['GET'])
def ts_list_services():
    rules = list_tailscale_rules()
    return jsonify({
        "status": "success",
        "services": [_serialize_ts_rule(k, v) for k, v in rules.items()],
        "count": len(rules),
    })


@tailscale_api_bp.route('/services/<path:rule_key>', methods=['DELETE'])
def ts_delete_service(rule_key):
    from app.core import tailscale_manager

    with state_lock:
        rule_data = tailscale_rules.get(rule_key)
        if rule_data is None:
            return jsonify({"status": "error", "message": "service_not_found"}), 404

        try:
            tailscale_manager.remove_service(rule_data.get("name", rule_key))
            if rule_data.get("funnel_active"):
                tailscale_manager.disable_funnel(
                    rule_data.get("funnel_port", 443),
                    rule_data.get("protocol", "https"),
                )
        except tailscale_manager.TailscaleCLIError as e:
            logging.error("TS_API: CLI error removing %s: %s", rule_key, e)
            return jsonify({"status": "error", "message": str(e)}), 500
        except Exception as e:
            logging.error("TS_API: Unexpected error removing %s: %s", rule_key, e, exc_info=True)
            return jsonify({"status": "error", "message": "internal_error"}), 500

        del tailscale_rules[rule_key]
        save_state()

    logging.info("TS_API: Deleted service %s", rule_key)
    return jsonify({"status": "success", "deleted": rule_key})


@tailscale_api_bp.route('/reconcile', methods=['POST'])
def ts_trigger_reconcile():
    if not config.TAILSCALE_ENABLED:
        return jsonify({"status": "error", "message": "tailscale_not_enabled"}), 400

    from app.core.reconciler import _run_tailscale_reconciliation

    t = threading.Thread(
        target=_run_tailscale_reconciliation,
        name="TailscaleReconcileManual",
        daemon=True,
    )
    t.start()
    return jsonify({"status": "success", "message": "reconciliation_started"})


@tailscale_api_bp.route('/serve-state', methods=['GET'])
def ts_get_serve_state():
    if not config.TAILSCALE_ENABLED:
        return jsonify({"status": "success", "services": {}, "enabled": False})

    from app.core import tailscale_manager

    try:
        serve_state = tailscale_manager.get_current_serve_state()
        return jsonify({"status": "success", "services": serve_state})
    except tailscale_manager.TailscaleSocketError as e:
        return jsonify({"status": "error", "message": "socket_unavailable", "detail": str(e)}), 503
    except tailscale_manager.TailscaleCLIError as e:
        return jsonify({"status": "error", "message": "cli_error", "detail": str(e)}), 500
    except Exception as e:
        logging.error("TS_API: serve-state error: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": "internal_error"}), 500


@tailscale_api_bp.route('/funnel-state', methods=['GET'])
def ts_get_funnel_state():
    if not config.TAILSCALE_ENABLED:
        return jsonify({"status": "success", "funnels": {}, "enabled": False})

    from app.core import tailscale_manager

    try:
        funnel_state = tailscale_manager.get_current_funnel_state()
        return jsonify({"status": "success", "funnels": funnel_state})
    except tailscale_manager.TailscaleSocketError as e:
        return jsonify({"status": "error", "message": "socket_unavailable", "detail": str(e)}), 503
    except tailscale_manager.TailscaleCLIError as e:
        return jsonify({"status": "error", "message": "cli_error", "detail": str(e)}), 500
    except Exception as e:
        logging.error("TS_API: funnel-state error: %s", e, exc_info=True)
        return jsonify({"status": "error", "message": "internal_error"}), 500
