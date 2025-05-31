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

from flask import Flask
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

def create_app():

    app_instance = Flask(__name__) 
    app_instance.secret_key = os.urandom(24) 
    app_instance.config['PREFERRED_URL_SCHEME'] = 'http' 
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
        app_instance.register_blueprint(api_v2_bp) 
        logging.info("API v2 blueprint registered.")
    return app_instance

app = create_app()