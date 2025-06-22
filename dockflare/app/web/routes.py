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
# app/web/routes.py
import copy
import logging
import time
import os 
import random 
import queue 
from datetime import datetime, timezone
import traceback 
import json
from app.core import access_manager
from urllib.parse import urlparse, urlunparse 
from flask import (
    Blueprint, render_template, jsonify, redirect, url_for, request, Response,
    stream_with_context, current_app
)

from app import config, docker_client, tunnel_state, cloudflared_agent_state, log_queue 
from app.core.state_manager import managed_rules, state_lock, save_state, load_state 
from app.core.tunnel_manager import (
    start_cloudflared_container,
    stop_cloudflared_container,
    update_cloudflare_config 
)
from app.core.cloudflare_api import (
    get_all_account_cloudflare_tunnels,
    get_dns_records_for_tunnel,
    create_cloudflare_dns_record, 
    delete_cloudflare_dns_record, 
    get_zone_id_from_name,
    get_zone_details_by_id
)
from app.core.access_manager import (
    check_for_tld_access_policy,
    get_cloudflare_account_email,
    delete_cloudflare_access_application,
    create_cloudflare_access_application,
    update_cloudflare_access_application,
    generate_access_app_config_hash,
    find_cloudflare_access_application_by_hostname 
)
from app.core.reconciler import reconcile_state_threaded 
from app.core.docker_handler import is_valid_hostname, is_valid_service 

bp = Blueprint('web', __name__)

def get_display_token_ui(token_value): 
    if not token_value: return "Not available"
    return f"{token_value[:5]}...{token_value[-5:]}" if len(token_value) > 10 else "Token (short)"

@bp.before_app_request 
def detect_protocol_bp():
        
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    current_app.config['PREFERRED_URL_SCHEME'] = 'https' if forwarded_proto == 'https' or request.is_secure else 'http'

