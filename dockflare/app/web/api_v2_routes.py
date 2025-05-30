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
# dockflare/app/web/api_v2_routes.py
import copy
import logging
import os
import time 
import traceback 
import json 
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, current_app, url_for

from app import config, docker_client, tunnel_state, cloudflared_agent_state, log_queue
from app.core.state_manager import managed_rules, state_lock, save_state
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

api_v2_bp = Blueprint('api_v2', __name__, url_prefix='/api/v2')

def serialize_rule(rule_data):
    if not rule_data:
        return None
    serialized = copy.deepcopy(rule_data)
    if "delete_at" in serialized and isinstance(serialized["delete_at"], datetime):
        dt_obj = serialized["delete_at"]
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        else:
            dt_obj = dt_obj.astimezone(timezone.utc)
        serialized["delete_at"] = dt_obj.isoformat()
    return serialized

def get_effective_tunnel_id():
    return tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID

@api_v2_bp.route('/overview', methods=['GET'])
def get_overview_data():
    rules_for_api = {}
    api_tunnel_state = {}
    api_agent_state = {}
    initialization_status_api = {}
    tld_policy_exists_val_api = False
    account_email_for_tld_api = None
    relevant_zone_name_for_tld_policy_api = None

    with state_lock:
        for hostname_key, rule_value in managed_rules.items():
            rules_for_api[hostname_key] = serialize_rule(rule_value)
        
        api_tunnel_state = tunnel_state.copy()
        api_agent_state = cloudflared_agent_state.copy() 

        initialization_status_api = {
            "complete": api_tunnel_state.get("id") is not None or config.EXTERNAL_TUNNEL_ID,
            "in_progress": not (api_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID) and \
                            api_tunnel_state.get("status_message", "").lower().startswith("init")
        }

        if config.CF_ZONE_ID and docker_client:
            zone_details = get_zone_details_by_id(config.CF_ZONE_ID)
            if zone_details and zone_details.get("name"):
                relevant_zone_name_for_tld_policy_api = zone_details.get("name")
            
            if relevant_zone_name_for_tld_policy_api:
                tld_policy_exists_val_api = check_for_tld_access_policy(relevant_zone_name_for_tld_policy_api)
                if not tld_policy_exists_val_api:
                    account_email_for_tld_api = get_cloudflare_account_email()
    
    all_account_tunnels_list_api = get_all_account_cloudflare_tunnels()
    
    log_stream_url = "/stream-logs"
    try:
        log_stream_url = url_for('web.stream_logs_route', _external=False)
    except RuntimeError as e:
        logging.error(f"RuntimeError generating url_for for 'web.stream_logs_route': {e}. Falling back to static path.")

    return jsonify({
        "tunnel_state": api_tunnel_state,
        "agent_state": api_agent_state,
        "initialization": initialization_status_api,
        "display_token": tunnel_state.get("token"), 
        "cloudflared_container_name": config.CLOUDFLARED_CONTAINER_NAME,
        "docker_available": docker_client is not None,
        "external_cloudflared": config.USE_EXTERNAL_CLOUDFLARED,
        "external_tunnel_id": config.EXTERNAL_TUNNEL_ID,
        "rules": rules_for_api,
        "all_account_tunnels": all_account_tunnels_list_api,
        "config_status": {
            "cf_account_id_configured": bool(config.CF_ACCOUNT_ID),
            "account_id_for_display": config.CF_ACCOUNT_ID if config.CF_ACCOUNT_ID else "Not Configured",
            "cf_zone_id_configured": bool(config.CF_ZONE_ID),
            "relevant_zone_name_for_tld_policy": relevant_zone_name_for_tld_policy_api,
            "tld_policy_exists": tld_policy_exists_val_api,
            "account_email_for_tld": account_email_for_tld_api,
        },
        "reconciliation_info": getattr(current_app, 'reconciliation_info', {
            "in_progress": False, "progress": 0, "total_items": 0,
            "processed_items": 0, "status": "Not started"
        }),
        "log_stream_path": log_stream_url
    })

