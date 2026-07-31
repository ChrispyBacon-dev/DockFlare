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
# dockflare/app/main.py
import logging
import threading
import time
import datetime
import sys
import os
import json
import secrets
from cryptography.fernet import Fernet

from app import app, docker_client, tunnel_state, cloudflared_agent_state, config

from app.core.state_manager import load_state, ensure_default_bypass_policy, ensure_authenticated_default_policy
from app.core.tunnel_manager import (
    initialize_tunnel,
    update_cloudflared_container_status, 
    start_cloudflared_container
)
from app.core.docker_handler import start_event_listeners, process_container_start
from app.core.reconciler import cleanup_expired_rules, reconcile_state_threaded

stop_event = threading.Event()
background_threads_list = []
agent_status_updater_thread = None
main_initialization_thread = None


def _restart_if_requested():
    data_path = os.path.dirname(config.STATE_FILE_PATH)
    flag_path = os.path.join(data_path, 'restore-restart.flag')
    if os.path.exists(flag_path):
        try:
            os.remove(flag_path)
        except OSError as err:
            logging.error("Failed to remove restart flag %s: %s", flag_path, err, exc_info=True)
        logging.info("RESTORE: Restart flag detected. Exiting process for container restart.")
        sys.exit(0)

def run_all_background_tasks():
    global background_threads_list, agent_status_updater_thread 
    
    threads_to_start = []
    if not docker_client:
        logging.warning("Docker client unavailable. Core background tasks (Event Listener, Cleanup) cannot start.")
    else:
        tunnel_ready_for_tasks = False
        if config.USE_EXTERNAL_CLOUDFLARED:
            if config.EXTERNAL_TUNNEL_ID:
                tunnel_ready_for_tasks = True
            else:
                logging.warning("External mode: EXTERNAL_TUNNEL_ID missing. Background tasks needing tunnel ID may fail.")
        elif tunnel_state.get("id") and tunnel_state.get("token"):
            tunnel_ready_for_tasks = True
        else:
            logging.warning("Managed tunnel not fully initialized (ID/token missing). Background tasks needing tunnel ID may fail.")

        if tunnel_ready_for_tasks:
            logging.info("Starting core background task threads (Docker Listeners, Cleanup Task)...")
            event_threads = start_event_listeners(stop_event)
            threads_to_start.extend(event_threads)
            
            cleanup_thread = threading.Thread(target=cleanup_expired_rules, args=(stop_event,), name="CleanupTask", daemon=True)
            threads_to_start.append(cleanup_thread)
        else:
            logging.warning("Tunnel not ready. Skipping Docker event listener and cleanup task.")

    if not config.USE_EXTERNAL_CLOUDFLARED and docker_client:
        logging.info("Starting periodic agent status updater thread...")
        agent_status_updater_thread = threading.Thread(target=periodic_agent_status_updater, name="AgentStatusUpdater", daemon=True)
        threads_to_start.append(agent_status_updater_thread)
    
    for t in threads_to_start:
        t.start()
    
    background_threads_list.extend(threads_to_start)
    if threads_to_start: 
        logging.info(f"{len(threads_to_start)} background tasks initiated.")
    return threads_to_start

def periodic_agent_status_updater():
    logging.info("Periodic agent status updater task starting...")
    while not stop_event.is_set():
        try:
            logging.debug("Running periodic agent status update check...")
            update_cloudflared_container_status() 
        except Exception as e_status_update:
            logging.error(f"Error in periodic agent status updater loop: {e_status_update}", exc_info=True)
        
        if stop_event.is_set(): break 
        stop_event.wait(config.AGENT_STATUS_UPDATE_INTERVAL_SECONDS)
    logging.info("Periodic agent status updater task stopped.")

