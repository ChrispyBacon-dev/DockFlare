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
# app/__init__.py
import logging
import queue
import sys
import os

from flask import Flask, request, redirect, url_for, current_app
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, current_user
import docker
from docker.errors import APIError

from . import config

tunnel_state = { "name": config.TUNNEL_NAME, "id": None, "token": None, "status_message": "Initializing...", "error": None }
cloudflared_agent_state = { "container_status": "unknown", "last_action_status": None }

log_queue = queue.Queue(maxsize=config.MAX_LOG_QUEUE_SIZE)
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

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
root_logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

queue_handler = QueueLogHandler(log_queue)
queue_handler.setFormatter(log_formatter)
queue_handler.setLevel(logging.INFO) 
root_logger.addHandler(queue_handler)


docker_client = None
try:
    docker_client = docker.from_env(timeout=10)
    docker_client.ping()
    logging.info("Successfully connected to Docker daemon.")
except APIError as e:
    logging.error(f"FATAL: Docker API error during initial connection: {e}")
    docker_client = None # Ensure it's None on APIError too
except Exception as e:
    logging.error(f"FATAL: Failed to connect to Docker daemon: {e}")
    docker_client = None 

def _load_encrypted_configuration(flask_app: Flask):
    """Attempt to load encrypted configuration from persistent storage.

    Sets flask_app.is_configured and populates flask_app.config values if present.
    """
    try:
        import json
        from cryptography.fernet import Fernet
        data_dir = os.path.dirname(config.STATE_FILE_PATH)
        key_path = os.path.join(data_dir, 'dockflare.key')
        cfg_path = os.path.join(data_dir, 'dockflare_config.dat')
        if os.path.exists(key_path) and os.path.exists(cfg_path):
            with open(key_path, 'rb') as fk:
                key = fk.read()
            fernet = Fernet(key)
            with open(cfg_path, 'rb') as fc:
                decrypted = fernet.decrypt(fc.read())
            loaded = json.loads(decrypted.decode('utf-8'))
            # Populate app.config
            flask_app.config['CF_API_TOKEN'] = loaded.get('cf_api_token')
            flask_app.config['CF_ACCOUNT_ID'] = loaded.get('cf_account_id')
            flask_app.config['CF_ZONE_ID'] = loaded.get('cf_zone_id')
            flask_app.config['TUNNEL_NAME'] = loaded.get('tunnel_name') or config.TUNNEL_NAME
            scan_names_str = loaded.get('tunnel_dns_scan_zone_names') or ''
            flask_app.config['TUNNEL_DNS_SCAN_ZONE_NAMES'] = scan_names_str
            flask_app.config['GRACE_PERIOD_SECONDS'] = int(loaded.get('grace_period_seconds') or config.GRACE_PERIOD_SECONDS)
            flask_app.is_configured = True

            # Backfill module-level config for compatibility
            config.CF_API_TOKEN = flask_app.config['CF_API_TOKEN']
            config.CF_ACCOUNT_ID = flask_app.config['CF_ACCOUNT_ID']
            config.CF_ZONE_ID = flask_app.config['CF_ZONE_ID']
            config.TUNNEL_NAME = flask_app.config['TUNNEL_NAME']
            config.GRACE_PERIOD_SECONDS = flask_app.config['GRACE_PERIOD_SECONDS']
            config.TUNNEL_DNS_SCAN_ZONE_NAMES_STR = scan_names_str
            config.TUNNEL_DNS_SCAN_ZONE_NAMES = [z.strip() for z in scan_names_str.split(',') if z.strip()]
            if config.CF_API_TOKEN:
                config.CF_HEADERS = {"Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "application/json"}
        else:
            flask_app.is_configured = False
    except Exception as e:
        logging.error(f"Failed to load encrypted configuration: {e}")
        flask_app.is_configured = False


def create_app():
    app_instance = Flask(__name__)
    app_instance.secret_key = os.urandom(24)
    app_instance.config['PREFERRED_URL_SCHEME'] = 'http'

    # Initialize CSRF Protection
    csrf = CSRFProtect(app_instance)

    # Attempt to load encrypted configuration
    _load_encrypted_configuration(app_instance)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app_instance)

    from app.core.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            import json
            from cryptography.fernet import Fernet
            data_dir = os.path.dirname(app_instance.config.get('STATE_FILE_PATH', '/app/data/state.json'))
            key_path = os.path.join(data_dir, 'dockflare.key')
            cfg_path = os.path.join(data_dir, 'dockflare_config.dat')
            if not (os.path.exists(key_path) and os.path.exists(cfg_path)):
                return None
            with open(key_path, 'rb') as fk:
                key = fk.read()
            with open(cfg_path, 'rb') as fc:
                encrypted = fc.read()
            fernet = Fernet(key)
            decrypted = fernet.decrypt(encrypted)
            loaded = json.loads(decrypted.decode('utf-8'))
            admin = loaded.get('admin') or {}
            if admin.get('username') == user_id:
                return User(user_id)
            return None
        except Exception as e:
            logging.error(f"user_loader exception: {e}")
            return None

    @app_instance.before_request
    def preflight_and_auth_gating():
        # Allow static and setup during pre-flight
        endpoint = request.endpoint or ''
        if not hasattr(app_instance, 'is_configured'):
            app_instance.is_configured = False

        if app_instance.is_configured is False:
            allowed_prefixes = ('setup.', 'static')
            if not endpoint.startswith(allowed_prefixes):
                return redirect(url_for('setup.step1_credentials'))
        else:
            # Configured: enforce login for all non-auth/static endpoints
            allowed_prefixes = ('auth.', 'static')
            if (not endpoint.startswith(allowed_prefixes)) and not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

    app_instance.reconciliation_info = {
        "in_progress": False,
        "progress": 0,
        "total_items": 0,
        "processed_items": 0,
        "start_time": 0,
        "status": "Not started"
    }

    with app_instance.app_context():
        from .web import routes as web_routes
        app_instance.register_blueprint(web_routes.bp)
        logging.info("Web blueprint registered.")

        from .web.api_v2_routes import api_v2_bp
        # Exclude the API blueprint from CSRF protection
        csrf.exempt(api_v2_bp)
        app_instance.register_blueprint(api_v2_bp)
        logging.info("API v2 blueprint registered.")

        from .web.auth_routes import auth_bp
        app_instance.register_blueprint(auth_bp)
        logging.info("Auth blueprint registered.")

        from .web.setup_routes import setup_bp
        app_instance.register_blueprint(setup_bp)
        logging.info("Setup blueprint registered.")

    return app_instance

app = create_app()