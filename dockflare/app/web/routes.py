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
from app.core.state_manager import managed_rules, access_groups, state_lock, save_state, load_state
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
from app.core.utils import get_rule_key

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
        'request_scheme': request.scheme,
        'app_version': config.APP_VERSION
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
    template_access_groups = {}

    with state_lock: 
        for hostname, rule in managed_rules.items():
            rule_copy = copy.deepcopy(rule)
            if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
                rule_copy["delete_at"] = rule_copy["delete_at"].replace(tzinfo=timezone.utc) if rule_copy["delete_at"].tzinfo is None else rule_copy["delete_at"].astimezone(timezone.utc)
            rules_for_template[hostname] = rule_copy
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()
        template_access_groups = copy.deepcopy(access_groups)
        
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

    return render_template('status_page.html',
                        tunnel_state=template_tunnel_state,
                        agent_state=template_agent_state,
                        initialization=initialization_status,
                        rules=rules_for_template,
                        CF_ACCOUNT_ID_CONFIGURED=bool(config.CF_ACCOUNT_ID), 
                        ACCOUNT_ID_FOR_DISPLAY=config.CF_ACCOUNT_ID if config.CF_ACCOUNT_ID else "Not Configured",
                        access_groups=template_access_groups,
                        CF_ZONE_ID_CONFIGURED=bool(config.CF_ZONE_ID)
                        )

@bp.route('/settings')
def settings_page():
    groups_for_template = {}
    used_group_ids = set()
    template_tunnel_state = {}
    template_agent_state = {}

    with state_lock:
        used_group_ids = {
            rule.get('access_group_id') for rule in managed_rules.values()
            if rule.get('source') == 'docker' and rule.get('access_group_id')
        }
        groups_for_template = copy.deepcopy(access_groups)
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()

    display_token_val = get_display_token_ui(template_tunnel_state.get("token"))
    all_account_tunnels_list = get_all_account_cloudflare_tunnels()

    return render_template(
        'settings.html',
        access_groups=groups_for_template,
        used_group_ids=used_group_ids,
        all_account_tunnels=all_account_tunnels_list,
        tunnel_state=template_tunnel_state,
        agent_state=template_agent_state,
        display_token=display_token_val,
        cloudflared_container_name=config.CLOUDFLARED_CONTAINER_NAME,
        docker_available=docker_client is not None,
        external_cloudflared=config.USE_EXTERNAL_CLOUDFLARED,
        external_tunnel_id=config.EXTERNAL_TUNNEL_ID,
        CF_ACCOUNT_ID_CONFIGURED=bool(config.CF_ACCOUNT_ID),
        ACCOUNT_ID_FOR_DISPLAY=config.CF_ACCOUNT_ID if config.CF_ACCOUNT_ID else "Not Configured"
    )