def start_core_services():
    global background_threads_list 

    logging.info("Core services initialization process started.")
    if not docker_client:
        logging.error("Docker client unavailable. Critical functionalities will be affected.")
        return

    initialize_tunnel()
    logging.info(f"Tunnel initialization attempt complete. Status: {tunnel_state.get('status_message')}, Error: {tunnel_state.get('error')}")

    ensure_default_bypass_policy(flask_app=app)
    logging.info("Bypass policy post-setup initialization complete.")

    from app.core import idp_manager
    from app.core.state_manager import identity_providers, save_state, state_lock, save_identity_provider
    logging.info("Syncing identity providers after setup...")
    try:
        with app.app_context():
            idps = idp_manager.list_identity_providers()
        if idps:
            with state_lock:
                for idp in idps:
                    idp_id = idp.get("id")
                    idp_type = idp.get("type", "unknown")
                    if idp_id and idp_type:
                        
                        friendly_name = idp_type
                        idp_data = {
                            "cloudflare_id": idp_id,
                            "name": idp.get("name", "Unknown"),
                            "type": idp_type,
                            "last_synced": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "system_managed": idp_manager.is_system_managed_idp(idp_type)
                        }
                        
                        identity_providers[friendly_name] = idp_data
                save_state()
            logging.info(f"Synced {len(idps)} identity providers from Cloudflare (keyed by type)")
    except Exception as e:
        logging.error(f"Error syncing identity providers: {e}", exc_info=True)

    ensure_authenticated_default_policy(flask_app=app)
    logging.info("Authenticated policy post-setup initialization complete.")

    initial_scan_needed_and_possible = True
    if config.USE_EXTERNAL_CLOUDFLARED:
        if not config.EXTERNAL_TUNNEL_ID:
            logging.error("External mode enabled, but EXTERNAL_TUNNEL_ID is missing. Skipping initial scan.")
            initial_scan_needed_and_possible = False
    elif not (tunnel_state.get("id") and tunnel_state.get("token")):
        logging.error("Managed tunnel not fully initialized (missing ID or token). Skipping initial scan.")
        initial_scan_needed_and_possible = False

    if initial_scan_needed_and_possible:
        logging.info("Performing initial container scan and rule processing...")
        flask_app_instance = app 
        max_initial_scan_time = 120 
        scan_start_time = time.time()
        
        if not hasattr(flask_app_instance, 'reconciliation_info'):
             flask_app_instance.reconciliation_info = {} 
        
        flask_app_instance.reconciliation_info.update({
            "in_progress": True, "progress": 0, "total_items": 0,
            "processed_items": 0, "start_time": scan_start_time,
            "status": "Starting initial container scan..."
        })

        try:
            containers = docker_client.containers.list(all=config.SCAN_ALL_NETWORKS)
            container_count = len(containers)
            logging.info(f"[InitialScan] Found {container_count} total containers to scan.")
            flask_app_instance.reconciliation_info["total_items"] = container_count
            
            processed_count = 0
            batch_size = 5 
            for i in range(0, container_count, batch_size):
                if time.time() - scan_start_time > max_initial_scan_time:
                    logging.warning("[InitialScan] Timeout reached during initial container processing.")
                    break
                
                current_batch = containers[i:i+batch_size]
                flask_app_instance.reconciliation_info["status"] = f"Initial scan: batch {i//batch_size + 1}/{(container_count+batch_size-1)//batch_size if container_count > 0 else 1}"
                
                for container_obj in current_batch:
                    process_container_start(container_obj) 
                    processed_count += 1
                    if container_count > 0:
                        flask_app_instance.reconciliation_info["progress"] = min(100, int((processed_count / container_count) * 100))
                flask_app_instance.reconciliation_info["processed_items"] = processed_count
                
                time.sleep(0.1) 
                if stop_event.is_set(): break 

        except Exception as e_scan:
            logging.error(f"Error during initial container scan/processing: {e_scan}", exc_info=True)
            if hasattr(flask_app_instance, 'reconciliation_info'):
                flask_app_instance.reconciliation_info["status"] = f"Error during initial scan: {str(e_scan)[:100]}"
        
        if hasattr(flask_app_instance, 'reconciliation_info'):
            flask_app_instance.reconciliation_info.update({"in_progress": False, "progress": 100, "status": "Initial container scan complete.", "completed_at": time.time()})
        logging.info("Initial container scan and rule processing complete.")

        logging.info("Scheduling full background reconciliation after initial setup (15s delay).")
        threading.Timer(15, reconcile_state_threaded).start() 

        if not config.USE_EXTERNAL_CLOUDFLARED and tunnel_state.get("id") and tunnel_state.get("token"):
            logging.info("Checking and reconciling managed cloudflared agent container...")
            start_cloudflared_container()

    if getattr(config, 'EMAIL_CONFIG', {}).get('enabled'):
        try:
            container = docker_client.containers.get('dockflare-mail-manager')
            if container.status == 'running':
                container.restart()
                logging.info("Email active: restarted dockflare-mail-manager to sync config.")
        except Exception as e:
            logging.debug(f"dockflare-mail-manager not found or could not restart: {e}")

        try:
            from app.core.email_manager import get_email_sending_status
            from app.web.email_routes import save_email_config
            email_cfg = config.EMAIL_CONFIG
            updated = False
            for domain, domain_cfg in email_cfg.get('domains', {}).items():
                if domain_cfg.get('email_sending_status') in (None, 'unknown'):
                    zone_id = domain_cfg.get('zone_id')
                    if zone_id:
                        status = get_email_sending_status(zone_id, domain)
                        domain_cfg['email_sending_status'] = status
                        updated = True
                        logging.info(f"Email sending status for {domain}: {status}")
            if updated:
                save_email_config(email_cfg)
        except Exception as e:
            logging.debug(f"Could not refresh email sending status on startup: {e}")

    run_all_background_tasks()

