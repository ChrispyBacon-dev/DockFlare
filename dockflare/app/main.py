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
# app/main.py
import copy
import logging 
import threading
import time
import sys

from app import app, docker_client, tunnel_state, cloudflared_agent_state, config, log_queue

from app.core.state_manager import load_state
from app.core.tunnel_manager import (
    initialize_tunnel,
    update_cloudflared_container_status, 
    start_cloudflared_container
)
from app.core.docker_handler import docker_event_listener, process_container_start
from app.core.reconciler import cleanup_expired_rules, reconcile_state_threaded

stop_event = threading.Event()
background_threads_list = []
agent_status_updater_thread = None
main_initialization_thread = None

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
            logging.info("Starting core background task threads (Docker Listener, Cleanup Task)...")
            event_thread = threading.Thread(target=docker_event_listener, args=(stop_event,), name="DockerEventListener", daemon=True)
            threads_to_start.append(event_thread)
            
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

def perform_initial_setup_and_tasks():
    global background_threads_list 

    logging.info("Main initialization process started in background thread.")
    if not docker_client:
        logging.error("Docker client unavailable during initialization process. Critical functionalities will be affected.")
        return

    initialize_tunnel() 
    logging.info(f"Tunnel initialization attempt complete. Status: {tunnel_state.get('status_message')}, Error: {tunnel_state.get('error')}")

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
            logging.info("Checking managed cloudflared agent container status post-initialization...")
            update_cloudflared_container_status()
            if cloudflared_agent_state.get("container_status") != 'running':
                logging.info("Managed agent container not running, attempting auto-start...")
                start_cloudflared_container()
            else:
                logging.info(f"Managed agent container '{config.CLOUDFLARED_CONTAINER_NAME}' is already running.")
    
    run_all_background_tasks()

def main_application_entrypoint():
    global main_initialization_thread

    logging.info("-" * 52)
    logging.info("--- DockFlare Starting ---")
    logging.info(f"--- Version: 1.8.7 ---") 
    logging.info("-" * 52)

    load_state() 
    logging.info("Initial state loading from file complete.")

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
        flask_server_thread = threading.Thread(
            target=serve,
            args=(app,), 
            kwargs={'host': '0.0.0.0', 'port': 5000, 'threads': 10, 'expose_tracebacks': False},
            daemon=True,
            name="FlaskWaitressServer"
        )
        flask_server_thread.start()
        logging.info("Flask server started using waitress on 0.0.0.0:5000.")
        
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
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False) 
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