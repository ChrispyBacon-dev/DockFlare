import logging
from flask import Flask, render_template, request, url_for, jsonify, Response, redirect
import os
import copy
from datetime import datetime, timezone, timedelta
import time
import json
import hashlib # For generate_access_app_config_hash
import threading # For state_lock

# --- Global Variables and Constants (mimicking your full app) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s')

# Flask App Setup
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Cloudflare Configuration (use dummies or actual from os.getenv if testing full functionality later)
CF_API_TOKEN = os.getenv('CF_API_TOKEN', "dummy_api_token")
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID', "dummy_account_id")
CF_ZONE_ID = os.getenv('CF_ZONE_ID', None) # Important for add_manual_host logic
CF_API_BASE_URL = "https://api.cloudflare.com/client/v4" # Needed if cf_api_request is real
CF_HEADERS = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json",
}


# DockFlare Configuration
USE_EXTERNAL_CLOUDFLARED = os.getenv('USE_EXTERNAL_CLOUDFLARED', 'false').lower() in ['true', '1']
EXTERNAL_TUNNEL_ID = os.getenv('EXTERNAL_TUNNEL_ID', None)
CLOUDFLARED_CONTAINER_NAME = "test-agent-minimal" # Dummy for display
TUNNEL_NAME = "test-tunnel" # Dummy for display

# State Variables
state_lock = threading.Lock()
tunnel_state = {
    "name": TUNNEL_NAME, "id": "test-id-from-state", "token": "test-token-value-from-state",
    "status_message": "Nominal", "error": None
}
cloudflared_agent_state = { # Used by add_manual_host to set last_action_status
    "container_status": "running",
    "last_action_status": None
}
managed_rules = {} # This will be modified by add_manual_host
zone_id_cache = {} # Used by get_zone_id_from_name
docker_client = True # Dummy, for docker_available check in template

# Cache for get_all_account_cloudflare_tunnels
_all_tunnels_cache = []
_all_tunnels_cache_time = 0
_ALL_TUNNELS_CACHE_TTL = 120

# --- Minimal Helper Function Implementations or Stubs ---
def cf_api_request(method, endpoint, json_data=None, params=None): # STUB
    logging.info(f"STUB cf_api_request: {method} {endpoint} Data: {json_data} Params: {params}")
    if "access/apps" in endpoint and method == "POST": # For create_cloudflare_access_application
        return {"success": True, "result": {"id": "stub_app_id_" + str(time.time())}}
    if "dns_records" in endpoint and method == "POST": # For create_cloudflare_dns_record
        return {"success": True, "result": {"id": "stub_dns_id_" + str(time.time())}}
    if "configurations" in endpoint and method == "PUT": # For update_cloudflare_config
        return {"success": True, "result": {}}
    # Add more specific stubs if other API calls are made by helpers
    return {"success": True, "result": []} # Generic success

def get_zone_id_from_name(zone_name): # STUB - important for add_manual_host
    with state_lock:
        if zone_name in zone_id_cache: return zone_id_cache[zone_name]
    logging.info(f"STUB get_zone_id_from_name for: {zone_name}")
    if zone_name == "example.com": # Simulate finding a zone
        found_id = "zone_id_for_example_com"
        with state_lock: zone_id_cache[zone_name] = found_id
        return found_id
    return None # Simulate not found

def get_zone_details_by_id(zone_id): # STUB - important for add_manual_host
    logging.info(f"STUB get_zone_details_by_id for: {zone_id}")
    if zone_id == CF_ZONE_ID and CF_ZONE_ID is not None:
        return {"name": "default.com"} # Simulate finding the default zone name
    if zone_id == "zone_id_for_example_com":
        return {"name": "example.com"}
    return None

def is_valid_hostname(hostname): return bool(hostname) and len(hostname) > 3 # Simplified STUB
def is_valid_service_url(url_string): return url_string.startswith("http") # Simplified STUB

def save_state():
    logging.info(f"STUB save_state called. Current managed_rules count: {len(managed_rules)}")
    # For a real test of add_manual_host functionality, you'd want this to actually save.
    pass