def perform_initial_setup_and_tasks():
    with app.app_context():
        if not app.is_configured:
            logging.info("Application is not configured. Skipping initial core service startup.")

            run_all_background_tasks()
            return

    logging.info("Application is configured. Starting core services.")
    start_core_services()

def main_application_entrypoint():
    global main_initialization_thread

    logging.info("-" * 52)
    logging.info("--- DockFlare Starting ---")
    logging.info(f"--- Version: {config.APP_VERSION} ---")
    logging.info("--- web: https://dockflare.app ---")
    logging.info("-" * 52)

    # === DockFlare Config Check & Pre-Flight Setup ===
    data_path = os.path.dirname(config.STATE_FILE_PATH)
    key_file = os.path.join(data_path, 'dockflare.key')
    config_file = os.path.join(data_path, 'dockflare_config.dat')

    app.is_configured = False
    app.import_from_env = False
    if os.path.exists(config_file) and os.path.exists(key_file):
        logging.info("Configuration file found. Loading settings.")
        try:
            from app.web import config_loader

            config_data, fernet = config_loader.load_encrypted_config_with_cipher()
            if config_data is None or fernet is None:
                raise ValueError("Configuration could not be decrypted")

            master_key_env = os.getenv('DOCKFLARE_API_KEY')
            master_key_existing = config_data.get('master_api_key')
            if not master_key_env and not master_key_existing:
                master_key_existing = secrets.token_urlsafe(40)
                config_data['master_api_key'] = master_key_existing
                updated_payload = fernet.encrypt(json.dumps(config_data).encode('utf-8'))
                with open(config_loader.config_file_path(), 'wb') as f:
                    f.write(updated_payload)

            config_loader.apply_config_to_app(app, config_data)

            from app import oauth
            from app.core.oauth_manager import register_oauth_providers
            register_oauth_providers(app, oauth, fernet)
            logging.info("DockFlare is configured and in Operational Mode.")
        except Exception as e:
            logging.error(f"Failed to load or decrypt configuration: {e}. Starting in Pre-Flight mode.", exc_info=True)
            app.is_configured = False
    else:
        logging.info("Configuration file not found. Starting in Pre-Flight Mode.")
        app.is_configured = False
        if os.getenv('CF_API_TOKEN'):
            logging.info("Found CF_API_TOKEN environment variable. Activating migration import flow.")
            app.import_from_env = True
        master_key_env = os.getenv('DOCKFLARE_API_KEY')
        if master_key_env:
            app.config['MASTER_API_KEY'] = master_key_env
            config.MASTER_API_KEY = master_key_env
    # === DockFlare Config Check & Pre-Flight Setup ===

    _restart_if_requested()

    load_state()
    logging.info("Initial state loading from file complete.")
    
    ensure_default_bypass_policy(flask_app=app)
    logging.info("Default bypass policy initialization complete.")

    ensure_authenticated_default_policy(flask_app=app)
    logging.info("Default authenticated policy initialization complete.")

    if docker_client:
        try:
            container_id = os.getenv('HOSTNAME')
            if container_id:
                logging.info(f"Attempting to discover public hostname from container ID: {container_id}")
                container = docker_client.containers.get(container_id)
                hostname_label = container.labels.get('dockflare.hostname')
                if hostname_label:
                    app.config['DOCKFLARE_PUBLIC_HOSTNAME'] = hostname_label
                    config.DOCKFLARE_PUBLIC_HOSTNAME = hostname_label
                    logging.info(f"Discovered public hostname from label: {hostname_label}")
        except Exception as e:
            logging.warning(f"Could not discover public hostname from Docker label: {e}", exc_info=True)

    if not docker_client:
        logging.error("Docker client is unavailable. Dockflare will operate with limited functionality.")
        if tunnel_state: tunnel_state["status_message"] = "Error: Docker client unavailable."
        if tunnel_state: tunnel_state["error"] = "Failed to connect to Docker daemon."
        if cloudflared_agent_state: cloudflared_agent_state["container_status"] = "docker_unavailable"
    else:
        logging.info("Docker client connected. Proceeding with full initialization in background.")
        main_initialization_thread = threading.Thread(
            target=perform_initial_setup_and_tasks,
            name="MainInitializationThread",
            daemon=True
        )
        main_initialization_thread.start()

    logging.info("Starting Flask web server...")
    flask_server_thread = None
    try:
        from waitress import serve
        waitress_kwargs = {
            'host': config.WAITRESS_HOST,
            'port': config.WAITRESS_PORT,
            'threads': config.WAITRESS_THREADS,
            'expose_tracebacks': False,
            'send_bytes': 1,
        }

        if config.WAITRESS_CONNECTION_LIMIT:
            waitress_kwargs['connection_limit'] = config.WAITRESS_CONNECTION_LIMIT
        if config.WAITRESS_BACKLOG:
            waitress_kwargs['backlog'] = config.WAITRESS_BACKLOG
        if config.WAITRESS_CHANNEL_TIMEOUT:
            waitress_kwargs['channel_timeout'] = config.WAITRESS_CHANNEL_TIMEOUT

        flask_server_thread = threading.Thread(
            target=serve,
            args=(app,), 
            kwargs=waitress_kwargs,
            daemon=True,
            name="FlaskWaitressServer"
        )
        flask_server_thread.start()
        logging.info(f"Flask server started using waitress on {config.WAITRESS_HOST}:{config.WAITRESS_PORT} with {config.WAITRESS_THREADS} threads.")
        
        while not stop_event.is_set():
            if flask_server_thread and not flask_server_thread.is_alive():
                logging.error("Flask server thread terminated unexpectedly! Initiating shutdown.")
                stop_event.set()
                break
            
            all_daemons_or_stopped = True
            for bg_thread in background_threads_list:
                if bg_thread and bg_thread.is_alive() and not bg_thread.daemon:
                    all_daemons_or_stopped = False
                    break
            if agent_status_updater_thread and agent_status_updater_thread.is_alive() and not agent_status_updater_thread.daemon:
                all_daemons_or_stopped = False
            if main_initialization_thread and main_initialization_thread.is_alive() and not main_initialization_thread.daemon:
                all_daemons_or_stopped = False
            
            if not all_daemons_or_stopped:
                time.sleep(5) 
            else: 
                if not (flask_server_thread and flask_server_thread.is_alive()): 
                    logging.info("All critical threads seem to have completed. Initiating shutdown.")
                    stop_event.set() 
                else: 
                    time.sleep(5)

    except ImportError:
        logging.warning("Waitress not found. Using Flask development server (NOT FOR PRODUCTION).")
        app.run(host=config.WAITRESS_HOST, port=config.WAITRESS_PORT, threaded=True, debug=False) 
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Shutting down...")
    except Exception as server_startup_err:
        logging.error(f"Web server failed to start or crashed: {server_startup_err}", exc_info=True)
    finally:
        logging.info("Shutdown sequence initiated...")
        stop_event.set() 
        
        if main_initialization_thread and main_initialization_thread.is_alive():
            logging.info("Waiting for main initialization thread to complete (timeout 15s)...")
            main_initialization_thread.join(timeout=15)
        
        threads_to_join = list(background_threads_list) # Create a copy
        if agent_status_updater_thread: threads_to_join.append(agent_status_updater_thread)

        for bg_thread in threads_to_join:
            if bg_thread and bg_thread.is_alive():
                logging.info(f"Waiting for background thread {bg_thread.name} to complete (timeout 5s)...")
                bg_thread.join(timeout=5)
        
        if flask_server_thread and flask_server_thread.is_alive():
            logging.info("Flask server thread (Waitress) is a daemon; process exit will terminate it.")

        logging.info("Dockflare application shutdown complete.")
        
        exit_code = 0
        if (tunnel_state and tunnel_state.get("error")) or \
           (cloudflared_agent_state and cloudflared_agent_state.get("container_status") == "docker_unavailable") or \
           not docker_client:
            exit_code = 1
        sys.exit(exit_code)

if __name__ == '__main__':
    main_application_entrypoint()