@bp.route('/ui_update_access_policy/<path:hostname>', methods=['POST'])
def ui_update_access_policy(hostname):
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: UI Policy Update - Docker client unavailable."
        return redirect(url_for('web.status_page'))
    fqdn = hostname.split('|')[0]

    new_policy_type = request.form.get('access_policy_type')
    auth_email = request.form.get('auth_email', '').strip()
    action_status_message = f"Processing UI policy update for {fqdn}..."
    state_changed_locally = False
    operation_successful = False

    with state_lock:
        current_rule = managed_rules.get(hostname)
        if not current_rule:
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {hostname} not found."
            return redirect(url_for('web.status_page'))

        current_access_app_id = current_rule.get("access_app_id")
        if new_policy_type in ["none", "public_no_policy", "default_tld"]:
            if current_access_app_id:
                logging.info(f"UI: Setting {fqdn} policy to '{new_policy_type}'. Deleting Access App {current_access_app_id}.")
                if delete_cloudflare_access_application(current_access_app_id):
                    action_status_message = f"Success: {fqdn} Access App deleted (set to {new_policy_type})."
                    operation_successful = True
                else:
                    action_status_message = f"Error: Failed to delete Access App for {fqdn}."
            else:
                action_status_message = f"Info: {fqdn} set to {new_policy_type} (no existing Access App in state)."
                operation_successful = True

            if operation_successful:
                current_rule["access_app_id"] = None
                current_rule["access_app_config_hash"] = None
                current_rule["access_policy_type"] = new_policy_type if new_policy_type == "default_tld" else None
                state_changed_locally = True

        elif new_policy_type in ["bypass", "authenticate_email"]:
            cf_access_policies = []
            allowed_idps_for_api_call = None

            if new_policy_type == "bypass":
                cf_access_policies = [{"name": "UI Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            elif new_policy_type == "authenticate_email":
                if not auth_email:
                    cloudflared_agent_state["last_action_status"] = f"Error: Email address required for 'authenticate_email' policy for {fqdn}."
                    return redirect(url_for('web.status_page'))
                
                cf_access_policies = [
                    {"name": f"UI Allow Access for {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
                    {"name": "UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
                ]

            desired_session_duration = request.form.get("session_duration", current_rule.get("access_session_duration", "24h"))
            desired_app_launcher_visible = request.form.get("app_launcher_visible", str(current_rule.get("access_app_launcher_visible", False))).lower() in ["true", "on", "1", "yes"]
            desired_auto_redirect = request.form.get("auto_redirect", str(current_rule.get("access_auto_redirect", False))).lower() in ["true", "on", "1", "yes"]
            
            new_config_hash = generate_access_app_config_hash(
                new_policy_type,
                desired_session_duration, desired_app_launcher_visible, allowed_idps_for_api_call,
                desired_auto_redirect,
                custom_access_rules_str=json.dumps(cf_access_policies)
            )

            if current_access_app_id and current_rule.get("access_app_config_hash") == new_config_hash:
                action_status_message = f"Info: Access Policy for {fqdn} already matched UI selection. No API update needed."
                operation_successful = True
            else:
                desired_app_name = f"DockFlare-{fqdn}"
                
                effective_app_id_for_operation = current_access_app_id
                if not effective_app_id_for_operation:
                    logging.info(f"UI Update: No local Access App ID for {fqdn}. Checking Cloudflare API...")
                    existing_cf_app = find_cloudflare_access_application_by_hostname(fqdn)
                    if existing_cf_app and existing_cf_app.get("id"):
                        effective_app_id_for_operation = existing_cf_app["id"]
                        logging.info(f"UI Update: Found existing Access App ID '{effective_app_id_for_operation}' on Cloudflare for {fqdn}.")

                app_result = None
                if effective_app_id_for_operation:
                    logging.info(f"UI: Attempting to update Access App. ID: {effective_app_id_for_operation}, Target Name: {desired_app_name}, Target Policy: {new_policy_type}")
                    app_result = update_cloudflare_access_application(
                        effective_app_id_for_operation, fqdn, desired_app_name,
                        desired_session_duration, desired_app_launcher_visible,
                        [fqdn], cf_access_policies, allowed_idps_for_api_call, desired_auto_redirect
                    )
                else:
                    logging.info(f"UI: Attempting to create Access App. Target Name: {desired_app_name}, Target Policy: {new_policy_type}")
                    app_result = create_cloudflare_access_application(
                        fqdn, desired_app_name,
                        desired_session_duration, desired_app_launcher_visible,
                        [fqdn], cf_access_policies, allowed_idps_for_api_call,
                        desired_auto_redirect
                    )

                if app_result and app_result.get("id"):
                    current_rule["access_app_id"] = app_result.get("id")
                    current_rule["access_policy_type"] = new_policy_type
                    current_rule["access_app_config_hash"] = new_config_hash
                    state_changed_locally = True
                    operation_successful = True
                    action_status_message = f"Success: Access Policy for {fqdn} created/updated to {new_policy_type}."
                else:
                    action_status_message = f"Error: Failed to create/update Access App for {fqdn}."
        
        if operation_successful:
            current_rule["access_policy_ui_override"] = True
        else:
            logging.warning(f"UI operation for {fqdn} failed or no effective change made.")

        if state_changed_locally or operation_successful:
            save_state()
    
    cloudflared_agent_state["last_action_status"] = action_status_message
    return redirect(url_for('web.status_page'))

@bp.route('/revert_access_policy_to_labels/<path:hostname>', methods=['POST'])
def revert_access_policy_to_labels(hostname):
    fqdn = hostname.split('|')[0]
    if not docker_client:
        return redirect(url_for('web.status_page'))
    
    action_status_message = f"Attempting to revert Access Policy for '{fqdn}' to label configuration..."
    app_id_to_delete_if_any = None
    state_changed_for_revert = False

    with state_lock:
        current_rule = managed_rules.get(hostname)
        if not current_rule:
            return redirect(url_for('web.status_page'))
        if not current_rule.get("access_policy_ui_override", False):
            return redirect(url_for('web.status_page'))
        
        app_id_to_delete_if_any = current_rule.get("access_app_id")
        current_rule["access_policy_ui_override"] = False
        state_changed_for_revert = True
        if state_changed_for_revert: save_state()

    if app_id_to_delete_if_any:
        if delete_cloudflare_access_application(app_id_to_delete_if_any): 
            pass
    
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
    fqdn = hostname.split('|')[0]
    rule_removed_from_state = False; dns_delete_success = False; access_app_delete_success = False
    zone_id_for_delete = None; access_app_id_for_delete = None
    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details: 
            zone_id_for_delete = rule_details.get("zone_id")
            access_app_id_for_delete = rule_details.get("access_app_id")
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if zone_id_for_delete and effective_tunnel_id:
        dns_delete_success = delete_cloudflare_dns_record(zone_id_for_delete, fqdn, effective_tunnel_id)
    if access_app_id_for_delete:
        access_app_delete_success = delete_cloudflare_access_application(access_app_id_for_delete)
    with state_lock:
        if hostname in managed_rules: del managed_rules[hostname]; rule_removed_from_state = True; save_state()
    if rule_removed_from_state and not config.USE_EXTERNAL_CLOUDFLARED:
        if update_cloudflare_config(): pass 
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
    manual_http_host_header = request.form.get('manual_http_host_header', '').strip()

    manual_access_group_id = request.form.get('manual_access_group', '').strip()
    manual_access_policy_type = request.form.get('manual_access_policy_type', 'none').strip().lower()
    manual_auth_email = request.form.get('manual_auth_email', '').strip()

    if not domain_name_input or not service_type_input:
        cloudflared_agent_state["last_action_status"] = "Error: Domain Name and Service Type are required for manual rule."
        return redirect(url_for('web.status_page'))
    if service_type_input not in ["http_status", "bastion"] and not service_address_input:
        cloudflared_agent_state["last_action_status"] = f"Error: Service Address is required for type '{service_type_input.upper()}'."
        return redirect(url_for('web.status_page'))
    
    full_hostname = f"{subdomain_input}.{domain_name_input}" if subdomain_input else domain_name_input
    if not is_valid_hostname(full_hostname):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed hostname '{full_hostname}' is invalid."
        return redirect(url_for('web.status_page'))
    
    processed_path = f"/{path_input.lstrip('/')}" if path_input else None
    key_for_managed_rules = get_rule_key(full_hostname, processed_path)
    
    processed_service_for_cf = ""
    if service_type_input in ["http", "https"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input in ["tcp", "ssh", "rdp"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input == "http_status":
        processed_service_for_cf = f"http_status:{service_address_input}"
    
    if not is_valid_service(processed_service_for_cf):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed service string '{processed_service_for_cf}' is invalid."
        return redirect(url_for('web.status_page'))
    
    zone_name_to_lookup = zone_name_override_input or '.'.join(domain_name_input.split('.')[-2:])
    target_zone_id = get_zone_id_from_name(zone_name_to_lookup) or config.CF_ZONE_ID
    if not target_zone_id:
        cloudflared_agent_state["last_action_status"] = f"Error: Could not determine Zone ID."
        return redirect(url_for('web.status_page'))
        
    access_app_id = None
    access_policy_type = None
    access_app_config_hash = None
    access_group_id = None

    with state_lock:
        if manual_access_group_id and manual_access_group_id in access_groups:
            group = access_groups[manual_access_group_id]
            access_group_id = manual_access_group_id
            access_policy_type = "group"
            
            desired_app_name = f"DockFlare-{full_hostname}"
            desired_session_duration = group.get("session_duration", "24h")
            desired_app_launcher_visible = group.get("app_launcher_visible", False)
            desired_allowed_idps = group.get("allowed_idps")
            desired_auto_redirect = group.get("auto_redirect_to_identity", False)
            cf_access_policies = group.get("policies")

            access_app_config_hash = generate_access_app_config_hash(
                policy_type="group", session_duration=desired_session_duration,
                app_launcher_visible=desired_app_launcher_visible,
                allowed_idps_str=json.dumps(desired_allowed_idps, sort_keys=True),
                auto_redirect_to_identity=desired_auto_redirect,
                custom_access_rules_str=json.dumps(cf_access_policies, sort_keys=True),
                group_id=access_group_id
            )

            existing_app = find_cloudflare_access_application_by_hostname(full_hostname)
            if existing_app:
                app_result = update_cloudflare_access_application(
                    existing_app['id'], full_hostname, desired_app_name, desired_session_duration,
                    desired_app_launcher_visible, [full_hostname], cf_access_policies,
                    desired_allowed_idps, desired_auto_redirect
                )
            else:
                app_result = create_cloudflare_access_application(
                    full_hostname, desired_app_name, desired_session_duration,
                    desired_app_launcher_visible, [full_hostname], cf_access_policies,
                    desired_allowed_idps, desired_auto_redirect
                )

            if app_result:
                access_app_id = app_result.get('id')
            else:
                cloudflared_agent_state["last_action_status"] = f"Error: Failed to create/update Access App for group '{access_group_id}'."

        elif manual_access_policy_type and manual_access_policy_type != 'none':
            cf_access_policies = []
            if manual_access_policy_type == "bypass":
                cf_access_policies = [{"name": "UI Manual Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            elif manual_access_policy_type == "authenticate_email":
                if not manual_auth_email:
                    cloudflared_agent_state["last_action_status"] = "Error: Email is required for this policy type."
                    return redirect(url_for('web.status_page'))
                cf_access_policies = [
                    {"name": f"UI Allow Access for {manual_auth_email}", "decision": "allow", "include": [{"email": {"email": manual_auth_email}}]},
                    {"name": "UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
                ]
            
            app_result = create_cloudflare_access_application(
                full_hostname, f"DockFlare-{full_hostname}", "24h", False, [full_hostname], cf_access_policies, None, False
            )
            if app_result:
                access_app_id = app_result.get('id')
                access_policy_type = manual_access_policy_type
            else:
                cloudflared_agent_state["last_action_status"] = f"Error: Failed to create Access App for manual policy."

    with state_lock:
        if key_for_managed_rules in managed_rules and managed_rules[key_for_managed_rules].get("source") == "docker":
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {full_hostname} is Docker-managed."
            return redirect(url_for('web.status_page'))

        managed_rules[key_for_managed_rules] = {
            "hostname": full_hostname,
            "path": processed_path,
            "service": processed_service_for_cf,
            "container_id": None, "status": "active", "delete_at": None,
            "zone_id": target_zone_id,
            "no_tls_verify": no_tls_verify,
            "origin_server_name": origin_server_name_input or None,
            "http_host_header": manual_http_host_header or None,
            "source": "manual",
            "access_app_id": access_app_id,
            "access_policy_type": access_policy_type,
            "access_app_config_hash": access_app_config_hash,
            "access_group_id": access_group_id,
            "access_policy_ui_override": bool(access_app_id)
        }
        save_state()

    if update_cloudflare_config():
        create_cloudflare_dns_record(target_zone_id, full_hostname, effective_tunnel_id)
        cloudflared_agent_state["last_action_status"] = f"Success: Manual rule for {full_hostname} added/updated."
    else:
        cloudflared_agent_state["last_action_status"] = f"Error: Failed to update Cloudflare tunnel config."

    return redirect(url_for('web.status_page'))

@bp.route('/ui/manual-rules/delete/<path:rule_key_from_url>', methods=['POST'])
def ui_delete_manual_rule_route(rule_key_from_url):
    if not docker_client: 
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to delete manual rule. Docker client unavailable."
        return redirect(url_for('web.status_page'))
    
    fqdn_for_dns = rule_key_from_url.split('|')[0]
    
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if not effective_tunnel_id: 
        cloudflared_agent_state["last_action_status"] = "Error: System not ready to delete manual rule. Tunnel not initialized or ID missing."
        return redirect(url_for('web.status_page'))

    rule_key_in_state = rule_key_from_url 
    logging.info(f"UI request: Delete manual rule for key: {rule_key_in_state}")
    
    zone_id_for_delete = None
    access_app_id_for_delete = None
    rule_existed_as_manual_and_deleted = False 

    with state_lock:
        rule_details = managed_rules.get(rule_key_in_state)
        if rule_details and rule_details.get("source") == "manual":
            logging.info(f"Found manual rule for {rule_key_in_state} to delete. Details: {rule_details}")
            zone_id_for_delete = rule_details.get("zone_id")
            access_app_id_for_delete = rule_details.get("access_app_id")
            
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
        if fqdn_for_dns: 
            with state_lock: 
                for other_key in managed_rules.keys():
                    if other_key.split('|')[0] == fqdn_for_dns:
                        should_delete_dns_record = False 
                        logging.info(f"DNS for {fqdn_for_dns} will NOT be deleted as other rules still use it (e.g., {other_key}).")
                        break
        else:
            should_delete_dns_record = False 
            logging.error(f"Cannot perform DNS deletion as FQDN could not be parsed from rule key {rule_key_in_state}.")

        if should_delete_dns_record and zone_id_for_delete and fqdn_for_dns: 
            logging.info(f"Attempting DNS delete for {fqdn_for_dns} (from rule {rule_key_in_state}) in zone {zone_id_for_delete}")
            if delete_cloudflare_dns_record(zone_id_for_delete, fqdn_for_dns, effective_tunnel_id):
                dns_deleted_successfully = True
                logging.info(f"DNS record for {fqdn_for_dns} deleted successfully.")
            else:
                logging.error(f"Failed to delete DNS record for {fqdn_for_dns}.")
        elif not should_delete_dns_record:
            dns_deleted_successfully = True 
            if fqdn_for_dns: 
                 logging.info(f"DNS deletion for {fqdn_for_dns} skipped because it's still in use.")

        if access_app_id_for_delete: 
            logging.info(f"Attempting Access App delete for manual rule {rule_key_in_state}, App ID {access_app_id_for_delete}")
            is_app_id_shared = False
            with state_lock: 
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

    with state_lock:
        original_rule_details = managed_rules.get(original_rule_key)
        if not original_rule_details or original_rule_details.get("source") != "manual":
            cloudflared_agent_state["last_action_status"] = f"Error: Could not find original manual rule '{original_rule_key}' to edit."
            return redirect(url_for('web.status_page'))

    subdomain_input = request.form.get('manual_subdomain', '').strip()
    domain_name_input = request.form.get('manual_domain_name', '').strip()
    path_input = request.form.get('manual_path', '').strip()
    service_type_input = request.form.get('manual_service_type', '').strip().lower()
    service_address_input = request.form.get('manual_service_address', '').strip()
    zone_name_override_input = request.form.get('manual_zone_name_override', '').strip()
    no_tls_verify = request.form.get('manual_no_tls_verify') == 'on'
    origin_server_name_input = request.form.get('manual_origin_server_name', '').strip()
    manual_http_host_header = request.form.get('manual_http_host_header', '').strip()
    manual_access_group_id = request.form.get('manual_access_group', '').strip()
    manual_access_policy_type = request.form.get('manual_access_policy_type', 'none').strip().lower()
    manual_auth_email = request.form.get('manual_auth_email', '').strip()
    
    if not domain_name_input or not service_type_input:
        cloudflared_agent_state["last_action_status"] = "Error: Domain Name and Service Type are required."
        return redirect(url_for('web.status_page'))
    if service_type_input not in ["http_status", "bastion"] and not service_address_input:
        cloudflared_agent_state["last_action_status"] = f"Error: Service Address is required for type '{service_type_input.upper()}'."
        return redirect(url_for('web.status_page'))

    full_hostname = f"{subdomain_input}.{domain_name_input}" if subdomain_input else domain_name_input
    if not is_valid_hostname(full_hostname):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed hostname '{full_hostname}' is invalid."
        return redirect(url_for('web.status_page'))
    
    processed_path = f"/{path_input.lstrip('/')}" if path_input else None
    new_rule_key = get_rule_key(full_hostname, processed_path)
    
    processed_service_for_cf = ""
    if service_type_input in ["http", "https"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input in ["tcp", "ssh", "rdp"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input == "http_status":
        processed_service_for_cf = f"http_status:{service_address_input}"
    
    if not is_valid_service(processed_service_for_cf):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed service string '{processed_service_for_cf}' is invalid."
        return redirect(url_for('web.status_page'))

    zone_name_to_lookup = zone_name_override_input or '.'.join(domain_name_input.split('.')[-2:])
    target_zone_id = get_zone_id_from_name(zone_name_to_lookup) or config.CF_ZONE_ID
    if not target_zone_id:
        cloudflared_agent_state["last_action_status"] = f"Error: Could not determine Zone ID."
        return redirect(url_for('web.status_page'))
        
    access_app_id = None
    access_policy_type = None
    access_app_config_hash = None
    access_group_id = None
    app_to_delete = None

    with state_lock:
        if manual_access_group_id and manual_access_group_id in access_groups:
            group = access_groups[manual_access_group_id]
            access_group_id = manual_access_group_id
            access_policy_type = "group"
            
            desired_app_name = f"DockFlare-{full_hostname}"
            desired_session_duration = group.get("session_duration", "24h")
            desired_app_launcher_visible = group.get("app_launcher_visible", False)
            desired_allowed_idps = group.get("allowed_idps")
            desired_auto_redirect = group.get("auto_redirect_to_identity", False)
            cf_access_policies = group.get("policies")

            access_app_config_hash = generate_access_app_config_hash(
                policy_type="group", session_duration=desired_session_duration,
                app_launcher_visible=desired_app_launcher_visible,
                allowed_idps_str=json.dumps(desired_allowed_idps, sort_keys=True),
                auto_redirect_to_identity=desired_auto_redirect,
                custom_access_rules_str=json.dumps(cf_access_policies, sort_keys=True),
                group_id=access_group_id
            )

            existing_app = find_cloudflare_access_application_by_hostname(full_hostname)
            app_to_update_id = existing_app['id'] if existing_app else original_rule_details.get('access_app_id')

            if app_to_update_id and (original_rule_details.get('hostname') != full_hostname):
                app_to_delete = app_to_update_id
                app_to_update_id = None

            if app_to_update_id:
                app_result = update_cloudflare_access_application(
                    app_to_update_id, full_hostname, desired_app_name, desired_session_duration,
                    desired_app_launcher_visible, [full_hostname], cf_access_policies,
                    desired_allowed_idps, desired_auto_redirect
                )
            else:
                app_result = create_cloudflare_access_application(
                    full_hostname, desired_app_name, desired_session_duration,
                    desired_app_launcher_visible, [full_hostname], cf_access_policies,
                    desired_allowed_idps, desired_auto_redirect
                )

            if app_result: access_app_id = app_result.get('id')

        elif manual_access_policy_type and manual_access_policy_type != 'none':
            cf_access_policies = []
            if manual_access_policy_type == "bypass":
                cf_access_policies = [{"name": "UI Manual Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            elif manual_access_policy_type == "authenticate_email":
                if not manual_auth_email:
                    cloudflared_agent_state["last_action_status"] = "Error: Email is required for this policy type."
                    return redirect(url_for('web.status_page'))
                cf_access_policies = [
                    {"name": f"UI Allow Access for {manual_auth_email}", "decision": "allow", "include": [{"email": {"email": manual_auth_email}}]},
                    {"name": "UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
                ]
            
            app_result = create_cloudflare_access_application(
                full_hostname, f"DockFlare-{full_hostname}", "24h", False, [full_hostname], cf_access_policies, None, False
            )
            if app_result:
                access_app_id = app_result.get('id')
                access_policy_type = manual_access_policy_type
        
        else: # Case where policy is set to "None"
            if original_rule_details.get('access_app_id'):
                app_to_delete = original_rule_details.get('access_app_id')

    if app_to_delete:
        delete_cloudflare_access_application(app_to_delete)

    if original_rule_key != new_rule_key:
        old_hostname = original_rule_details.get('hostname')
        old_zone_id = original_rule_details.get('zone_id')
        with state_lock:
            is_old_hostname_still_used = any(r.get("hostname") == old_hostname for k, r in managed_rules.items() if k != original_rule_key)
        if not is_old_hostname_still_used:
            delete_cloudflare_dns_record(old_zone_id, old_hostname, effective_tunnel_id)
    
    with state_lock:
        if new_rule_key in managed_rules and new_rule_key != original_rule_key:
            cloudflared_agent_state["last_action_status"] = f"Error: A rule for {full_hostname} already exists."
            return redirect(url_for('web.status_page'))

        if original_rule_key in managed_rules:
            del managed_rules[original_rule_key]

        managed_rules[new_rule_key] = {
            "hostname": full_hostname,
            "path": processed_path,
            "service": processed_service_for_cf,
            "container_id": None, "status": "active", "delete_at": None,
            "zone_id": target_zone_id,
            "no_tls_verify": no_tls_verify,
            "origin_server_name": origin_server_name_input or None,
            "http_host_header": manual_http_host_header or None,
            "source": "manual",
            "access_app_id": access_app_id,
            "access_policy_type": access_policy_type,
            "access_app_config_hash": access_app_config_hash,
            "access_group_id": access_group_id,
            "access_policy_ui_override": bool(access_app_id)
        }
        save_state()

    if update_cloudflare_config():
        create_cloudflare_dns_record(target_zone_id, full_hostname, effective_tunnel_id)
        cloudflared_agent_state["last_action_status"] = f"Success: Manual rule for {full_hostname} updated."
    else:
        cloudflared_agent_state["last_action_status"] = f"Error: Failed to update Cloudflare tunnel config."

    return redirect(url_for('web.status_page'))

def _parse_and_build_policy_from_form(email_str):
    if not email_str or not email_str.strip():
        return []
    
    include_rules = []
    
    parts = [part.strip() for part in email_str.split(',') if part.strip()]
    for part in parts:
        if part.startswith('@'):
            include_rules.append({"email_domain": {"domain": part[1:]}})
        else:
            include_rules.append({"email": {"email": part}})
            
    if not include_rules:
        return []

    return [
        {"name": "Allow defined users and domains", "decision": "allow", "include": include_rules},
        {"name": "Default Deny", "decision": "deny", "include": [{"everyone": {}}]}
    ]


@bp.route('/ui/access-groups/create', methods=['POST'])
def create_access_group():
    form = request.form
    group_id = form.get('group_id', '').strip()
    display_name = form.get('display_name', '').strip()

    if not group_id or not display_name:
        cloudflared_agent_state["last_action_status"] = "Error: Group ID and Display Name are required."
        return redirect(url_for('web.settings_page'))

    with state_lock:
        if group_id in access_groups:
            cloudflared_agent_state["last_action_status"] = f"Error: Access Group with ID '{group_id}' already exists."
            return redirect(url_for('web.settings_page'))
        
        new_group = {
            "id": group_id,
            "display_name": display_name,
            "session_duration": form.get('session_duration', '24h').strip(),
            "app_launcher_visible": form.get('app_launcher_visible') == 'on',
            "auto_redirect_to_identity": form.get('auto_redirect') == 'on',
            "policies": _parse_and_build_policy_from_form(form.get('emails', ''))
        }
        access_groups[group_id] = new_group
        save_state()

    cloudflared_agent_state["last_action_status"] = f"Success: Access Group '{display_name}' created."
    return redirect(url_for('web.settings_page'))


@bp.route('/ui/access-groups/edit/<group_id>', methods=['POST'])
def edit_access_group(group_id):
    with state_lock:
        if group_id not in access_groups:
            cloudflared_agent_state["last_action_status"] = f"Error: Access Group with ID '{group_id}' not found."
            return redirect(url_for('web.settings_page'))
    
    form = request.form
    display_name = form.get('display_name', '').strip()
    if not display_name:
        cloudflared_agent_state["last_action_status"] = "Error: Display Name is required."
        return redirect(url_for('web.settings_page'))
    
    with state_lock:
        updated_group = {
            "id": group_id,
            "display_name": display_name,
            "session_duration": form.get('session_duration', '24h').strip(),
            "app_launcher_visible": form.get('app_launcher_visible') == 'on',
            "auto_redirect_to_identity": form.get('auto_redirect') == 'on',
            "policies": _parse_and_build_policy_from_form(form.get('emails', ''))
        }
        access_groups[group_id] = updated_group
        save_state()

    cloudflared_agent_state["last_action_status"] = f"Success: Access Group '{display_name}' updated. Triggering reconciliation."
    reconcile_state_threaded()
    return redirect(url_for('web.settings_page'))


@bp.route('/ui/access-groups/delete/<group_id>', methods=['POST'])
def delete_access_group(group_id):
    with state_lock:
        if group_id not in access_groups:
            cloudflared_agent_state["last_action_status"] = f"Error: Access Group with ID '{group_id}' not found."
            return redirect(url_for('web.settings_page'))

        is_in_use = any(
            rule.get('access_group_id') == group_id
            for rule in managed_rules.values()
        )

        if is_in_use:
            cloudflared_agent_state["last_action_status"] = f"Error: Cannot delete Access Group '{access_groups[group_id]['display_name']}' because it is currently in use."
            return redirect(url_for('web.settings_page'))

        display_name = access_groups[group_id]['display_name']
        del access_groups[group_id]
        save_state()

    cloudflared_agent_state["last_action_status"] = f"Success: Access Group '{display_name}' has been deleted."
    return redirect(url_for('web.settings_page'))


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