@api_v2_bp.route('/reconciliation-status', methods=['GET'])
def get_reconciliation_status():
    reconciliation_info_data = getattr(current_app, 'reconciliation_info', {})
    return jsonify({
        "in_progress": reconciliation_info_data.get("in_progress", False),
        "progress": reconciliation_info_data.get("progress", 0),
        "total_items": reconciliation_info_data.get("total_items", 0),
        "processed_items": reconciliation_info_data.get("processed_items", 0),
        "status": reconciliation_info_data.get("status", "Not started")
    })

@api_v2_bp.route('/agent/start', methods=['POST'])
def agent_start():
    if config.USE_EXTERNAL_CLOUDFLARED:
        return jsonify({"status": "error", "message": "Cannot start agent: configured for external cloudflared."}), 400
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client not available."}), 503
        
    start_cloudflared_container()
    time.sleep(0.5) 
    return jsonify({
        "status": "success",
        "message": "Agent start command issued.",
        "agent_state": cloudflared_agent_state.copy()
    }), 202 

@api_v2_bp.route('/agent/stop', methods=['POST'])
def agent_stop():
    if config.USE_EXTERNAL_CLOUDFLARED:
        return jsonify({"status": "error", "message": "Cannot stop agent: configured for external cloudflared."}), 400
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client not available."}), 503

    stop_cloudflared_container()
    time.sleep(0.5)
    return jsonify({
        "status": "success",
        "message": "Agent stop command issued.",
        "agent_state": cloudflared_agent_state.copy()
    }), 202 