def generate_access_app_config_hash(policy_type, session_duration, app_launcher_visible, allowed_idps_str, auto_redirect_to_identity, custom_access_rules_str=None):
    # This is your actual hash function, good to keep
    config_items = {
        "policy_type": policy_type, "session_duration": session_duration,
        "app_launcher_visible": app_launcher_visible, "allowed_idps_str": allowed_idps_str,
        "auto_redirect_to_identity": auto_redirect_to_identity,
        "custom_access_rules_str": custom_access_rules_str
    }
    consistent_config_string = json.dumps(config_items, sort_keys=True)
    hasher = hashlib.sha256()
    hasher.update(consistent_config_string.encode('utf-8'))
    return hasher.hexdigest()

def create_cloudflare_access_application(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    # Uses the stubbed cf_api_request
    logging.info(f"STUB create_cloudflare_access_application for: {hostname}")
    # Simulate payload building for logging or simple checks
    payload = { "name": name, "domain": hostname, "type": "self_hosted", "policies": access_policies}
    response = cf_api_request("POST", f"/accounts/{CF_ACCOUNT_ID}/access/apps", json_data=payload)
    return response.get("result") if response and response.get("success") else None

def update_cloudflare_config(): # STUB
    logging.info("STUB update_cloudflare_config called")
    return True # Simulate success

def create_cloudflare_dns_record(zone_id, hostname, tunnel_id): # STUB
    logging.info(f"STUB create_cloudflare_dns_record for: {hostname} in zone {zone_id}")
    response = cf_api_request("POST", f"/zones/{zone_id}/dns_records", json_data={"name": hostname, "content": tunnel_id})
    return response.get("result", {}).get("id") if response and response.get("success") else None

def get_display_token(token):
    if not token: return "Not available"
    return f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "Token (short)"

def get_all_account_cloudflare_tunnels():
    global _all_tunnels_cache, _all_tunnels_cache_time
    current_time = time.time()
    with state_lock:
        if _all_tunnels_cache is not None and (current_time - _all_tunnels_cache_time < _ALL_TUNNELS_CACHE_TTL):
            logging.info("Returning all_account_tunnels from cache.")
            return copy.deepcopy(_all_tunnels_cache)
    logging.info("Cache miss for all_account_tunnels, returning empty for this test (simulating API call).")
    simulated_tunnels = []
    with state_lock:
        _all_tunnels_cache = simulated_tunnels
        _all_tunnels_cache_time = current_time
    return copy.deepcopy(simulated_tunnels)
# --- End Helper Functions ---

# --- Flask Hooks and Context Processors ---
@app.before_request
def detect_protocol():
    # ... (same as before)
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    app.config['PREFERRED_URL_SCHEME'] = 'https' if forwarded_proto == 'https' or request.is_secure else 'http'

@app.after_request
def add_security_headers(response):
    # ... (same as before)
    response.headers['X-Content-Type-Options'] = 'nosniff'; response.headers['X-Frame-Options'] = 'SAMEORIGIN'; response.headers['X-XSS-Protection'] = '1; mode=block' # Simplified
    return response

@app.context_processor
def inject_protocol():
    # ... (same as before)
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    is_https = forwarded_proto == 'https' or request.is_secure
    base_url = f"{'https' if is_https else 'http'}://{request.host}"
    request_scheme = request.scheme
    return {
        'protocol': 'https' if is_https else 'http',
        'is_https': is_https,
        'base_url': base_url,
        'host': request.host,
        'request_scheme': request_scheme
    }
# --- End Hooks ---

# --- Main Routes ---
@app.route('/')
def status_page():
    logging.info("Attempting to render status_page.html (for Step N)")
    try:
        # Use the more complete global state variables now
        rules_for_template = {}
        with state_lock:
            for hostname, rule in managed_rules.items():
                rule_copy = copy.deepcopy(rule)
                if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
                    rule_copy["delete_at"] = rule_copy["delete_at"].astimezone(timezone.utc)
                rules_for_template[hostname] = rule_copy
        
        current_tunnel_state = {}
        with state_lock: current_tunnel_state = tunnel_state.copy()
        
        current_agent_state = {}
        with state_lock: current_agent_state = cloudflared_agent_state.copy()

        display_token_val = get_display_token(current_tunnel_state.get("token"))
        docker_available_val = docker_client is not None
        all_account_tunnels_list_val = get_all_account_cloudflare_tunnels() # Uses cache

        return render_template('status_page.html',
                            tunnel_state=current_tunnel_state,
                            agent_state=current_agent_state,
                            initialization={"complete": True, "in_progress": False}, # Simplified for test
                            display_token=display_token_val,
                            cloudflared_container_name=CLOUDFLARED_CONTAINER_NAME,
                            docker_available=docker_available_val,
                            external_cloudflared=USE_EXTERNAL_CLOUDFLARED,
                            external_tunnel_id=EXTERNAL_TUNNEL_ID,
                            rules=rules_for_template,
                            all_account_tunnels=all_account_tunnels_list_val,
                            CF_ACCOUNT_ID_CONFIGURED=bool(CF_ACCOUNT_ID),
                            ACCOUNT_ID_FOR_DISPLAY=CF_ACCOUNT_ID if CF_ACCOUNT_ID else "Not Configured",
                            CF_ZONE_ID_CONFIGURED=bool(CF_ZONE_ID)
                            )
    except Exception as e:
        logging.error(f"Error rendering status_page.html (Step N): {e}", exc_info=True)
        return f"Error rendering template: {e}", 500

# --- YOUR ACTUAL add_manual_host FUNCTION ---
@app.route('/add_manual_host', methods=['POST'])
def add_manual_host():
    # This is the function you provided
    if not (tunnel_state.get("id") or (USE_EXTERNAL_CLOUDFLARED and EXTERNAL_TUNNEL_ID)):
        cloudflared_agent_state["last_action_status"] = "Error: Cannot add manual host - system not fully initialized or tunnel ID missing."
        return redirect(url_for('status_page'))

    hostname = request.form.get('manual_hostname', '').strip()
    service_target = request.form.get('manual_service_target', '').strip()
    zone_name_manual = request.form.get('manual_zone_name', '').strip()
    no_tls_verify_manual_str = request.form.get('manual_no_tls_verify')
    no_tls_verify_manual = no_tls_verify_manual_str == 'true'

    access_policy_type_manual = request.form.get('manual_access_policy_type')
    auth_email_manual = request.form.get('manual_auth_email', '').strip()
    session_duration_manual = request.form.get("session_duration", "24h")
    app_launcher_visible_manual = request.form.get("app_launcher_visible", "false").lower() in ["true", "1", "t", "yes"]
    allowed_idps_manual_str = request.form.get("allowed_idps", "")
    auto_redirect_manual = request.form.get("auto_redirect", "false").lower() in ["true", "1", "t", "yes"]

    action_status_message = f"Processing add manual host: {hostname}"
    logging.info(action_status_message)

    if not is_valid_hostname(hostname): # Uses stub or your actual function
        cloudflared_agent_state["last_action_status"] = f"Error: Invalid hostname '{hostname}' for manual rule."
        return redirect(url_for('status_page'))
    if not is_valid_service_url(service_target): # Uses stub or your actual function
        cloudflared_agent_state["last_action_status"] = f"Error: Invalid service target URL '{service_target}'. Must be like 'http(s)://host:port'."
        return redirect(url_for('status_page'))

    target_zone_id_manual = None
    target_zone_name_str = ""
    if zone_name_manual:
        target_zone_id_manual = get_zone_id_from_name(zone_name_manual) # Uses stub or your actual
        if not target_zone_id_manual:
            cloudflared_agent_state["last_action_status"] = f"Error: Could not find Zone ID for '{zone_name_manual}'."
            return redirect(url_for('status_page'))
        target_zone_name_str = zone_name_manual
    elif CF_ZONE_ID:
        target_zone_id_manual = CF_ZONE_ID
        zone_details = get_zone_details_by_id(CF_ZONE_ID) # Uses stub or your actual
        if zone_details: target_zone_name_str = zone_details.get("name", "")
    else:
        cloudflared_agent_state["last_action_status"] = "Error: CF_ZONE_ID is not set, and no zone name was provided for the manual host."
        return redirect(url_for('status_page'))

    with state_lock:
        if hostname in managed_rules:
            cloudflared_agent_state["last_action_status"] = f"Error: Hostname '{hostname}' is already managed."
            return redirect(url_for('status_page'))

        new_manual_rule_staging = {
            "service": service_target, "container_id": None, "management_type": "manual",
            "status": "active", "delete_at": None, "zone_id": target_zone_id_manual,
            "zone_name_used": target_zone_name_str, "no_tls_verify": no_tls_verify_manual,
            "access_app_id": None, "access_policy_type": None,
            "access_app_config_hash": None, "access_policy_ui_override": True
        }
        temp_access_app_id = None; temp_access_policy_type = None; temp_access_app_config_hash = None
        access_policy_setup_ok = False; desired_app_name_manual = f"DockFlare-Manual-{hostname}"
        cf_access_policies_manual = []; custom_rules_for_hash_manual = None

        if access_policy_type_manual == "none" or access_policy_type_manual == "public_no_policy":
            temp_access_policy_type = None; access_policy_setup_ok = True
        elif access_policy_type_manual == "default_tld":
            temp_access_policy_type = "default_tld"; access_policy_setup_ok = True
        elif access_policy_type_manual == "bypass":
            cf_access_policies_manual = [{"name": "Manual UI Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            temp_access_policy_type = "bypass"
        elif access_policy_type_manual == "authenticate_email":
            if not auth_email_manual:
                cloudflared_agent_state["last_action_status"] = f"Error: Email required for 'authenticate_email' policy for {hostname}."
                return redirect(url_for('status_page'))
            cf_access_policies_manual = [
                {"name": f"Manual UI Allow {auth_email_manual}", "decision": "allow", "include": [{"email": {"email": auth_email_manual}}]},
                {"name": "Manual UI Deny Fallback", "decision": "deny", "include": [{"everyone": {}}]}]; temp_access_policy_type = "authenticate_email"

        if access_policy_type_manual in ["bypass", "authenticate_email"]:
            if not cf_access_policies_manual:
                cloudflared_agent_state["last_action_status"] = f"Error: Internal - policy definition missing for {access_policy_type_manual}."
                return redirect(url_for('status_page'))
            temp_access_app_config_hash = generate_access_app_config_hash(
                temp_access_policy_type, session_duration_manual, app_launcher_visible_manual,
                allowed_idps_manual_str, auto_redirect_manual, custom_rules_for_hash_manual)
            allowed_idps_list = [idp.strip() for idp in allowed_idps_manual_str.split(',') if idp.strip()] if allowed_idps_manual_str else None
            created_app = create_cloudflare_access_application( # Uses stub or your actual
                hostname, desired_app_name_manual, session_duration_manual, app_launcher_visible_manual,
                [hostname], cf_access_policies_manual, allowed_idps_list, auto_redirect_manual)
            if created_app and created_app.get("id"):
                temp_access_app_id = created_app.get("id"); access_policy_setup_ok = True
            else:
                action_status_message = f"Error: Failed to create Access App for {hostname} (policy: {temp_access_policy_type}). Rule not added."
                cloudflared_agent_state["last_action_status"] = action_status_message; logging.error(action_status_message)
                return redirect(url_for('status_page'))
        if access_policy_setup_ok:
            new_manual_rule_staging["access_app_id"] = temp_access_app_id
            new_manual_rule_staging["access_policy_type"] = temp_access_policy_type
            new_manual_rule_staging["access_app_config_hash"] = temp_access_app_config_hash
            managed_rules[hostname] = new_manual_rule_staging
            save_state() # Uses stub or your actual
            logging.info(f"Added manual rule for {hostname} to state.")
        else:
            cloudflared_agent_state["last_action_status"] = f"Error: Access Policy setup failed for {hostname}. Rule not added."
            return redirect(url_for('status_page'))

    config_updated_successfully = False
    if not USE_EXTERNAL_CLOUDFLARED:
        if update_cloudflare_config(): # Uses stub or your actual
            logging.info(f"Cloudflare tunnel config updated for manual host {hostname}.")
            config_updated_successfully = True
        else:
            action_status_message = f"Error: Added manual rule {hostname} to state, but FAILED to update Cloudflare tunnel config."
            logging.error(action_status_message)
    else:
        config_updated_successfully = True
        logging.info(f"External mode: Manual rule {hostname} added. DNS will be managed.")

    if config_updated_successfully:
        effective_tunnel_id_for_dns = tunnel_state.get("id") if not USE_EXTERNAL_CLOUDFLARED else EXTERNAL_TUNNEL_ID
        if effective_tunnel_id_for_dns:
            dns_record_id = create_cloudflare_dns_record(target_zone_id_manual, hostname, effective_tunnel_id_for_dns) # Uses stub or your actual
            if dns_record_id:
                action_status_message = f"Successfully added manual host {hostname}, updated config, and created DNS record."
            else:
                action_status_message = f"Warning: Added manual host {hostname} and updated config, but DNS record creation FAILED in zone {target_zone_id_manual}."
        else:
             action_status_message = f"Error: Added manual host {hostname}, but tunnel ID missing for DNS creation."
    else:
        action_status_message = f"Error: Added {hostname} to state, but failed tunnel config update. DNS not created."

    cloudflared_agent_state["last_action_status"] = action_status_message
    logging.info(action_status_message)
    return redirect(url_for('status_page'))
# --- End of add_manual_host ---

# --- Other DUMMY Route Definitions ---
@app.route('/stop-tunnel', methods=['POST'])
def stop_tunnel():
    logging.info("Dummy stop_tunnel route called")
    return redirect(url_for('status_page'))

@app.route('/start-tunnel', methods=['POST'])
def start_tunnel():
    logging.info("Dummy start_tunnel route called")
    return redirect(url_for('status_page'))

@app.route('/stream-logs')
def stream_logs():
    logging.info("Dummy stream_logs route")
    def dummy_stream(): yield "data: dummy log\n\n"
    return Response(dummy_stream(), mimetype='text/event-stream')

@app.route('/reconciliation-status')
def reconciliation_status():
    logging.info("Dummy reconciliation_status route")
    return jsonify({"in_progress": False, "status": "Dummy status"})

@app.route('/ping')
def ping():
    logging.info("Dummy ping route")
    return jsonify({"status": "ok"})

# Routes that would be needed if "Managed Ingress Rules" is active
@app.route('/ui_update_access_policy/<path:hostname>', methods=['POST'])
def ui_update_access_policy(hostname):
    logging.info(f"Dummy ui_update_access_policy for {hostname}")
    return redirect(url_for('status_page'))

@app.route('/revert_access_policy_to_labels/<path:hostname>', methods=['POST'])
def revert_access_policy_to_labels(hostname):
    logging.info(f"Dummy revert_access_policy_to_labels for {hostname}")
    return redirect(url_for('status_page'))

@app.route('/delete_manual_host/<path:hostname>', methods=['POST'])
def delete_manual_host(hostname):
    logging.info(f"Dummy delete_manual_host for {hostname}")
    return redirect(url_for('status_page'))

@app.route('/force_delete_rule/<path:hostname>', methods=['POST'])
def force_delete_rule(hostname):
    logging.info(f"Dummy force_delete_rule for {hostname}")
    return redirect(url_for('status_page'))

@app.route('/tunnel-dns-records/<path:tunnel_id>')
def tunnel_dns_records(tunnel_id):
    logging.info(f"Dummy tunnel_dns_records for {tunnel_id}")
    return jsonify({"dns_records": []})
# --- End DUMMY Routes ---

if __name__ == '__main__':
    logging.info("Starting Flask app for Step N testing (with actual add_manual_host).")
    app.run(host='0.0.0.0', port=5000, debug=True)