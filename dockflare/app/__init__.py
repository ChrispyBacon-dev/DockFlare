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
# dockflare/app/__init__.py
import logging
import queue
import sys
import os
import json

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .core.user import User
import docker
from docker.errors import APIError
from . import config
from .core.cache import init_app as init_cache

tunnel_state = { "name": config.TUNNEL_NAME, "id": None, "token": None, "status_message": "Initializing...", "error": None }
cloudflared_agent_state = { "container_status": "unknown", "last_action_status": None }

log_queue = queue.Queue(maxsize=config.MAX_LOG_QUEUE_SIZE)
state_update_queue = queue.Queue(maxsize=50) 
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')

oauth = None

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://"
)

class QueueLogHandler(logging.Handler):
    def __init__(self, log_queue_instance):
        super().__init__()
        self.log_queue_instance = log_queue_instance

    def emit(self, record):
        log_entry = self.format(record)
        try:
            self.log_queue_instance.put_nowait(log_entry)
        except queue.Full:
            try:
                self.log_queue_instance.get_nowait() 
                self.log_queue_instance.put_nowait(log_entry)
            except queue.Empty:
                pass 
            except queue.Full:
                 print("Log queue still full after attempting to make space, dropping message.", file=sys.stderr)

root_logger = logging.getLogger()

# Set log level from config
log_level_str = config.LOG_LEVEL.upper()
log_level_map = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}
log_level = log_level_map.get(log_level_str, logging.INFO)
root_logger.setLevel(log_level)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

queue_handler = QueueLogHandler(log_queue)
queue_handler.setFormatter(log_formatter)
queue_handler.setLevel(log_level)
root_logger.addHandler(queue_handler)


def publish_state_event(event_type, data=None):
    message = json.dumps({
        "type": event_type,
        "data": data or {}
    })
    try:
        from .core.cache import get_redis_client
        redis_client = get_redis_client()
        if redis_client:
            try:
                redis_client.publish('dockflare:state_updates', message)
                logging.info(f"STATE_EVENT_PUBLISHED: {event_type} via Redis pub/sub")
                return
            except Exception as pub_err:
                logging.error(f"Redis publish failed: {pub_err}, falling back to queue")

        state_update_queue.put_nowait(message)
        logging.info(f"STATE_EVENT_PUBLISHED: {event_type} - Queue size: {state_update_queue.qsize()} (fallback)")
    except queue.Full:
        logging.warning("State event queue full. Dropping event: %s", event_type)
    except Exception as e:
        logging.error(f"Failed to publish state event {event_type}: {e}")


docker_client = None
try:
    docker_client = docker.from_env(timeout=10)
    docker_client.ping()
    logging.info("Successfully connected to Docker daemon.")
except APIError as e:
    logging.error(f"FATAL: Docker API error during initial connection: {e}")
    docker_client = None 
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    docker_client = None 

def create_app():
    app_instance = Flask(__name__)
    app_instance.secret_key = os.urandom(24)
    app_instance.config['PREFERRED_URL_SCHEME'] = 'http'
    app_instance.config['APP_VERSION'] = config.APP_VERSION
    app_instance.config['SESSION_COOKIE_HTTPONLY'] = True
    app_instance.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app_instance.config['PERMANENT_SESSION_LIFETIME'] = 86400

    # Initialize CSRF Protection
    csrf = CSRFProtect(app_instance)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app_instance)
    login_manager.login_view = 'web.login'
    login_manager.login_message_category = "info"

    # Initialize OAuth
    global oauth
    oauth = OAuth()
    oauth.init_app(app_instance)

    limiter.init_app(app_instance)

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import request, jsonify, redirect, url_for

        if app_instance.config.get('DISABLE_PASSWORD_LOGIN', False):
            from flask_login import login_user
            from app.core.user import User
            user = User('anonymous', auth_method='disabled')
            login_user(user)
            return redirect(request.url)

        if request.path.startswith('/api/'):
            return jsonify({"status": "error", "message": "authentication_required"}), 401

        oauth_providers = app_instance.config.get('OAUTH_PROVIDERS', [])
        if oauth_providers and not app_instance.config.get('DISABLE_PASSWORD_LOGIN', False):
            return redirect(url_for('web.login'))
        elif oauth_providers:
            return redirect(url_for('web.login'))
        else:
            return redirect(url_for('web.login'))

    # Custom user loader that exempts API routes from authentication checks
    @login_manager.request_loader
    def load_user_from_request(request):
        """Load user from request - bypass session auth for designated API endpoints."""

        if request.path.startswith('/api/v2/auth/'):
            return None

        elif request.endpoint and request.endpoint.startswith('api_v2.'):
            # Check if endpoint is UI-only (should use session auth via @login_required)
            from app.web.api_v2_routes import _UI_ENDPOINT_ALLOWLIST
            if request.endpoint in _UI_ENDPOINT_ALLOWLIST:
                # UI endpoints must use session-based auth, don't auto-authenticate
                return None

            # API endpoints (not in UI allowlist) can use MASTER_API_KEY
            from app.core.user import User
            return User('api_user')

        return None

    @login_manager.user_loader
    def load_user(user_id):
        if not app_instance.is_configured:
            return None

        stored_username = app_instance.config.get('DOCKFLARE_USERNAME')
        authorized_oauth_users = app_instance.config.get('OAUTH_AUTHORIZED_USERS', [])

        if user_id == stored_username:
            return User(user_id, auth_method='password')
        elif user_id in authorized_oauth_users:
            return User(user_id, auth_method='oauth')
        return None

    @app_instance.context_processor
    def inject_version():
        """Injects the app version into all templates."""
        return dict(app_version=config.APP_VERSION)

    app_instance.reconciliation_info = {
        "in_progress": False,
        "progress": 0,
        "total_items": 0,
        "processed_items": 0,
        "start_time": 0,
        "status": "Not started"
    }

    # Initialize cache
    init_cache(app_instance)
    logging.info("Cache initialized.")

    with app_instance.app_context():
        from .web import routes as web_routes
        app_instance.register_blueprint(web_routes.bp)
        csrf.exempt(web_routes.auth_callback)
        logging.info("Web blueprint registered.")

        from .web.api_v2_routes import api_v2_bp
        
        csrf.exempt(api_v2_bp)
        app_instance.register_blueprint(api_v2_bp)
        logging.info("API v2 blueprint registered.")

        from .web.setup_routes import setup_bp
        csrf.exempt(setup_bp)
        app_instance.register_blueprint(setup_bp)
        logging.info("Setup blueprint registered.")


        from .web.help_routes import help_bp
        app_instance.register_blueprint(help_bp)
        logging.info("Help blueprint registered.")

    return app_instance

app = create_app()