@bp.after_app_request 
def add_security_headers_bp(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
        
    is_https = current_app.config.get('PREFERRED_URL_SCHEME') == 'https'
    
    csp = ("default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
           "script-src * 'unsafe-inline' 'unsafe-eval'; "
           "style-src * 'unsafe-inline'; "
           "img-src * data: blob:; font-src * data:; "
           "connect-src *; frame-src *; ")
    if is_https: csp += "upgrade-insecure-requests; "
    response.headers['Content-Security-Policy'] = csp
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if is_https: response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
    response.headers['Access-Control-Allow-Origin'] = '*' 
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
    return response

@bp.context_processor
def inject_protocol_bp():
    
    preferred_scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
    base_url = f"{preferred_scheme}://{request.host}"
    return {
        'protocol': preferred_scheme,
        'is_https': preferred_scheme == 'https',
        'base_url': base_url,
        'host': request.host,
        'request_scheme': request.scheme 
    }

@bp.route('/')
def status_page():
    rules_for_template = {}
    template_tunnel_state = {}
    template_agent_state = {}
    initialization_status = {} 
    tld_policy_exists_val = False
    account_email_for_tld_val = None
    relevant_zone_name_for_tld_policy_val = None

    with state_lock: 
        for hostname, rule in managed_rules.items():
            rule_copy = copy.deepcopy(rule)
            if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
                rule_copy["delete_at"] = rule_copy["delete_at"].replace(tzinfo=timezone.utc) if rule_copy["delete_at"].tzinfo is None else rule_copy["delete_at"].astimezone(timezone.utc)
            rules_for_template[hostname] = rule_copy
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()
        
        initialization_status = {
            "complete": template_tunnel_state.get("id") is not None or config.EXTERNAL_TUNNEL_ID,
            "in_progress": not (template_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID) and \
                           template_tunnel_state.get("status_message", "").lower().startswith("init")
        }
        
        if config.CF_ZONE_ID and docker_client:
            
            zone_details = get_zone_details_by_id(config.CF_ZONE_ID)
            if zone_details and zone_details.get("name"):
                relevant_zone_name_for_tld_policy_val = zone_details.get("name")
            
            if relevant_zone_name_for_tld_policy_val:
                tld_policy_exists_val = check_for_tld_access_policy(relevant_zone_name_for_tld_policy_val)
                if not tld_policy_exists_val: 
                    account_email_for_tld_val = get_cloudflare_account_email()
            else:
                logging.info("Relevant zone name for TLD policy check (from CF_ZONE_ID) could not be determined.")

    display_token_val = get_display_token_ui(template_tunnel_state.get("token"))
    all_account_tunnels_list = get_all_account_cloudflare_tunnels()

    return render_template('status_page.html',
                        tunnel_state=template_tunnel_state,
                        agent_state=template_agent_state,
                        initialization=initialization_status,
                        display_token=display_token_val,
                        cloudflared_container_name=config.CLOUDFLARED_CONTAINER_NAME,
                        docker_available=docker_client is not None,
                        external_cloudflared=config.USE_EXTERNAL_CLOUDFLARED,
                        external_tunnel_id=config.EXTERNAL_TUNNEL_ID,
                        rules=rules_for_template,
                        all_account_tunnels=all_account_tunnels_list,
                        CF_ACCOUNT_ID_CONFIGURED=bool(config.CF_ACCOUNT_ID), 
                        ACCOUNT_ID_FOR_DISPLAY=config.CF_ACCOUNT_ID if config.CF_ACCOUNT_ID else "Not Configured",
                        relevant_zone_name_for_tld_policy=relevant_zone_name_for_tld_policy_val,
                        tld_policy_exists=tld_policy_exists_val,
                        account_email_for_tld=account_email_for_tld_val,
                        CF_ZONE_ID_CONFIGURED=bool(config.CF_ZONE_ID)
                        )

@bp.route('/ui_update_access_policy/<path:hostname>', methods=['POST'])
def ui_update_access_policy(hostname):
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: UI Policy Update - Docker client unavailable."
        return redirect(url_for('web.status_page')) 

    new_policy_type = request.form.get('access_policy_type')
    auth_email = request.form.get('auth_email', '').strip()
    action_status_message = f"Processing UI policy update for {hostname}..."
    state_changed_locally = False 

    with state_lock:
        current_rule = managed_rules.get(hostname)
        if not current_rule:
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {hostname} not found."
            return redirect(url_for('web.status_page'))

        current_access_app_id = current_rule.get("access_app_id")
        
        desired_session_duration = request.form.get("session_duration", current_rule.get("access_session_duration", "24h"))
        
        form_app_launcher_visible = request.form.get("app_launcher_visible") 
        if form_app_launcher_visible is not None:
            desired_app_launcher_visible = form_app_launcher_visible.lower() in ["true", "on", "1", "yes"]
        else:
            desired_app_launcher_visible = current_rule.get("access_app_launcher_visible", False)

        desired_allowed_idps_str = request.form.get("allowed_idps", current_rule.get("access_allowed_idps_str")) 
        
        form_auto_redirect = request.form.get("auto_redirect") 
        if form_auto_redirect is not None:
            desired_auto_redirect = form_auto_redirect.lower() in ["true", "on", "1", "yes"]
        else:
            desired_auto_redirect = current_rule.get("access_auto_redirect", False)
        
        desired_app_name = f"DockFlare-{hostname}"
        
        cf_access_policies = []
        final_policy_type_for_state = new_policy_type
        custom_rules_for_hash = None 
        operation_successful = False

        if new_policy_type == "none" or new_policy_type == "public_no_policy":
            if current_access_app_id:
                logging.info(f"UI: Setting {hostname} to public. Deleting Access App {current_access_app_id}.")
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = None 
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: {hostname} Access App deleted (set to public)."
                else:
                    action_status_message = f"Error: Failed to delete Access App for {hostname}."
            else: # No existing app_id in state
                if current_rule.get("access_policy_type") is not None: 
                    current_rule["access_policy_type"] = None
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True 
                action_status_message = f"Info: {hostname} set to public (no existing Access App in state)."
            final_policy_type_for_state = None 

        elif new_policy_type == "default_tld":
            if current_access_app_id:
                logging.info(f"UI: Setting {hostname} to default_tld. Deleting Access App {current_access_app_id}.")
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: {hostname} Access App deleted (set to default_tld)."
                else:
                    action_status_message = f"Error: Failed to delete Access App for {hostname} for default_tld."
            else: # No existing app_id in state
                if current_rule.get("access_policy_type") != "default_tld":
                    current_rule["access_app_id"] = None 
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
                action_status_message = f"Info: {hostname} set to default_tld (no existing Access App in state)."
            final_policy_type_for_state = "default_tld"
        
        elif new_policy_type == "bypass":
            cf_access_policies = [{"name": "UI Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            custom_rules_for_hash = json.dumps(cf_access_policies) 
            final_policy_type_for_state = "bypass"
        
        elif new_policy_type == "authenticate_email": 
            if not auth_email:
                cloudflared_agent_state["last_action_status"] = f"Error: Email address required for 'authenticate_email' policy for {hostname}."
                return redirect(url_for('web.status_page'))
            cf_access_policies = [
                {"name": f"UI Allow Email {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
                {"name": "UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
            ]
            custom_rules_for_hash = json.dumps(cf_access_policies)
            final_policy_type_for_state = "authenticate_email"
                
        if new_policy_type in ["bypass", "authenticate_email"]: 
            if not cf_access_policies: 
                logging.error(f"UI: No policies defined for {hostname} with type {new_policy_type} but expected. Aborting.")
                cloudflared_agent_state["last_action_status"] = f"Error: Internal - No policies for {new_policy_type}."
                return redirect(url_for('web.status_page'))
            
            new_config_hash = generate_access_app_config_hash(
                final_policy_type_for_state, 
                desired_session_duration, 
                desired_app_launcher_visible,       
                desired_allowed_idps_str,           
                desired_auto_redirect,              
                custom_access_rules_str=custom_rules_for_hash
            )
            allowed_idps_list_for_app = [idp.strip() for idp in desired_allowed_idps_str.split(',') if idp.strip()] if desired_allowed_idps_str else None

            effective_app_id_for_operation = current_access_app_id
            if not effective_app_id_for_operation:
                logging.info(f"UI Update: No local Access App ID for {hostname}. Checking Cloudflare API...")
                existing_cf_app = access_manager.find_cloudflare_access_application_by_hostname(hostname)
                if existing_cf_app and existing_cf_app.get("id"):
                    effective_app_id_for_operation = existing_cf_app.get("id")
                    logging.info(f"UI Update: Found existing Access App ID '{effective_app_id_for_operation}' on Cloudflare for {hostname}.")
                    current_rule["access_app_id"] = effective_app_id_for_operation 
                    state_changed_locally = True


            if effective_app_id_for_operation:
                if current_rule.get("access_policy_type") != final_policy_type_for_state or \
                   current_rule.get("access_app_config_hash") != new_config_hash or \
                   current_rule.get("access_app_id") != effective_app_id_for_operation: 

                    logging.info(f"UI: Attempting to update Access App. ID: {effective_app_id_for_operation}, Target Name: {desired_app_name}, Target Policy: {final_policy_type_for_state}")
                    updated_app = update_cloudflare_access_application(
                        effective_app_id_for_operation, hostname, desired_app_name,
                        desired_session_duration, desired_app_launcher_visible,
                        [hostname], cf_access_policies, allowed_idps_list_for_app, desired_auto_redirect
                    )
                    if updated_app:
                        current_rule["access_app_id"] = updated_app.get("id") 
                        current_rule["access_policy_type"] = final_policy_type_for_state
                        current_rule["access_app_config_hash"] = new_config_hash
                        state_changed_locally = True
                        operation_successful = True
                        action_status_message = f"Success: Access Policy for {hostname} updated to {final_policy_type_for_state}."
                    else:
                        action_status_message = f"Error: Failed to update Access App for {hostname}."
                else:
                    operation_successful = True 
                    action_status_message = f"Info: Access Policy for {hostname} already matched UI selection. No API update needed."
            else: 
                logging.info(f"UI: Attempting to create Access App. Target Name: {desired_app_name}, Target Policy: {final_policy_type_for_state}")
                created_app = create_cloudflare_access_application(
                    hostname, desired_app_name,
                    desired_session_duration, desired_app_launcher_visible,
                    [hostname], cf_access_policies, allowed_idps_list_for_app, desired_auto_redirect
                )
                if created_app and created_app.get("id"):
                    current_rule["access_app_id"] = created_app.get("id")
                    current_rule["access_policy_type"] = final_policy_type_for_state
                    current_rule["access_app_config_hash"] = new_config_hash
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: Access Policy for {hostname} created as {final_policy_type_for_state}."
                else:
                    action_status_message = f"Error: Failed to create Access App for {hostname}."
        
        if operation_successful:
            if not current_rule.get("access_policy_ui_override", False):
                 logging.info(f"Access policy for {hostname} is now UI-managed due to UI interaction.")
            current_rule["access_policy_ui_override"] = True
            if not current_rule.get("access_policy_ui_override_previous_state", True): 
                 state_changed_locally = True
        else:
            logging.warning(f"UI operation for {hostname} failed or no effective change made.")

        if state_changed_locally:
            save_state()
    
    cloudflared_agent_state["last_action_status"] = action_status_message
    return redirect(url_for('web.status_page'))

@bp.route('/revert_access_policy_to_labels/<path:hostname>', methods=['POST'])
def revert_access_policy_to_labels(hostname):
    
    if not docker_client: # ...
        return redirect(url_for('web.status_page'))
    
    action_status_message = f"Attempting to revert Access Policy for '{hostname}' to label configuration..."
    app_id_to_delete_if_any = None
    state_changed_for_revert = False

    with state_lock:
        current_rule = managed_rules.get(hostname)
        if not current_rule: # ...
            return redirect(url_for('web.status_page'))
        if not current_rule.get("access_policy_ui_override", False): # ...
            return redirect(url_for('web.status_page'))
        
        app_id_to_delete_if_any = current_rule.get("access_app_id")
        current_rule["access_policy_ui_override"] = False
        # ...
        state_changed_for_revert = True
        if state_changed_for_revert: save_state()

    if app_id_to_delete_if_any:
        if delete_cloudflare_access_application(app_id_to_delete_if_any): 
            pass # ...
    
    reconcile_state_threaded() 
    action_status_message += " Reconciliation triggered."
    cloudflared_agent_state["last_action_status"] = action_status_message
    return redirect(url_for('web.status_page'))

@bp.route('/tunnel-dns-records/<tunnel_id>')
def tunnel_dns_records(tunnel_id):
    if not tunnel_id: return jsonify({"error": "Tunnel ID is required"}), 400
    all_found_dns_records = []
    zone_ids_to_scan = set()
    if config.CF_ZONE_ID: zone_ids_to_scan.add(config.CF_ZONE_ID)
    for zone_name in config.TUNNEL_DNS_SCAN_ZONE_NAMES:
        resolved_zone_id = get_zone_id_from_name(zone_name) 
        if resolved_zone_id: zone_ids_to_scan.add(resolved_zone_id)
    
    if not zone_ids_to_scan:
        return jsonify({"dns_records": [], "message": "No zones configured or resolved for DNS scan."})

    for z_id in zone_ids_to_scan:
        records_in_zone = get_dns_records_for_tunnel(z_id, tunnel_id) 
        if records_in_zone: all_found_dns_records.extend(records_in_zone)
    
    all_found_dns_records.sort(key=lambda r: r.get("name", "").lower())
    return jsonify({"dns_records": all_found_dns_records})

@bp.route('/ping')
def ping():
    return jsonify({ "status": "ok", "timestamp": int(time.time()), "version": "1.7.1", 
                     "protocol": request.environ.get('wsgi.url_scheme', 'unknown')})

@bp.route('/debug')
def debug_info():
    try:
        headers = {k: v for k, v in request.headers.items()}
        return jsonify({
            "request": { "scheme": request.scheme, "is_secure": request.is_secure, "host": request.host, 
                         "path": request.path, "url": request.url, "headers": headers },
            "environment": { "wsgi.url_scheme": request.environ.get('wsgi.url_scheme'),
                             "HTTP_X_FORWARDED_PROTO": request.environ.get('HTTP_X_FORWARDED_PROTO') },
            "timestamp": int(time.time())
        })
    except Exception as e:
        return jsonify({ "error": str(e), "traceback": traceback.format_exc() }), 500

@bp.route('/reconciliation-status')
def reconciliation_status_route(): 
    
    reconciliation_info_data = getattr(current_app, 'reconciliation_info', {})
    return jsonify({
        "in_progress": reconciliation_info_data.get("in_progress", False),
        "progress": reconciliation_info_data.get("progress", 0),
        "total_items": reconciliation_info_data.get("total_items", 0),
        "processed_items": reconciliation_info_data.get("processed_items", 0),
        "status": reconciliation_info_data.get("status", "Not started")
    })

@bp.route('/start-tunnel', methods=['POST'])
def start_tunnel_route(): 
    start_cloudflared_container() 
    time.sleep(1)
    return redirect(url_for('web.status_page'))

@bp.route('/stop-tunnel', methods=['POST'])
def stop_tunnel_route(): 
    stop_cloudflared_container() 
    time.sleep(1)
    return redirect(url_for('web.status_page'))

@bp.route('/force_delete_rule/<path:hostname>', methods=['POST']) 
def force_delete_rule_route(hostname): 
    
    rule_removed_from_state = False; dns_delete_success = False; access_app_delete_success = False
    zone_id_for_delete = None; access_app_id_for_delete = None
    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details: # ...
            zone_id_for_delete = rule_details.get("zone_id")
            access_app_id_for_delete = rule_details.get("access_app_id")
    # ...
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if zone_id_for_delete and effective_tunnel_id:
        dns_delete_success = delete_cloudflare_dns_record(zone_id_for_delete, hostname, effective_tunnel_id)
    if access_app_id_for_delete:
        access_app_delete_success = delete_cloudflare_access_application(access_app_id_for_delete)
    # ...
    with state_lock:
        if hostname in managed_rules: del managed_rules[hostname]; rule_removed_from_state = True; save_state()
    # ...
    if rule_removed_from_state and not config.USE_EXTERNAL_CLOUDFLARED:
        if update_cloudflare_config(): pass # ...
    # ...
    return redirect(url_for('web.status_page'))

@bp.route('/stream-logs')
def stream_logs_route(): 
    client_id = f"client-{random.randint(1000, 9999)}"
    logging.info(f"Log stream client {client_id} connected.")
    def event_stream():
        try:
            yield f"data: --- Log stream connected (client {client_id}) ---\n\n"
            last_heartbeat = time.time()
            while True:
                try:
                    log_entry = log_queue.get(timeout=0.25) 
                    yield f"data: {log_entry}\n\n"
                    last_heartbeat = time.time() 
                except queue.Empty:
                    if time.time() - last_heartbeat > 2: 
                        yield f": keepalive\n\n" 
                        last_heartbeat = time.time()
                    time.sleep(0.1) 
        except GeneratorExit:
            logging.info(f"Log stream client {client_id} disconnected.")
        except Exception as e_stream:
            logging.error(f"Error in log stream for {client_id}: {e_stream}", exc_info=True)
        finally:
            logging.info(f"Log stream for client {client_id} ended.")
            
    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'; response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response

@bp.route('/ui/manual-rules/add', methods=['POST'])
def ui_add_manual_rule_route():
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
        return redirect(url_for('web.status_page'))
    
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if not effective_tunnel_id:
        cloudflared_agent_state["last_action_status"] = "Error: Tunnel not initialized or essential Tunnel ID missing."
        return redirect(url_for('web.status_page'))

    subdomain_input = request.form.get('manual_subdomain', '').strip()
    domain_name_input = request.form.get('manual_domain_name', '').strip()
    path_input = request.form.get('manual_path', '').strip()
    service_type_input = request.form.get('manual_service_type', '').strip().lower()
    service_address_input = request.form.get('manual_service_address', '').strip()
    zone_name_override_input = request.form.get('manual_zone_name_override', '').strip()
    no_tls_verify = request.form.get('manual_no_tls_verify') == 'on'
    origin_server_name_input = request.form.get('manual_origin_server_name', '').strip()
    manual_access_policy_type = request.form.get('manual_access_policy_type', 'none').strip().lower()
    manual_auth_email = request.form.get('manual_auth_email', '').strip()

    if not domain_name_input or not service_type_input: 
        cloudflared_agent_state["last_action_status"] = "Error: Domain Name and Service Type are required for manual rule."
        return redirect(url_for('web.status_page'))
    
    if service_type_input not in ["http_status", "bastion"] and not service_address_input:
        cloudflared_agent_state["last_action_status"] = f"Error: Service Address is required for type '{service_type_input.upper()}'."
        return redirect(url_for('web.status_page'))
    
    if manual_access_policy_type == "authenticate_email" and not manual_auth_email:
        cloudflared_agent_state["last_action_status"] = "Error: Allowed Email(s) required for 'Authenticate by Email' policy."
        return redirect(url_for('web.status_page'))

    if subdomain_input:
        full_hostname = f"{subdomain_input}.{domain_name_input}"
    else:
        full_hostname = domain_name_input
    
    if not is_valid_hostname(full_hostname): 
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed hostname '{full_hostname}' is invalid."
        return redirect(url_for('web.status_page'))
    
    processed_path = None
    if path_input:
        processed_path = path_input.strip()
        if not processed_path.startswith('/'):
            cloudflared_agent_state["last_action_status"] = f"Error: Path '{processed_path}' must start with a '/'."
            return redirect(url_for('web.status_page'))
        if len(processed_path) > 1 and processed_path.endswith('/'):
            processed_path = processed_path.rstrip('/')

    key_for_managed_rules = f"{full_hostname}{'|' + processed_path if processed_path else ''}"

    processed_service_for_cf = ""
    if service_type_input in ["http", "https"]:
        if ":" not in service_address_input and "." not in service_address_input and service_address_input != "localhost": 
             cloudflared_agent_state["last_action_status"] = f"Error: For HTTP/S, address '{service_address_input}' should be host:port or a resolvable hostname."
             return redirect(url_for('web.status_page'))
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input in ["tcp", "ssh", "rdp"]:
        if ":" not in service_address_input: 
            cloudflared_agent_state["last_action_status"] = f"Error: For {service_type_input.upper()}, address '{service_address_input}' must be in host:port format."
            return redirect(url_for('web.status_page'))
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input == "http_status":
        if not service_address_input.isdigit() or not (100 <= int(service_address_input) <= 599):
            cloudflared_agent_state["last_action_status"] = f"Error: Invalid HTTP status code '{service_address_input}'. Must be 100-599."
            return redirect(url_for('web.status_page'))
        processed_service_for_cf = f"http_status:{service_address_input}"
    else:
        cloudflared_agent_state["last_action_status"] = f"Error: Unsupported service type '{service_type_input}' submitted."
        return redirect(url_for('web.status_page'))

    if not is_valid_service(processed_service_for_cf): 
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed service string '{processed_service_for_cf}' is invalid."
        return redirect(url_for('web.status_page'))
    
    target_zone_id = None
    zone_name_to_lookup = None
    if zone_name_override_input:
        zone_name_to_lookup = zone_name_override_input
    else: 
        parts = domain_name_input.split('.')
        if len(parts) >= 2:
            potential_zone = f"{parts[-2]}.{parts[-1]}"
            zone_name_to_lookup = potential_zone
        else: 
            zone_name_to_lookup = None 

    if zone_name_to_lookup:
        target_zone_id = get_zone_id_from_name(zone_name_to_lookup)
        if not target_zone_id and config.CF_ZONE_ID: 
            logging.info(f"Could not find zone for '{zone_name_to_lookup}', trying default CF_ZONE_ID.")
            target_zone_id = config.CF_ZONE_ID 
        elif not target_zone_id:
            cloudflared_agent_state["last_action_status"] = f"Error: Could not find Zone ID for '{zone_name_to_lookup}' and no default CF_ZONE_ID to fallback."
            return redirect(url_for('web.status_page'))
    elif config.CF_ZONE_ID:
        target_zone_id = config.CF_ZONE_ID
        logging.info(f"Using default CF_ZONE_ID as no specific zone name was provided or derivable.")
    else:
        cloudflared_agent_state["last_action_status"] = "Error: Cloudflare Zone Name/ID is required."
        return redirect(url_for('web.status_page'))

    access_app_created_or_updated_id = None
    access_app_final_config_hash = None
    cf_access_policies_for_app = [] 
    custom_rules_for_hash_str = None 
    desired_session_duration = "24h" 
    desired_app_launcher_visible = False 
    desired_allowed_idps_str = None 
    desired_auto_redirect = False
    desired_app_name = f"DockFlare-{full_hostname}" 

    if manual_access_policy_type == "bypass":
        cf_access_policies_for_app = [{"name": "UI Manual Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
        custom_rules_for_hash_str = json.dumps(cf_access_policies_for_app)
    elif manual_access_policy_type == "authenticate_email":
        cf_access_policies_for_app = [
            {"name": f"UI Manual Allow Email {manual_auth_email}", "decision": "allow", "include": [{"email": {"email": manual_auth_email}}]},
            {"name": "UI Manual Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
        ]
        custom_rules_for_hash_str = json.dumps(cf_access_policies_for_app)
    
    if manual_access_policy_type in ["bypass", "authenticate_email"]:
        existing_cf_app = find_cloudflare_access_application_by_hostname(full_hostname)
        if existing_cf_app and existing_cf_app.get("id"):
            logging.info(f"Manual Add: Found existing Access App {existing_cf_app.get('id')} for {full_hostname}. Will attempt to update it.")
            access_app_created_or_updated_id = existing_cf_app.get("id")
            allowed_idps_list = [idp.strip() for idp in desired_allowed_idps_str.split(',') if idp.strip()] if desired_allowed_idps_str else None
            updated_app = update_cloudflare_access_application(
                access_app_created_or_updated_id, full_hostname, desired_app_name,
                desired_session_duration, desired_app_launcher_visible,
                [full_hostname], cf_access_policies_for_app, allowed_idps_list, desired_auto_redirect
            )
            if updated_app:
                access_app_created_or_updated_id = updated_app.get("id")
                access_app_final_config_hash = generate_access_app_config_hash(
                    manual_access_policy_type, desired_session_duration, desired_app_launcher_visible,
                    desired_allowed_idps_str, desired_auto_redirect, custom_access_rules_str=custom_rules_for_hash_str
                )
            else:
                logging.error(f"Failed to update existing Access App for manual rule {full_hostname}")
                access_app_created_or_updated_id = None 
        else:
            created_app = create_cloudflare_access_application(
                full_hostname, desired_app_name,
                desired_session_duration, desired_app_launcher_visible,
                [full_hostname], cf_access_policies_for_app, 
                [idp.strip() for idp in desired_allowed_idps_str.split(',') if idp.strip()] if desired_allowed_idps_str else None, 
                desired_auto_redirect
            )
            if created_app and created_app.get("id"):
                access_app_created_or_updated_id = created_app.get("id")
                access_app_final_config_hash = generate_access_app_config_hash(
                    manual_access_policy_type, desired_session_duration, desired_app_launcher_visible,
                    desired_allowed_idps_str, desired_auto_redirect, custom_access_rules_str=custom_rules_for_hash_str
                )
            else:
                logging.error(f"Failed to create Access App for manual rule {full_hostname}")

    with state_lock:
        existing_rule_details = managed_rules.get(key_for_managed_rules)
        if existing_rule_details and existing_rule_details.get("source", "docker") == "docker":
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {full_hostname} (Path: {processed_path or '(root)'}) is Docker-managed."
            return redirect(url_for('web.status_page'))
        
        log_action = "Adding new" if not existing_rule_details else "Updating existing"
        logging.info(f"{log_action} manual rule for Key: {key_for_managed_rules} (FQDN: {full_hostname}, Path: {processed_path or '(root)'}) with service {processed_service_for_cf}")
        
        managed_rules[key_for_managed_rules] = { 
            "service": processed_service_for_cf,
            "path": processed_path, 
            "hostname_for_dns": full_hostname, 
            "container_id": None, 
            "status": "active",
            "delete_at": None,
            "zone_id": target_zone_id, 
            "no_tls_verify": no_tls_verify,
            "origin_server_name": origin_server_name_input if origin_server_name_input else None,
            "access_app_id": access_app_created_or_updated_id if manual_access_policy_type in ["bypass", "authenticate_email"] \
                             else (existing_rule_details.get("access_app_id") if existing_rule_details else None),
            "access_policy_type": manual_access_policy_type if manual_access_policy_type != "none" else None,
            "access_app_config_hash": access_app_final_config_hash if manual_access_policy_type in ["bypass", "authenticate_email"] \
                                      else (existing_rule_details.get("access_app_config_hash") if existing_rule_details else None),
            "auth_email": manual_auth_email if manual_access_policy_type == "authenticate_email" else (existing_rule_details.get("auth_email") if existing_rule_details else None),
            "access_policy_ui_override": True if manual_access_policy_type != "none" else (existing_rule_details.get("access_policy_ui_override", False) if existing_rule_details else False),
            "source": "manual"
        }
        save_state() 
        
    if update_cloudflare_config(): 
        if create_cloudflare_dns_record(target_zone_id, full_hostname, effective_tunnel_id):
            cloudflared_agent_state["last_action_status"] = f"Success: Manual rule for {full_hostname} (Path: {processed_path if processed_path else '(root)'}) added/updated. Policy: {manual_access_policy_type.upper()}."
        else:
            cloudflared_agent_state["last_action_status"] = f"Warning: Manual rule for {full_hostname} (Path: {processed_path if processed_path else '(root)'}) added/updated. Policy: {manual_access_policy_type.upper()}. DNS creation FAILED."
    else:
        cloudflared_agent_state["last_action_status"] = f"Error: Failed to update Cloudflare tunnel config for manual rule {full_hostname} (Path: {processed_path if processed_path else '(root)'})."

    return redirect(url_for('web.status_page'))

@bp.route('/ui/manual-rules/delete/<path:rule_key_from_url>', methods=['POST'])
def ui_delete_manual_rule_route(rule_key_from_url):
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to delete manual rule. Docker client unavailable."
        return redirect(url_for('web.status_page'))
    
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if not effective_tunnel_id: 
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to delete manual rule. Tunnel not initialized or ID missing."
        return redirect(url_for('web.status_page'))

    rule_key_in_state = rule_key_from_url 
    logging.info(f"UI request: Delete manual rule for key: {rule_key_in_state}")
    
    zone_id_for_delete = None
    access_app_id_for_delete = None
    hostname_for_dns_operations = None 
    rule_existed_as_manual_and_deleted = False 

    with state_lock:
        rule_details = managed_rules.get(rule_key_in_state)
        if rule_details and rule_details.get("source") == "manual":
            logging.info(f"Found manual rule for {rule_key_in_state} to delete. Details: {rule_details}")
            zone_id_for_delete = rule_details.get("zone_id")
            access_app_id_for_delete = rule_details.get("access_app_id")
            hostname_for_dns_operations = rule_details.get("hostname_for_dns") 
            
            del managed_rules[rule_key_in_state]
            save_state() 
            rule_existed_as_manual_and_deleted = True
            action_status_message = f"Manual rule {rule_key_in_state} removed from local state." 
        elif rule_details:
            action_status_message = f"Error: Rule for {rule_key_in_state} is not a manual rule. Cannot delete via this action."
            cloudflared_agent_state["last_action_status"] = action_status_message
            return redirect(url_for('web.status_page'))
        else:
            action_status_message = f"Info: Manual rule for {rule_key_in_state} not found to delete."
            cloudflared_agent_state["last_action_status"] = action_status_message
            return redirect(url_for('web.status_page'))

    if rule_existed_as_manual_and_deleted:
        dns_deleted_successfully = False
        access_app_deleted_successfully = False
        
        should_delete_dns_record = True
        if hostname_for_dns_operations: 
            with state_lock: 
                for other_key, other_rule in managed_rules.items():
                    if other_rule.get("hostname_for_dns") == hostname_for_dns_operations:
                        should_delete_dns_record = False 
                        logging.info(f"DNS for {hostname_for_dns_operations} will NOT be deleted as other rules still use it (e.g., {other_key}).")
                        break
        else:
            should_delete_dns_record = False 
            logging.warning(f"Cannot perform DNS deletion for rule {rule_key_in_state} as 'hostname_for_dns' was not found in rule details.")

        if should_delete_dns_record and zone_id_for_delete and hostname_for_dns_operations: 
            logging.info(f"Attempting DNS delete for {hostname_for_dns_operations} (from rule {rule_key_in_state}) in zone {zone_id_for_delete}")
            if delete_cloudflare_dns_record(zone_id_for_delete, hostname_for_dns_operations, effective_tunnel_id):
                dns_deleted_successfully = True
                logging.info(f"DNS record for {hostname_for_dns_operations} deleted successfully.")
            else:
                logging.error(f"Failed to delete DNS record for {hostname_for_dns_operations}.")
        elif not should_delete_dns_record:
            dns_deleted_successfully = True 
            if hostname_for_dns_operations: 
                 logging.info(f"DNS deletion for {hostname_for_dns_operations} skipped.")

        if access_app_id_for_delete: 
            logging.info(f"Attempting Access App delete for manual rule {rule_key_in_state}, App ID {access_app_id_for_delete}")
            is_app_id_shared = False
            with state_lock: # Re-acquire lock
                for other_key, other_rule in managed_rules.items():
                    if other_rule.get("access_app_id") == access_app_id_for_delete:
                        is_app_id_shared = True
                        logging.info(f"Access App ID {access_app_id_for_delete} is still in use by rule {other_key}. Will not delete.")
                        break
            
            if not is_app_id_shared:
                if delete_cloudflare_access_application(access_app_id_for_delete):
                    access_app_deleted_successfully = True
                    logging.info(f"Access App ID {access_app_id_for_delete} deleted successfully.")
                else:
                    logging.error(f"Failed to delete Access App ID {access_app_id_for_delete}.")
            else:
                access_app_deleted_successfully = True 
        else:
            logging.info(f"No Access App ID found for manual rule {rule_key_in_state}, skipping Access App deletion.")
            access_app_deleted_successfully = True 
        
        if update_cloudflare_config(): 
            action_status_message = f"Success: Manual rule {rule_key_in_state} deleted. DNS: {'OK' if dns_deleted_successfully else 'Fail/Skip'}. AccessApp: {'OK' if access_app_deleted_successfully else 'Fail/Skip'}. Tunnel config updated."
        else:
            action_status_message = f"Warning: Manual rule {rule_key_in_state} deleted. DNS/AccessApp processed. Tunnel config update FAILED."
        
        cloudflared_agent_state["last_action_status"] = action_status_message
    return redirect(url_for('web.status_page'))

@bp.route('/ui/manual-rules/edit', methods=['POST'])
def ui_edit_manual_rule_route():
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
        return redirect(url_for('web.status_page'))
    
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if not effective_tunnel_id:
        cloudflared_agent_state["last_action_status"] = "Error: Tunnel not initialized or essential Tunnel ID missing."
        return redirect(url_for('web.status_page'))
        
    original_rule_key = request.form.get('original_rule_key', '').strip()
    if not original_rule_key:
        cloudflared_agent_state["last_action_status"] = "Error: Original rule key was missing from the edit request."
        return redirect(url_for('web.status_page'))

    original_rule_details = None
    with state_lock:
        original_rule_details = managed_rules.get(original_rule_key)

    if not original_rule_details or original_rule_details.get("source") != "manual":
        cloudflared_agent_state["last_action_status"] = f"Error: Could not find original manual rule '{original_rule_key}' to edit."
        return redirect(url_for('web.status_page'))

    old_zone_id = original_rule_details.get("zone_id")
    old_access_app_id = original_rule_details.get("access_app_id")
    old_hostname_for_dns = original_rule_details.get("hostname_for_dns")

    subdomain_input = request.form.get('manual_subdomain', '').strip()
    domain_name_input = request.form.get('manual_domain_name', '').strip()
    path_input = request.form.get('manual_path', '').strip()
    service_type_input = request.form.get('manual_service_type', '').strip().lower()
    service_address_input = request.form.get('manual_service_address', '').strip()
    zone_name_override_input = request.form.get('manual_zone_name_override', '').strip()
    no_tls_verify = request.form.get('manual_no_tls_verify') == 'on'
    origin_server_name_input = request.form.get('manual_origin_server_name', '').strip()
    manual_access_policy_type = request.form.get('manual_access_policy_type', 'none').strip().lower()
    manual_auth_email = request.form.get('manual_auth_email', '').strip()
    
    if not domain_name_input or not service_type_input:
        cloudflared_agent_state["last_action_status"] = "Error: Domain Name and Service Type are required."
        return redirect(url_for('web.status_page'))
    if service_type_input not in ["http_status", "bastion"] and not service_address_input:
        cloudflared_agent_state["last_action_status"] = f"Error: Service Address is required for type '{service_type_input.upper()}'."
        return redirect(url_for('web.status_page'))
    if manual_access_policy_type == "authenticate_email" and not manual_auth_email:
        cloudflared_agent_state["last_action_status"] = "Error: Allowed Email(s) required for 'Authenticate by Email' policy."
        return redirect(url_for('web.status_page'))

    full_hostname = f"{subdomain_input}.{domain_name_input}" if subdomain_input else domain_name_input
    if not is_valid_hostname(full_hostname):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed hostname '{full_hostname}' is invalid."
        return redirect(url_for('web.status_page'))
    
    processed_path = path_input.strip() if path_input else None
    if processed_path and not processed_path.startswith('/'):
        processed_path = '/' + processed_path
    
    new_rule_key = f"{full_hostname}{'|' + processed_path if processed_path else ''}"
    
    processed_service_for_cf = ""
    if service_type_input in ["http", "https", "tcp", "ssh", "rdp"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input == "http_status":
        processed_service_for_cf = f"http_status:{service_address_input}"

    if not is_valid_service(processed_service_for_cf):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed service string '{processed_service_for_cf}' is invalid."
        return redirect(url_for('web.status_page'))

    zone_name_to_lookup = zone_name_override_input or '.'.join(domain_name_input.split('.')[-2:])
    target_zone_id = get_zone_id_from_name(zone_name_to_lookup) or config.CF_ZONE_ID
    if not target_zone_id:
        cloudflared_agent_state["last_action_status"] = f"Error: Could not determine Zone ID for '{zone_name_to_lookup}'."
        return redirect(url_for('web.status_page'))
        
    access_app_created_or_updated_id = None
    access_app_final_config_hash = None
    cf_access_policies_for_app = [] 
    
    if manual_access_policy_type in ["bypass", "authenticate_email"]:
        if manual_access_policy_type == "bypass":
            cf_access_policies_for_app = [{"name": "UI Manual Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
        else: 
            cf_access_policies_for_app = [
                {"name": f"UI Manual Allow Email {manual_auth_email}", "decision": "allow", "include": [{"email": {"email": manual_auth_email}}]},
                {"name": "UI Manual Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
            ]
        
        app_id_to_update = old_access_app_id if old_hostname_for_dns == full_hostname else None
        
        if app_id_to_update:
            logging.info(f"Manual Edit: Updating existing Access App {app_id_to_update} for {full_hostname}")
            updated_app = update_cloudflare_access_application(app_id_to_update, full_hostname, f"DockFlare-{full_hostname}", "24h", False, [full_hostname], cf_access_policies_for_app, None, False)
            if updated_app: access_app_created_or_updated_id = updated_app.get("id")
        else:
            logging.info(f"Manual Edit: Creating new Access App for {full_hostname}")
            created_app = create_cloudflare_access_application(full_hostname, f"DockFlare-{full_hostname}", "24h", False, [full_hostname], cf_access_policies_for_app, None, False)
            if created_app: access_app_created_or_updated_id = created_app.get("id")
            
        if access_app_created_or_updated_id:
             access_app_final_config_hash = generate_access_app_config_hash(manual_access_policy_type, "24h", False, None, False, custom_access_rules_str=json.dumps(cf_access_policies_for_app))

    with state_lock:
        if new_rule_key != original_rule_key and managed_rules.get(new_rule_key, {}).get("source") == "docker":
            cloudflared_agent_state["last_action_status"] = f"Error: New rule for {full_hostname} conflicts with an existing Docker-managed rule."
            return redirect(url_for('web.status_page'))

        if original_rule_key in managed_rules:
            del managed_rules[original_rule_key]

        managed_rules[new_rule_key] = { 
            "service": processed_service_for_cf, "path": processed_path, "hostname_for_dns": full_hostname, 
            "container_id": None, "status": "active", "delete_at": None, "zone_id": target_zone_id, 
            "no_tls_verify": no_tls_verify, "origin_server_name": origin_server_name_input or None,
            "access_app_id": access_app_created_or_updated_id, "access_policy_type": manual_access_policy_type if manual_access_policy_type != "none" else None,
            "access_app_config_hash": access_app_final_config_hash, "auth_email": manual_auth_email if manual_access_policy_type == "authenticate_email" else None,
            "access_policy_ui_override": True if manual_access_policy_type != "none" else False, "source": "manual"
        }
        save_state()

    if old_hostname_for_dns != full_hostname:
        with state_lock:
            is_old_hostname_still_used = any(r.get("hostname_for_dns") == old_hostname_for_dns for r in managed_rules.values())
        if not is_old_hostname_still_used:
            logging.info(f"Old hostname '{old_hostname_for_dns}' no longer in use. Deleting its DNS record.")
            delete_cloudflare_dns_record(old_zone_id, old_hostname_for_dns, effective_tunnel_id)
    
    if old_access_app_id and old_access_app_id != access_app_created_or_updated_id:
        with state_lock:
            is_old_app_id_still_used = any(r.get("access_app_id") == old_access_app_id for r in managed_rules.values())
        if not is_old_app_id_still_used:
            logging.info(f"Old Access App ID '{old_access_app_id}' no longer in use. Deleting it.")
            delete_cloudflare_access_application(old_access_app_id)

    if update_cloudflare_config():
        if create_cloudflare_dns_record(target_zone_id, full_hostname, effective_tunnel_id):
            cloudflared_agent_state["last_action_status"] = f"Success: Manual rule for {full_hostname} updated."
        else:
            cloudflared_agent_state["last_action_status"] = f"Warning: Manual rule for {full_hostname} updated, but DNS creation failed."
    else:
        cloudflared_agent_state["last_action_status"] = f"Error: Failed to update Cloudflare tunnel config for manual rule {full_hostname}."

    return redirect(url_for('web.status_page'))

@bp.route('/cloudflare-ping')
def cloudflare_ping_route(): 
    try:
        cf_headers = {k: v for k, v in request.headers.items() if k.lower().startswith('cf-')}
        visitor_data = json.loads(request.headers.get('Cf-Visitor', '{}'))
        return jsonify({
            "status": "ok", "timestamp": int(time.time()),
            "cloudflare": { "connecting_ip": request.headers.get('Cf-Connecting-Ip') or request.remote_addr,
                            "visitor": visitor_data, "ray": request.headers.get('Cf-Ray') },
             "request": { "host": request.host, "path": request.path, "scheme": request.scheme },
             "server": { "wsgi_url_scheme": request.environ.get('wsgi.url_scheme') }
        })
    except Exception as e_cfping:
        return jsonify({ "error": str(e_cfping), "status": "error", "timestamp": int(time.time()) }), 500