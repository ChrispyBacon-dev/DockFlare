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

# app/web/routes.py

import logging
import time
import copy 
import os 
import random 
import queue 
from datetime import datetime, timezone
import traceback 
import json 

from flask import (
    Blueprint, render_template, jsonify, redirect, url_for, request, Response,
    stream_with_context, current_app
)

from app import config, docker_client, tunnel_state, cloudflared_agent_state, log_queue # Globals from app/__init__
from app.core.state_manager import managed_rules, state_lock, save_state, load_state # load_state if UI triggers it
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
    generate_access_app_config_hash 
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

    with state_lock:
        current_rule = managed_rules.get(hostname)
        if not current_rule:
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {hostname} not found."
            return redirect(url_for('web.status_page'))

        current_access_app_id = current_rule.get("access_app_id")
        desired_session_duration = request.form.get("session_duration", current_rule.get("access_session_duration", "24h"))
        
        
        cf_access_policies = []
        final_policy_type_for_state = new_policy_type
        custom_rules_for_hash = None
        operation_successful = False

        
        if new_policy_type == "none" or new_policy_type == "public_no_policy":
            if current_access_app_id:
                if delete_cloudflare_access_application(current_access_app_id): 
                    current_rule["access_app_id"] = None 
                    operation_successful = True
            # ...
            final_policy_type_for_state = None
        elif new_policy_type == "default_tld":
            
            final_policy_type_for_state = "default_tld"
        elif new_policy_type == "bypass":
            cf_access_policies = [{"name": "UI Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            custom_rules_for_hash = json.dumps(cf_access_policies)
            final_policy_type_for_state = "bypass"
        elif new_policy_type == "authenticate_email":
            if not auth_email: 
                return redirect(url_for('web.status_page'))
            cf_access_policies = [
                {"name": f"UI Allow Email {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
                {"name": "UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
            ]
            custom_rules_for_hash = json.dumps(cf_access_policies)
            final_policy_type_for_state = "authenticate_email"
        
        if new_policy_type in ["bypass", "authenticate_email"]:
            if not cf_access_policies: # ... error ...
                return redirect(url_for('web.status_page'))
            
            new_config_hash = generate_access_app_config_hash( 
                final_policy_type_for_state, desired_session_duration, # ...
                custom_access_rules_str=custom_rules_for_hash
            )
            
            if current_access_app_id:
                
                pass
            else:
                
                pass
        
        if operation_successful:
            current_rule["access_policy_ui_override"] = True
        # ...
        if current_rule.get("access_policy_ui_override") or operation_successful : 
            current_rule["access_policy_ui_override"] = True
            if operation_successful: state_changed_locally = True


        if state_changed_locally: save_state()
    
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
    
    if not docker_client or (not tunnel_state.get("id") and not config.EXTERNAL_TUNNEL_ID): # ...
        return redirect(url_for('web.status_page'))
    hostname = request.form.get('manual_hostname', '').strip()
    
    with state_lock:
        
        save_state()
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if update_cloudflare_config():
        create_cloudflare_dns_record(target_zone_id, hostname, effective_tunnel_id)
    # ...
    return redirect(url_for('web.status_page'))

@bp.route('/ui/manual-rules/delete/<path:hostname>', methods=['POST'])
def ui_delete_manual_rule_route(hostname): 
    
    with state_lock:
        rule_details = managed_rules.get(hostname)
        if rule_details and rule_details.get("source") == "manual":
            # ... (get zone_id, access_app_id) ...
            del managed_rules[hostname]; save_state()
        # ...
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if zone_id_for_delete and effective_tunnel_id: delete_cloudflare_dns_record(...)
    if access_app_id_for_delete: delete_cloudflare_access_application(...)
    if update_cloudflare_config(): pass # ...
    return redirect(url_for('web.status_page'))

@bp.route('/cloudflare-ping')
def cloudflare_ping_route(): # Renamed
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