@api_v2_bp.route('/rules/manual', methods=['POST'])
def add_manual_rule():
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client unavailable."}), 503
    
    effective_tunnel_id = get_effective_tunnel_id()
    if not effective_tunnel_id:
        return jsonify({"status": "error", "message": "Tunnel not initialized or Tunnel ID missing."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON payload."}), 400

    subdomain = data.get('subdomain', '').strip()
    domain_name = data.get('domain_name', '').strip()
    path = data.get('path', '').strip()
    service_type = data.get('service_type', '').strip().lower()
    service_address = data.get('service_address', '').strip()
    zone_name_override = data.get('zone_name_override', '').strip()
    no_tls_verify = data.get('no_tls_verify', False) # boolean
    origin_server_name = data.get('origin_server_name', '').strip()
    access_policy_type = data.get('access_policy_type', 'none').strip().lower()
    auth_email = data.get('auth_email', '').strip()
    session_duration = data.get('session_duration', '24h')
    app_launcher_visible = data.get('app_launcher_visible', False)
    allowed_idps_str = data.get('allowed_idps_str') 
    auto_redirect = data.get('auto_redirect', False)

    if not domain_name or not service_type:
        return jsonify({"status": "error", "message": "Domain Name and Service Type are required."}), 400

    if subdomain:
        full_hostname = f"{subdomain}.{domain_name}"
    else:
        full_hostname = domain_name
    
    if not is_valid_hostname(full_hostname):
        return jsonify({"status": "error", "message": f"Constructed hostname '{full_hostname}' is invalid."}), 400

    processed_path = None
    if path:
        processed_path = path.strip()
        if not processed_path.startswith('/'):
            return jsonify({"status": "error", "message": f"Path '{processed_path}' must start with a '/'."}), 400
        if len(processed_path) > 1 and processed_path.endswith('/'):
            processed_path = processed_path.rstrip('/')

    rule_key = f"{full_hostname}{'|' + processed_path if processed_path else ''}"

    processed_service_for_cf = "" 
    if service_type in ["http", "https"]:
        if ":" not in service_address and "." not in service_address and service_address != "localhost":
             return jsonify({"status": "error", "message": f"For HTTP/S, address '{service_address}' should be host:port or a resolvable hostname."}), 400
        processed_service_for_cf = f"{service_type}://{service_address}"
    elif service_type in ["tcp", "ssh", "rdp", "smb", "vnc"]: 
        if ":" not in service_address:
            return jsonify({"status": "error", "message": f"For {service_type.upper()}, address '{service_address}' must be in host:port format."}), 400
        processed_service_for_cf = f"{service_type}://{service_address}"
    elif service_type == "http_status":
        if not service_address.isdigit() or not (100 <= int(service_address) <= 599):
            return jsonify({"status": "error", "message": f"Invalid HTTP status code '{service_address}'. Must be 100-599."}), 400
        processed_service_for_cf = f"http_status:{service_address}"
    elif service_type == "unix":
        if not service_address.startswith("/"):
            return jsonify({"status": "error", "message": "For UNIX socket, address must be an absolute path."}), 400
        processed_service_for_cf = f"unix:{service_address}"
    else: 
        if service_type != "bastion":
             return jsonify({"status": "error", "message": f"Unsupported service type '{service_type}' submitted."}), 400
        processed_service_for_cf = "bastion" 

    if service_type != "bastion" and not is_valid_service(processed_service_for_cf):
         return jsonify({"status": "error", "message": f"Constructed service string '{processed_service_for_cf}' is invalid."}), 400

    target_zone_id = None 
    zone_name_to_lookup = zone_name_override if zone_name_override else ('.'.join(domain_name.split('.')[-2:]) if '.' in domain_name else None)
    if zone_name_to_lookup:
        target_zone_id = get_zone_id_from_name(zone_name_to_lookup)
    if not target_zone_id:
        if config.CF_ZONE_ID:
            target_zone_id = config.CF_ZONE_ID
        else:
            return jsonify({"status": "error", "message": f"Could not determine Zone ID for '{zone_name_to_lookup or domain_name}' and no default CF_ZONE_ID."}), 400

    access_app_created_or_updated_id = None
    access_app_final_config_hash = None
    cf_access_policies_for_app = []
    custom_rules_for_hash_str = None
    desired_app_name = f"DockFlare-{full_hostname}" 

    if access_policy_type == "bypass":
        cf_access_policies_for_app = [{"name": "API Manual Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
        custom_rules_for_hash_str = json.dumps(cf_access_policies_for_app)
    elif access_policy_type == "authenticate_email":
        if not auth_email:
            return jsonify({"status": "error", "message": "Auth Email is required for 'authenticate_email' policy."}), 400
        cf_access_policies_for_app = [
            {"name": f"API Manual Allow Email {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
            {"name": "API Manual Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
        ]
        custom_rules_for_hash_str = json.dumps(cf_access_policies_for_app)
    
    allowed_idps_list = [idp.strip() for idp in allowed_idps_str.split(',') if idp.strip()] if allowed_idps_str else None
    if access_policy_type in ["bypass", "authenticate_email"]:
        existing_cf_app = find_cloudflare_access_application_by_hostname(full_hostname)
        if existing_cf_app and existing_cf_app.get("id"):
            app_id_to_use = existing_cf_app.get("id")
            updated_app = update_cloudflare_access_application(
                app_id_to_use, full_hostname, desired_app_name,
                session_duration, app_launcher_visible,
                [full_hostname], cf_access_policies_for_app, allowed_idps_list, auto_redirect
            )
            if updated_app: access_app_created_or_updated_id = updated_app.get("id")
        else:
            created_app = create_cloudflare_access_application(
                full_hostname, desired_app_name,
                session_duration, app_launcher_visible,
                [full_hostname], cf_access_policies_for_app, allowed_idps_list, auto_redirect
            )
            if created_app: access_app_created_or_updated_id = created_app.get("id")
        
        if access_app_created_or_updated_id:
            access_app_final_config_hash = generate_access_app_config_hash(
                access_policy_type, session_duration, app_launcher_visible,
                allowed_idps_str, auto_redirect, custom_access_rules_str=custom_rules_for_hash_str
            )
        else:
            logging.error(f"API: Failed to create/update Access App for manual rule {full_hostname}")
            # Decide if this is a critical failure for the whole rule add operation

    with state_lock:
        if rule_key in managed_rules and managed_rules[rule_key].get("source", "docker") == "docker":
            return jsonify({"status": "error", "message": f"Rule for '{rule_key}' is Docker-managed and cannot be manually overridden this way."}), 409 

        managed_rules[rule_key] = {
            "service": processed_service_for_cf, "path": processed_path,
            "hostname_for_dns": full_hostname, "container_id": None, "status": "active",
            "delete_at": None, "zone_id": target_zone_id, "no_tls_verify": no_tls_verify,
            "origin_server_name": origin_server_name if origin_server_name else None,
            "access_app_id": access_app_created_or_updated_id,
            "access_policy_type": access_policy_type if access_policy_type != "none" else None,
            "access_app_config_hash": access_app_final_config_hash,
            "auth_email": auth_email if access_policy_type == "authenticate_email" else None,
            "access_policy_ui_override": True if access_policy_type != "none" else False, 
            "access_session_duration": session_duration,
            "access_app_launcher_visible": app_launcher_visible,
            "access_allowed_idps_str": allowed_idps_str,
            "access_auto_redirect": auto_redirect,
            "source": "manual"
        }
        save_state()

    dns_success = create_cloudflare_dns_record(target_zone_id, full_hostname, effective_tunnel_id)
    config_update_success = update_cloudflare_config()

    if config_update_success:
        message = f"Manual rule for {rule_key} added/updated."
        if not dns_success: message += " DNS creation FAILED."
        return jsonify({"status": "success", "message": message, "rule_key": rule_key, "rule_data": serialize_rule(managed_rules.get(rule_key))}), 201
    else:
        # Potentially revert state changes or mark rule as errored if critical
        return jsonify({"status": "error", "message": f"Failed to update Cloudflare tunnel config for manual rule {rule_key}."}), 500

@api_v2_bp.route('/rules/manual/<path:rule_key>', methods=['DELETE'])
def delete_manual_rule(rule_key):
    if not docker_client: 
        return jsonify({"status": "error", "message": "System not ready."}), 503
    
    effective_tunnel_id = get_effective_tunnel_id()
    if not effective_tunnel_id:
        return jsonify({"status": "error", "message": "Tunnel not initialized."}), 503

    zone_id_for_delete = None
    access_app_id_for_delete = None
    hostname_for_dns_operations = None
    rule_deleted_from_state = False

    with state_lock:
        rule_details = managed_rules.get(rule_key)
        if not rule_details or rule_details.get("source") != "manual":
            return jsonify({"status": "error", "message": f"Manual rule '{rule_key}' not found or not a manual rule."}), 404
        
        zone_id_for_delete = rule_details.get("zone_id")
        access_app_id_for_delete = rule_details.get("access_app_id")
        hostname_for_dns_operations = rule_details.get("hostname_for_dns")
        
        del managed_rules[rule_key]
        save_state()
        rule_deleted_from_state = True

    dns_deleted_ok = True 
    access_app_deleted_ok = True 

    should_delete_dns = True
    if hostname_for_dns_operations:
        with state_lock: 
            for other_rule in managed_rules.values():
                if other_rule.get("hostname_for_dns") == hostname_for_dns_operations:
                    should_delete_dns = False
                    break
    else: should_delete_dns = False 

    if should_delete_dns and zone_id_for_delete:
        if not delete_cloudflare_dns_record(zone_id_for_delete, hostname_for_dns_operations, effective_tunnel_id):
            dns_deleted_ok = False
            logging.error(f"API: Failed to delete DNS record for {hostname_for_dns_operations} from manual rule {rule_key}.")

    should_delete_access_app = True
    if access_app_id_for_delete:
        with state_lock: 
            for other_rule_key, other_rule in managed_rules.items():
                if other_rule.get("access_app_id") == access_app_id_for_delete:
                    should_delete_access_app = False
                    logging.info(f"API: Access App ID {access_app_id_for_delete} for rule {rule_key} is shared by rule {other_rule_key}. Not deleting.")
                    break
        if should_delete_access_app:
            if not delete_cloudflare_access_application(access_app_id_for_delete):
                access_app_deleted_ok = False
                logging.error(f"API: Failed to delete Access App {access_app_id_for_delete} from manual rule {rule_key}.")
    
    config_update_success = update_cloudflare_config()

    if config_update_success:
        message = f"Manual rule {rule_key} deleted."
        if not dns_deleted_ok: message += " DNS deletion failed or skipped."
        if not access_app_deleted_ok: message += " Access App deletion failed or skipped."
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "warning", "message": f"Manual rule {rule_key} removed from state, but Cloudflare tunnel config update FAILED."}), 207 # Multi-Status

@api_v2_bp.route('/rules/<path:rule_key>/force-delete', methods=['POST']) 
def force_delete_rule(rule_key):
    effective_tunnel_id = get_effective_tunnel_id()
    if not effective_tunnel_id:
        return jsonify({"status": "error", "message": "Tunnel not initialized."}), 503

    zone_id_for_delete = None
    access_app_id_for_delete = None
    hostname_for_dns = None
    rule_details_copy = None

    with state_lock:
        rule_details = managed_rules.get(rule_key)
        if not rule_details:
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' not found."}), 404
        
        rule_details_copy = rule_details.copy() 
        zone_id_for_delete = rule_details_copy.get("zone_id")
        access_app_id_for_delete = rule_details_copy.get("access_app_id")
        hostname_for_dns = rule_details_copy.get("hostname_for_dns")
        
        del managed_rules[rule_key]
        save_state()

    dns_deleted = True 
    if zone_id_for_delete and hostname_for_dns:
        # Check if DNS is shared
        is_dns_shared = False
        with state_lock:
            for other_rule in managed_rules.values():
                if other_rule.get("hostname_for_dns") == hostname_for_dns:
                    is_dns_shared = True
                    break
        if not is_dns_shared:
            if not delete_cloudflare_dns_record(zone_id_for_delete, hostname_for_dns, effective_tunnel_id):
                dns_deleted = False
        else:
            logging.info(f"API Force Delete: DNS for {hostname_for_dns} (rule {rule_key}) not deleted as it's shared.")

    access_app_deleted = True 
    if access_app_id_for_delete:
        is_app_shared = False
        with state_lock:
            for other_rule in managed_rules.values():
                if other_rule.get("access_app_id") == access_app_id_for_delete:
                    is_app_shared = True
                    break
        if not is_app_shared:
            if not delete_cloudflare_access_application(access_app_id_for_delete):
                access_app_deleted = False
        else:
            logging.info(f"API Force Delete: Access App {access_app_id_for_delete} (rule {rule_key}) not deleted as it's shared.")

    config_updated = update_cloudflare_config()

    status_code = 200
    results = {
        "dns_deleted": dns_deleted,
        "access_app_deleted": access_app_deleted,
        "config_updated": config_updated
    }
    if not all(results.values()):
        status_code = 207 

    return jsonify({
        "status": "success" if status_code == 200 else "warning",
        "message": f"Rule '{rule_key}' force deleted. See details.",
        "details": results
    }), status_code


@api_v2_bp.route('/rules/<path:rule_key>/access-policy', methods=['PUT'])
def update_rule_access_policy(rule_key):
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client unavailable."}), 503

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON payload."}), 400

    new_policy_type = data.get('access_policy_type') 
    auth_email = data.get('auth_email', '').strip()
    session_duration = data.get('session_duration', '24h') 
    app_launcher_visible = data.get('app_launcher_visible', False)
    allowed_idps_str = data.get('allowed_idps_str') 
    auto_redirect = data.get('auto_redirect', False)
    
    action_status_message = f"Processing UI policy update for {rule_key}..."
    state_changed_locally = False
    operation_successful = False
    final_rule_state = None

    with state_lock:
        current_rule = managed_rules.get(rule_key)
        if not current_rule:
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' not found."}), 404
        
        hostname_for_access_app = current_rule.get("hostname_for_dns") 
        if not hostname_for_access_app:
             return jsonify({"status": "error", "message": f"Cannot determine hostname for Access App for rule '{rule_key}'."}), 400


        current_access_app_id = current_rule.get("access_app_id")
        session_duration = data.get('session_duration', current_rule.get("access_session_duration", "24h"))
        app_launcher_visible = data.get('app_launcher_visible', current_rule.get("access_app_launcher_visible", False))
        allowed_idps_str = data.get('allowed_idps_str', current_rule.get("access_allowed_idps_str"))
        auto_redirect = data.get('auto_redirect', current_rule.get("access_auto_redirect", False))

        desired_app_name = f"DockFlare-{hostname_for_access_app}" 
        cf_access_policies = []
        final_policy_type_for_state = new_policy_type
        custom_rules_for_hash = None

        if new_policy_type == "none" or new_policy_type == "public_no_policy":
            if current_access_app_id:
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = None
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                    operation_successful = True
                else: action_status_message = f"Error: Failed to delete Access App for {rule_key}."
            else: 
                if current_rule.get("access_policy_type") is not None:
                    current_rule["access_policy_type"] = None
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
            final_policy_type_for_state = None
        
        elif new_policy_type == "default_tld":
            if current_access_app_id: 
                if delete_cloudflare_access_application(current_access_app_id):
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None 
                    state_changed_locally = True
                    operation_successful = True
                else: action_status_message = f"Error: Failed to delete Access App for {rule_key} for TLD switch."
            else: 
                if current_rule.get("access_policy_type") != "default_tld":
                    current_rule["access_app_id"] = None
                    current_rule["access_policy_type"] = "default_tld"
                    current_rule["access_app_config_hash"] = None
                    state_changed_locally = True
                operation_successful = True
            final_policy_type_for_state = "default_tld"

        elif new_policy_type == "bypass":
            cf_access_policies = [{"name": "API Public Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            custom_rules_for_hash = json.dumps(cf_access_policies)
        
        elif new_policy_type == "authenticate_email":
            if not auth_email:
                return jsonify({"status": "error", "message": "Auth Email required for 'authenticate_email' policy."}), 400
            cf_access_policies = [
                {"name": f"API Allow Email {auth_email}", "decision": "allow", "include": [{"email": {"email": auth_email}}]},
                {"name": "API Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}
            ]
            custom_rules_for_hash = json.dumps(cf_access_policies)
        
        if new_policy_type in ["bypass", "authenticate_email"]:
            if not cf_access_policies: 
                return jsonify({"status": "error", "message": "Internal: No policies defined."}), 500
            
            new_config_hash = generate_access_app_config_hash(
                final_policy_type_for_state, session_duration, app_launcher_visible,
                allowed_idps_str, auto_redirect, custom_access_rules_str=custom_rules_for_hash
            )
            allowed_idps_list_for_app = [idp.strip() for idp in allowed_idps_str.split(',') if idp.strip()] if allowed_idps_str else None

            effective_app_id_for_operation = current_access_app_id
            if not effective_app_id_for_operation: 
                existing_cf_app = find_cloudflare_access_application_by_hostname(hostname_for_access_app)
                if existing_cf_app and existing_cf_app.get("id"):
                    effective_app_id_for_operation = existing_cf_app.get("id")
                    current_rule["access_app_id"] = effective_app_id_for_operation 
                    state_changed_locally = True
            
            if effective_app_id_for_operation: 
                if current_rule.get("access_policy_type") != final_policy_type_for_state or \
                   current_rule.get("access_app_config_hash") != new_config_hash or \
                   current_rule.get("access_app_id") != effective_app_id_for_operation: 
                    
                    updated_app = update_cloudflare_access_application(
                        effective_app_id_for_operation, hostname_for_access_app, desired_app_name,
                        session_duration, app_launcher_visible, [hostname_for_access_app],
                        cf_access_policies, allowed_idps_list_for_app, auto_redirect
                    )
                    if updated_app:
                        current_rule["access_app_id"] = updated_app.get("id")
                        current_rule["access_policy_type"] = final_policy_type_for_state
                        current_rule["access_app_config_hash"] = new_config_hash
                        # Update other access params in current_rule
                        current_rule["access_session_duration"] = session_duration
                        current_rule["access_app_launcher_visible"] = app_launcher_visible
                        current_rule["access_allowed_idps_str"] = allowed_idps_str
                        current_rule["access_auto_redirect"] = auto_redirect
                        current_rule["auth_email"] = auth_email if final_policy_type_for_state == "authenticate_email" else None
                        state_changed_locally = True; operation_successful = True
                    else: action_status_message = f"Error: Failed to update Access App for {rule_key}."
                else: # No change needed
                    operation_successful = True; action_status_message = "No change in policy needed."
            else: # Create new
                created_app = create_cloudflare_access_application(
                    hostname_for_access_app, desired_app_name,
                    session_duration, app_launcher_visible, [hostname_for_access_app],
                    cf_access_policies, allowed_idps_list_for_app, auto_redirect
                )
                if created_app and created_app.get("id"):
                    current_rule["access_app_id"] = created_app.get("id")
                    current_rule["access_policy_type"] = final_policy_type_for_state
                    current_rule["access_app_config_hash"] = new_config_hash
                    current_rule["access_session_duration"] = session_duration
                    current_rule["access_app_launcher_visible"] = app_launcher_visible
                    current_rule["access_allowed_idps_str"] = allowed_idps_str
                    current_rule["access_auto_redirect"] = auto_redirect
                    current_rule["auth_email"] = auth_email if final_policy_type_for_state == "authenticate_email" else None
                    state_changed_locally = True; operation_successful = True
                else: action_status_message = f"Error: Failed to create Access App for {rule_key}."

        if operation_successful:
            current_rule["access_policy_ui_override"] = True 
            state_changed_locally = True 

        if state_changed_locally:
            save_state()
        
        final_rule_state = serialize_rule(current_rule)

    if operation_successful:
        return jsonify({"status": "success", "message": f"Access policy for {rule_key} updated to {final_policy_type_for_state}.", "rule": final_rule_state}), 200
    else:
        return jsonify({"status": "error", "message": action_status_message, "rule": final_rule_state}), 500

@api_v2_bp.route('/rules/<path:rule_key>/access-policy/revert-to-labels', methods=['POST'])
def revert_rule_access_policy_to_labels(rule_key):
    if not docker_client:
        return jsonify({"status": "error", "message": "Docker client unavailable."}), 503

    app_id_to_delete_if_any = None
    state_changed_for_revert = False
    initial_rule_source = None

    with state_lock:
        current_rule = managed_rules.get(rule_key)
        if not current_rule:
            return jsonify({"status": "error", "message": f"Rule '{rule_key}' not found."}), 404
        
        initial_rule_source = current_rule.get("source")
        if not current_rule.get("access_policy_ui_override", False):
            return jsonify({"status": "info", "message": f"Access policy for '{rule_key}' is not UI-overridden. No action taken."}), 200


        if initial_rule_source == "manual":
            app_id_to_delete_if_any = current_rule.get("access_app_id")
            current_rule["access_policy_ui_override"] = False
            current_rule["access_app_id"] = None
            current_rule["access_policy_type"] = None 
            current_rule["access_app_config_hash"] = None
            current_rule["access_session_duration"] = "24h" # Default
            current_rule["access_app_launcher_visible"] = False
            current_rule["access_allowed_idps_str"] = None
            current_rule["access_auto_redirect"] = False
            current_rule["auth_email"] = None
            state_changed_for_revert = True
            logging.info(f"API: Reverting manual rule '{rule_key}' access policy to none/public.")
        elif initial_rule_source == "docker":
            current_rule["access_policy_ui_override"] = False
            state_changed_for_revert = True
            logging.info(f"API: Reverting Docker rule '{rule_key}' access policy to be label-driven.")
        else: 
             return jsonify({"status": "error", "message": f"Rule '{rule_key}' has unknown source '{initial_rule_source}'."}), 500

        if state_changed_for_revert:
            save_state()

    if initial_rule_source == "manual" and app_id_to_delete_if_any:
        is_shared = False
        with state_lock:
            for r_key, r_val in managed_rules.items():
                if r_key != rule_key and r_val.get("access_app_id") == app_id_to_delete_if_any:
                    is_shared = True
                    break
        if not is_shared:
            if delete_cloudflare_access_application(app_id_to_delete_if_any):
                logging.info(f"API: Deleted Access App {app_id_to_delete_if_any} for reverted manual rule '{rule_key}'.")
            else:
                logging.warning(f"API: Failed to delete Access App {app_id_to_delete_if_any} for reverted manual rule '{rule_key}'.")
        else:
            logging.info(f"API: Access App {app_id_to_delete_if_any} for reverted manual rule '{rule_key}' is shared, not deleting.")

    reconcile_state_threaded()
    return jsonify({"status": "success", "message": f"Access policy for '{rule_key}' reverted. Reconciliation triggered."}), 202 

@api_v2_bp.route('/tunnels/account', methods=['GET'])
def get_account_tunnels_api():
    tunnels = get_all_account_cloudflare_tunnels()
    return jsonify({"tunnels": tunnels})

@api_v2_bp.route('/tunnels/<tunnel_id>/dns-records', methods=['GET'])
def get_tunnel_dns_records_api(tunnel_id):
    if not tunnel_id:
        return jsonify({"error": "Tunnel ID is required"}), 400
    
    all_found_dns_records = []
    zone_ids_to_scan = set()
    if config.CF_ZONE_ID:
        zone_ids_to_scan.add(config.CF_ZONE_ID)
    
    scan_zone_names_list = getattr(config, 'TUNNEL_DNS_SCAN_ZONE_NAMES', [])
    if isinstance(scan_zone_names_list, str) and scan_zone_names_list: 
        scan_zone_names_list = [z.strip() for z in scan_zone_names_list.split(',')]

    for zone_name in scan_zone_names_list:
        resolved_zone_id = get_zone_id_from_name(zone_name)
        if resolved_zone_id:
            zone_ids_to_scan.add(resolved_zone_id)
    
    if not zone_ids_to_scan:
        return jsonify({"dns_records": [], "message": "No zones configured or resolved for DNS scan."})

    for z_id in zone_ids_to_scan:
        records_in_zone = get_dns_records_for_tunnel(z_id, tunnel_id)
        if records_in_zone: 
            all_found_dns_records.extend(records_in_zone)
    
    all_found_dns_records.sort(key=lambda r: r.get("name", "").lower()) 
    return jsonify({"dns_records": all_found_dns_records})

@api_v2_bp.route('/ping', methods=['GET'])
def ping_api():
    return jsonify({
        "status": "ok",
        "timestamp": int(time.time()),
        "version": current_app.config.get('APP_VERSION', 'unknown'), 
        "message": "DockFlare API is responsive."
    })

@api_v2_bp.route('/debug-info', methods=['GET']) 
def debug_info_api():
    try:
        headers = {k: v for k, v in request.headers.items()}
        env_vars = {
            "wsgi.url_scheme": request.environ.get('wsgi.url_scheme'),
            "HTTP_X_FORWARDED_PROTO": request.environ.get('HTTP_X_FORWARDED_PROTO')
        }
        return jsonify({
            "request_info": {
                "scheme": request.scheme, "is_secure": request.is_secure,
                "host": request.host, "path": request.path, "url": request.url,
                "remote_addr": request.remote_addr, "headers": headers
            },
            "environment_info": env_vars,
            "flask_config_preferred_url_scheme": current_app.config.get('PREFERRED_URL_SCHEME'),
            "timestamp": int(time.time())
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "traceback": traceback.format_exc()}), 500