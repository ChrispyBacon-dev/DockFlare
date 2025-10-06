# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute and/or modify
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
# dockflare/app/web/routes.py
import copy
import logging
import time
import os
import random
import queue
import uuid
from datetime import datetime, timezone
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import send_file
from flask import (
    Blueprint, render_template, jsonify, redirect, url_for, request, Response,
    current_app, session, flash
)
from flask_login import current_user, login_required, login_user, logout_user
from app.core.user import User

from app import config, docker_client, tunnel_state, cloudflared_agent_state, log_queue, state_update_queue, publish_state_event, limiter
from app.core.cache import CACHE_ENABLED
from app.core.state_manager import managed_rules, access_groups, state_lock, save_state, load_state
from app.core.tunnel_manager import (
    start_cloudflared_container,
    stop_cloudflared_container,
    update_cloudflare_config,
    initialize_tunnel
)
from app.core.cloudflare_api import (
    get_all_account_cloudflare_tunnels,
    get_dns_records_for_tunnel,
    create_cloudflare_dns_record,
    delete_cloudflare_dns_record,
    get_zone_id_from_name,
    get_zone_details_by_id,
    list_account_zones,
    delete_tunnel_via_api,
    get_tunnel_name_by_id
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
from app.core import backup_manager
from app.web import config_loader
from cryptography.fernet import Fernet

bp = Blueprint('web', __name__)

@bp.route('/agents')
@login_required
def agents_page():
    from app.core.state_manager import list_agents
    with state_lock:
        agents = list_agents()
    return render_template('agents.html', agents=agents)

@bp.route('/agents/<agent_id>/roll-key', methods=['POST'])
@login_required
def roll_agent_key(agent_id):
    """
    Rolls (regenerates) the API key for a specific agent.
    """
    from app.core.state_manager import get_agent, update_agent, revoke_agent_key, add_agent_key
    import secrets
    from datetime import datetime, timezone

    if not agent_id:
        cloudflared_agent_state["last_action_status"] = "Error: Missing agent ID."
        return redirect(url_for('web.agents_page'))

    with state_lock:
        agent = get_agent(agent_id)
        if not agent:
            cloudflared_agent_state["last_action_status"] = f"Error: Agent '{agent_id}' not found."
            return redirect(url_for('web.agents_page'))

        old_api_key = agent.get("api_key")

        new_api_key = secrets.token_urlsafe(32)

        success = update_agent(agent_id, {"api_key": new_api_key})
        if not success:
            cloudflared_agent_state["last_action_status"] = f"Error: Failed to update agent '{agent_id}' with new API key."
            return redirect(url_for('web.agents_page'))

        if old_api_key:
            revoke_agent_key(old_api_key)

        now_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
        add_agent_key(new_api_key, {
            "bound_agent_id": agent_id,
            "created_at": now_iso,
            "last_used_at": None,
            "rolled_from": old_api_key[:8] + "..." if old_api_key else None
        })

        cloudflared_agent_state["last_action_status"] = f"Success: API key rolled for agent '{agent.get('display_name', agent_id)}'. Agent must be restarted with new key: {new_api_key}"

    return redirect(url_for('web.agents_page'))

def get_display_token_ui(token_value):
    if not token_value:
        return "Not available"
    return f"{token_value[:5]}...{token_value[-5:]}" if len(token_value) > 10 else "Token (short)"

@bp.before_app_request
def gating_logic():

    data_path = os.path.dirname(config.STATE_FILE_PATH)
    config_file = os.path.join(data_path, 'dockflare_config.dat')
    key_file = os.path.join(data_path, 'dockflare.key')
    files_present = os.path.exists(config_file) and os.path.exists(key_file)
    is_configured = bool(current_app.config.get('DOCKFLARE_PASSWORD_HASH')) or getattr(current_app, 'is_configured', False) or files_present

    if not is_configured:

        if request.endpoint and not request.endpoint.startswith('setup.') and request.endpoint != 'static' and not request.endpoint.startswith('api_v2.'):
            try:
                if getattr(current_app, 'import_from_env', False):

                    session['is_env_import'] = True
                    session['cf_api_token'] = os.getenv('CF_API_TOKEN')
                    session['cf_account_id'] = os.getenv('CF_ACCOUNT_ID')
                    session['tunnel_name'] = os.getenv('TUNNEL_NAME', 'dockflare-tunnel')
                    session['cf_zone_id'] = os.getenv('CF_ZONE_ID')
                    session['tunnel_dns_scan_zone_names'] = os.getenv('TUNNEL_DNS_SCAN_ZONE_NAMES', '')
                    session['master_api_key'] = os.getenv('DOCKFLARE_API_KEY')

                    grace_period_str = os.getenv('GRACE_PERIOD_SECONDS', '28800')
                    session['grace_period_seconds'] = int(grace_period_str) if grace_period_str.isdigit() else 28800


                    return redirect(url_for('setup.step_import_env'))
                else:

                    return redirect(url_for('setup.step1_admin_user'))
            except Exception as e:
                logging.error(f"Error during setup redirection logic: {e}", exc_info=True)

                return "Application is initializing setup. Please try again in a moment.", 503
        return


    if hasattr(current_app, 'login_manager'):
        if current_app.config.get('DISABLE_PASSWORD_LOGIN'):
            logging.info(f"DISABLE_PASSWORD_LOGIN is True, checking authentication bypass")
            oauth_providers = current_app.config.get('OAUTH_PROVIDERS', [])
            enabled_oauth_providers = [p for p in oauth_providers if p.get('enabled', True)]
            logging.info(f"OAuth providers: {len(oauth_providers)}, Enabled: {len(enabled_oauth_providers)}")
            if not current_user.is_authenticated:
                logging.info("Bypassing authentication - logging in anonymous user")
                login_user(User("anonymous", auth_method='disabled'))
            return

        if not current_user.is_authenticated:
            exempt_endpoints = ['static', 'web.ping', 'web.cloudflare_ping_route', 'setup.step_import_env']
            oauth_endpoints = ['web.login_provider', 'web.auth_callback', 'web.login']
            if request.endpoint and not request.endpoint.startswith('auth.') and request.endpoint not in exempt_endpoints and request.endpoint not in oauth_endpoints:
                try:
                    return redirect(url_for('web.login'))
                except Exception:
                    pass

@bp.before_app_request
def detect_protocol_bp():
    forwarded_proto = request.headers.get('X-Forwarded-Proto', '').lower()
    if forwarded_proto == 'https':
        current_app.config['PREFERRED_URL_SCHEME'] = 'https'
        return

    cf_visitor = request.headers.get('Cf-Visitor')
    if cf_visitor:
        try:
            visitor_data = json.loads(cf_visitor)
            if visitor_data.get('scheme') == 'https':
                current_app.config['PREFERRED_URL_SCHEME'] = 'https'
                return
        except (json.JSONDecodeError, TypeError):
            pass

    current_app.config['PREFERRED_URL_SCHEME'] = 'https' if request.is_secure else 'http'

@bp.after_app_request
def add_security_headers_bp(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    is_https = current_app.config.get('PREFERRED_URL_SCHEME') == 'https'

    csp = {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        "style-src": ["'self'", "'unsafe-inline'", "https://rsms.me", "https://cdn.jsdelivr.net"],
        "img-src": ["'self'", "data:", "https://img.shields.io"],
        "font-src": ["'self'", "https://rsms.me"],
        "connect-src": ["'self'"],
        "frame-src": ["'none'"]
    }
    if is_https:
        csp["upgrade-insecure-requests"] = []

    csp_string = "; ".join([f"{key} {" ".join(value)}" for key, value in csp.items()])
    response.headers['Content-Security-Policy'] = csp_string
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if is_https:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With, Authorization'
    return response

@bp.context_processor
def inject_protocol_bp():
    preferred_scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'http')
    base_url = f"{preferred_scheme}://{request.host}"
    master_key_value = None
    oauth_enabled = bool(current_app.config.get('OAUTH_PROVIDERS', []))

    if current_user.is_authenticated:
        master_key_value = current_app.config.get('MASTER_API_KEY')

    public_hostname = current_app.config.get('DOCKFLARE_PUBLIC_HOSTNAME')

    return {
        'protocol': preferred_scheme,
        'is_https': preferred_scheme == 'https',
        'base_url': base_url,
        'host': request.host,
        'request_scheme': request.scheme,
        'app_version': config.APP_VERSION,
        'master_api_key': master_key_value,
        'oauth_enabled': oauth_enabled,
        'current_user_auth_method': getattr(current_user, 'auth_method', None) if current_user.is_authenticated else None,
        'DOCKFLARE_PUBLIC_HOSTNAME': public_hostname
    }

@bp.route('/')
@login_required
def status_page():
    import time
    start_time = time.time()
    
    request_id = str(uuid.uuid4())[:8]
    logging.info(f"[{request_id}] Status page request started")
    
    rules_for_template = {}
    template_tunnel_state = {}
    template_agent_state = {}
    initialization_status = {}
    tld_policy_exists_val = False
    account_email_for_tld_val = None
    relevant_zone_name_for_tld_policy_val = None
    template_access_groups = {}
    template_agents = {}

    with state_lock:
        rules_snapshot = {hostname: copy.deepcopy(rule) for hostname, rule in managed_rules.items()}
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()
        template_access_groups = copy.deepcopy(access_groups)
        from app.core.state_manager import list_agents
        template_agents = list_agents()

    for hostname, rule_copy in rules_snapshot.items():
        if rule_copy.get("delete_at") and isinstance(rule_copy["delete_at"], datetime):
            rule_copy["delete_at"] = rule_copy["delete_at"].replace(tzinfo=timezone.utc) if rule_copy["delete_at"].tzinfo is None else rule_copy["delete_at"].astimezone(timezone.utc)
        rules_for_template[hostname] = rule_copy

    initialization_status = {
        "complete": template_tunnel_state.get("id") is not None or config.EXTERNAL_TUNNEL_ID,
        "in_progress": not (template_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID) and \
                       template_tunnel_state.get("status_message", "").lower().startswith("init")
    }

    cf_zone_id = current_app.config.get('CF_ZONE_ID')
    if cf_zone_id and docker_client:
        zone_details = get_zone_details_by_id(cf_zone_id)
        if zone_details and zone_details.get("name"):
            relevant_zone_name_for_tld_policy_val = zone_details.get("name")

        if relevant_zone_name_for_tld_policy_val:
            tld_policy_exists_val = check_for_tld_access_policy(relevant_zone_name_for_tld_policy_val)
            if not tld_policy_exists_val:
                account_email_for_tld_val = get_cloudflare_account_email()
        else:
            logging.info("Relevant zone name for TLD policy check (from CF_ZONE_ID) could not be determined.")

    display_token_val = get_display_token_ui(template_tunnel_state.get("token"))
    cf_account_id = current_app.config.get('CF_ACCOUNT_ID')

    default_tunnel_id_value = template_tunnel_state.get("id") or (config.EXTERNAL_TUNNEL_ID if config.USE_EXTERNAL_CLOUDFLARED else None)

    zone_lookup = {}
    try:
        zones_for_lookup = list_account_zones()
        zone_lookup = {z.get('id'): z.get('name') for z in zones_for_lookup if z.get('id')}
    except Exception as zone_lookup_error:
        logging.debug(f"Unable to build zone lookup: {zone_lookup_error}")

    for rule_details in rules_for_template.values():
        if rule_details.get("zone_name") or not zone_lookup:
            continue
        zone_name_from_lookup = zone_lookup.get(rule_details.get("zone_id"))
        if zone_name_from_lookup:
            rule_details["zone_name"] = zone_name_from_lookup

    dns_fetch_start = time.time()
    
    public_hostname_indices = {}
    try:
        effective_tunnel_id = template_tunnel_state.get("id") or config.EXTERNAL_TUNNEL_ID
        
        if not effective_tunnel_id:
            logging.warning("No effective tunnel ID available. Skipping DNS records fetch.")
        else:
            zone_ids_to_scan = set()
            cf_zone_id_cfg = current_app.config.get('CF_ZONE_ID')
            if cf_zone_id_cfg:
                zone_ids_to_scan.add(cf_zone_id_cfg)
            
            scan_zone_names = current_app.config.get('TUNNEL_DNS_SCAN_ZONE_NAMES', [])
            for zname in scan_zone_names:
                try:
                    zid = get_zone_id_from_name(zname)
                    if zid:
                        zone_ids_to_scan.add(zid)
                except Exception:
                    logging.debug(f"Failed to resolve zone name '{zname}' to ID", exc_info=True)
            
            collected_names = []
            if zone_ids_to_scan:
                def fetch_zone_records(zone_id):
                    try:
                        return get_dns_records_for_tunnel(zone_id, effective_tunnel_id)
                    except Exception as e:
                        logging.error(f"Error fetching DNS records for zone {zone_id}: {e}")
                        return []
                
                with ThreadPoolExecutor(max_workers=min(len(zone_ids_to_scan), 5)) as executor:
                    future_to_zone = {executor.submit(fetch_zone_records, zid): zid for zid in zone_ids_to_scan}
                    for future in as_completed(future_to_zone):
                        zone_id = future_to_zone[future]
                        try:
                            records = future.result()
                            for r in records:
                                name = r.get("name")
                                if name:
                                    collected_names.append(name.lower())
                        except Exception as e:
                            logging.error(f"Exception processing zone {zone_id}: {e}")
            
            unique_sorted_names = sorted(set(collected_names))
            for idx, name in enumerate(unique_sorted_names):
                public_hostname_indices[name] = idx
    except Exception as e:
        logging.error(f"Failed to build public hostname indices: {e}", exc_info=True)
        public_hostname_indices = {}
    
    dns_fetch_end = time.time()
    dns_fetch_duration = dns_fetch_end - dns_fetch_start
    logging.info(f"[{request_id}] DNS records fetching took {dns_fetch_duration:.3f} seconds")
        
    end_time = time.time()
    total_duration = end_time - start_time
    logging.info(f"[{request_id}] Status page request completed in {total_duration:.3f} seconds")
        
    timing_info = {
        'dns_fetch_duration': f"{dns_fetch_duration:.3f}s",
        'total_duration': f"{total_duration:.3f}s",
        'cache_used': CACHE_ENABLED
    }
    
    cache_status = None
    try:
        if hasattr(current_app, 'cache'):
            from app.core.cache import get_cache_stats
            cache_stats = get_cache_stats()
            cache_status = {
                'connected': cache_stats.get('connected', False),
                'dns_records_count': cache_stats.get('dns_records_count', 0)
            }
    except Exception as e:
        logging.error(f"Error getting cache status: {e}", exc_info=True)
        
        cache_status = {
            'connected': False,
            'dns_records_count': 0,
            'error': str(e)
        }

    return render_template('status_page.html',
                        tunnel_state=template_tunnel_state,
                        agent_state=template_agent_state,
                        initialization=initialization_status,
                        rules=rules_for_template,
                        CF_ACCOUNT_ID_CONFIGURED=bool(cf_account_id),
                        ACCOUNT_ID_FOR_DISPLAY=cf_account_id if cf_account_id else "Not Configured",
                        access_groups=template_access_groups,
                        agents=template_agents,
                        CF_ZONE_ID_CONFIGURED=bool(current_app.config.get('CF_ZONE_ID')),
                        public_hostname_indices=public_hostname_indices,
                        timing_info=timing_info,
                        default_tunnel_id=default_tunnel_id_value
                        )

from app.web.forms import ChangePasswordForm, SecuritySettingsForm, SettingsForm, CloudflareCredentialsForm
from werkzeug.security import check_password_hash, generate_password_hash
from cryptography.fernet import Fernet

@bp.route('/access-policies', methods=['GET'])
@login_required
def access_policies_page():
    """Renders the Access Policies page."""
    from app.core import reusable_policies

    default_bypass_id = "public-default-bypass"
    if default_bypass_id in access_groups:
        policy = access_groups[default_bypass_id]
        cf_policy_id = policy.get("cf_policy_id")

        # If no Cloudflare policy ID, create it now
        if not cf_policy_id or cf_policy_id == default_bypass_id:
            try:
                cf_policy = reusable_policies.create_reusable_policy(
                    name="DockFlare-Default-Public-Access-Bypass",
                    decision="bypass",
                    include_rules=[{"everyone": {}}]
                )
                if cf_policy and cf_policy.get("id"):
                    with state_lock:
                        access_groups[default_bypass_id]["cf_policy_id"] = cf_policy["id"]
                        access_groups[default_bypass_id]["id"] = cf_policy["id"]
                        save_state()
                    logging.info(f"Synced default bypass policy to Cloudflare with ID: {cf_policy['id']}")
            except Exception as e:
                logging.error(f"Failed to sync default bypass policy to Cloudflare: {e}", exc_info=True)

    groups_for_template = {}
    used_group_ids = set()
    group_usage = {}  

    with state_lock:
        for rule in managed_rules.values():
            
            if rule.get('source') in ['docker', 'agent']:
                hostname = rule.get('hostname', 'Unknown')
                group_id_val = rule.get('access_group_id')
                if isinstance(group_id_val, list):
                    for gid in group_id_val:
                        used_group_ids.add(gid)
                        if gid not in group_usage:
                            group_usage[gid] = []
                        group_usage[gid].append(hostname)
                elif group_id_val:
                    used_group_ids.add(group_id_val)
                    if group_id_val not in group_usage:
                        group_usage[group_id_val] = []
                    group_usage[group_id_val].append(hostname)
        groups_for_template_raw = copy.deepcopy(access_groups)
        groups_for_template = {
            gid: group for gid, group in groups_for_template_raw.items()
            if not group.get("hide_from_ui", False)
        }

    try:
        with open(os.path.join(current_app.static_folder, 'json', 'countries.json')) as f:
            countries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        countries = []
        flash('Could not load country list for Access Group modal.', 'error')

    cf_account_id = current_app.config.get('CF_ACCOUNT_ID', '')

    return render_template(
        'access_policies.html',
        access_groups=groups_for_template,
        used_group_ids=used_group_ids,
        group_usage=group_usage,
        countries=countries,
        ACCOUNT_ID_FOR_DISPLAY=cf_account_id if cf_account_id else "Not Configured"
    )

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings_page():
    """Renders and handles the main settings page."""
    settings_form = SettingsForm(prefix='general')
    change_password_form = ChangePasswordForm()
    security_settings_form = SecuritySettingsForm(prefix='security')
    cf_credentials_form = CloudflareCredentialsForm(prefix='cf_creds')

    
    if request.method == 'POST':
        if settings_form.submit_settings.data and settings_form.validate():
            data_path = os.path.dirname(config.STATE_FILE_PATH)
            key_file = os.path.join(data_path, 'dockflare.key')
            config_file = os.path.join(data_path, 'dockflare_config.dat')

            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                fernet = Fernet(key)

                with open(config_file, 'rb') as f:
                    decrypted_data = fernet.decrypt(f.read())
                config_data = json.loads(decrypted_data)

                original_tunnel_name = config_data.get('tunnel_name')
                new_tunnel_name = settings_form.tunnel_name.data
                tunnel_name_changed = original_tunnel_name != new_tunnel_name

                config_data['tunnel_name'] = new_tunnel_name
                config_data['cf_zone_id'] = settings_form.cf_zone_id.data
                config_data['tunnel_dns_scan_zone_names'] = settings_form.tunnel_dns_scan_zone_names.data
                config_data['grace_period_seconds'] = settings_form.grace_period_seconds.data

                encrypted_payload = fernet.encrypt(json.dumps(config_data).encode('utf-8'))
                with open(config_file, 'wb') as f:
                    f.write(encrypted_payload)

                from app import config as config_module
                current_app.config['TUNNEL_NAME'] = new_tunnel_name
                config_module.TUNNEL_NAME = new_tunnel_name
                current_app.config['CLOUDFLARED_CONTAINER_NAME'] = f"cloudflared-agent-{new_tunnel_name}"
                config_module.CLOUDFLARED_CONTAINER_NAME = f"cloudflared-agent-{new_tunnel_name}"
                current_app.config['CF_ZONE_ID'] = config_data['cf_zone_id']
                config_module.CF_ZONE_ID = config_data['cf_zone_id']
                scan_zones_str = config_data.get('tunnel_dns_scan_zone_names', '')
                current_app.config['TUNNEL_DNS_SCAN_ZONE_NAMES'] = [name.strip() for name in scan_zones_str.split(',') if name.strip()]
                config_module.TUNNEL_DNS_SCAN_ZONE_NAMES = current_app.config['TUNNEL_DNS_SCAN_ZONE_NAMES']
                current_app.config['GRACE_PERIOD_SECONDS'] = int(config_data.get('grace_period_seconds', 28800))
                config_module.GRACE_PERIOD_SECONDS = app_config['GRACE_PERIOD_SECONDS']

                flash('General settings updated successfully.', 'success')

                if tunnel_name_changed and not config.USE_EXTERNAL_CLOUDFLARED:
                    flash('Tunnel name changed. Restarting the agent to apply changes...', 'info')
                    logging.info(f"Tunnel name changed from '{original_tunnel_name}' to '{new_tunnel_name}'. Triggering agent restart.")
                    
                    def restart_agent_task():
                        stop_cloudflared_container()
                        time.sleep(5)
                        initialize_tunnel()
                        start_cloudflared_container()

                    from threading import Thread
                    restart_thread = Thread(target=restart_agent_task)
                    restart_thread.start()

                return redirect(url_for('web.settings_page'))
            except Exception as e:
                logging.error(f"Failed to update settings in config file: {e}", exc_info=True)
                flash('An error occurred while saving settings.', 'danger')
        
        elif security_settings_form.submit_security_settings.data and security_settings_form.validate():
            data_path = os.path.dirname(config.STATE_FILE_PATH)
            key_file = os.path.join(data_path, 'dockflare.key')
            config_file = os.path.join(data_path, 'dockflare_config.dat')
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                fernet = Fernet(key)

                with open(config_file, 'rb') as f:
                    decrypted_data = fernet.decrypt(f.read())
                config_data = json.loads(decrypted_data)

                config_data['disable_password_login'] = security_settings_form.disable_password_login.data
                auth_settings = config_data.get('auth_settings') or {}
                auth_settings['password_login_enabled'] = not config_data['disable_password_login']
                config_data['auth_settings'] = auth_settings

                encrypted_payload = fernet.encrypt(json.dumps(config_data).encode('utf-8'))
                with open(config_file, 'wb') as f:
                    f.write(encrypted_payload)

                current_app.config['DISABLE_PASSWORD_LOGIN'] = config_data['disable_password_login']
                
                flash('Security settings updated successfully.', 'success')
                return redirect(url_for('web.settings_page'))
            except Exception as e:
                logging.error(f"Failed to update security settings in config file: {e}", exc_info=True)
                flash('An error occurred while saving security settings.', 'danger')
        
        elif cf_credentials_form.submit_cloudflare_credentials.data and cf_credentials_form.validate():
            data_path = os.path.dirname(config.STATE_FILE_PATH)
            key_file = os.path.join(data_path, 'dockflare.key')
            config_file = os.path.join(data_path, 'dockflare_config.dat')
            try:
                with open(key_file, 'rb') as f:
                    key = f.read()
                fernet = Fernet(key)

                with open(config_file, 'rb') as f:
                    decrypted_data = fernet.decrypt(f.read())
                config_data = json.loads(decrypted_data)

                updated = False
                if cf_credentials_form.cf_account_id.data:
                    config_data['cf_account_id'] = cf_credentials_form.cf_account_id.data
                    current_app.config['CF_ACCOUNT_ID'] = config_data['cf_account_id']
                    config.CF_ACCOUNT_ID = config_data['cf_account_id']
                    updated = True
                
                if cf_credentials_form.cf_api_token.data:
                    config_data['cf_api_token'] = cf_credentials_form.cf_api_token.data
                    current_app.config['CF_API_TOKEN'] = config_data['cf_api_token']
                    config.CF_API_TOKEN = config_data['cf_api_token']
                    updated = True

                if updated:
                    encrypted_payload = fernet.encrypt(json.dumps(config_data).encode('utf-8'))
                    with open(config_file, 'wb') as f:
                        f.write(encrypted_payload)
                    flash('Cloudflare credentials updated. Re-initializing tunnel...', 'success')
                    
                    from threading import Thread
                    Thread(target=initialize_tunnel).start()
                else:
                    flash('No new credentials were provided.', 'info')

                return redirect(url_for('web.settings_page'))
            except Exception as e:
                logging.error(f"Failed to update Cloudflare credentials: {e}", exc_info=True)
                flash('An error occurred while updating credentials.', 'danger')
    
    if request.method == 'GET':
        settings_form.tunnel_name.data = current_app.config.get('TUNNEL_NAME')
        settings_form.cf_zone_id.data = current_app.config.get('CF_ZONE_ID')
        settings_form.tunnel_dns_scan_zone_names.data = ','.join(current_app.config.get('TUNNEL_DNS_SCAN_ZONE_NAMES', []))
        settings_form.grace_period_seconds.data = current_app.config.get('GRACE_PERIOD_SECONDS')
        security_settings_form.disable_password_login.data = current_app.config.get('DISABLE_PASSWORD_LOGIN', False)

    template_tunnel_state = {}
    template_agent_state = {}

    with state_lock:
        template_tunnel_state = tunnel_state.copy()
        template_agent_state = cloudflared_agent_state.copy()

    display_token_val = get_display_token_ui(template_tunnel_state.get("token"))
    all_account_tunnels_list = get_all_account_cloudflare_tunnels(force_refresh=True)
    cf_account_id = current_app.config.get('CF_ACCOUNT_ID')
    
    return render_template(
        'settings.html',
        settings_form=settings_form,
        change_password_form=change_password_form,
        security_settings_form=security_settings_form,
        cf_credentials_form=cf_credentials_form,
        all_account_tunnels=all_account_tunnels_list,
        tunnel_state=template_tunnel_state,
        agent_state=template_agent_state,
        display_token=display_token_val,
        cloudflared_container_name=current_app.config.get('CLOUDFLARED_CONTAINER_NAME'),
        docker_available=docker_client is not None,
        external_cloudflared=config.USE_EXTERNAL_CLOUDFLARED,
        external_tunnel_id=config.EXTERNAL_TUNNEL_ID,
        CF_ACCOUNT_ID_CONFIGURED=bool(cf_account_id),
        ACCOUNT_ID_FOR_DISPLAY=cf_account_id if cf_account_id else "Not Configured"
    )

@bp.route('/settings/reveal-master-key', methods=['POST'])
@login_required
def reveal_master_key():
    master_key = current_app.config.get('MASTER_API_KEY') or config.MASTER_API_KEY
    if not master_key:
        data_path = os.path.dirname(config.STATE_FILE_PATH)
        key_file = os.path.join(data_path, 'dockflare.key')
        config_file = os.path.join(data_path, 'dockflare_config.dat')
        try:
            if os.path.exists(key_file) and os.path.exists(config_file):
                with open(key_file, 'rb') as f:
                    key_bytes = f.read()
                with open(config_file, 'rb') as f:
                    encrypted_payload = f.read()
                decrypted = Fernet(key_bytes).decrypt(encrypted_payload)
                payload = json.loads(decrypted.decode('utf-8'))
                master_key = payload.get('master_api_key')
        except Exception as err:
            logging.error(f"Failed to load master API key from config: {err}", exc_info=True)
            master_key = None
    if not master_key:
        return jsonify({"status": "error", "message": "master_api_key_not_configured"}), 404
    return jsonify({"status": "success", "master_api_key": master_key})

@bp.route('/ui/cloudflare-tunnels/delete', methods=['POST'])
@login_required
def ui_delete_cloudflare_tunnel_route():
    tunnel_id = request.form.get('tunnel_id', '').strip()
    confirmation = request.form.get('confirm_text', '').strip().lower()

    if not tunnel_id:
        flash('Tunnel ID is required to delete a Cloudflare tunnel.', 'danger')
        return redirect(url_for('web.settings_page') + '#cloudflare-tunnels')

    if confirmation != 'delete':
        flash('Deletion cancelled. Type "delete" to confirm.', 'warning')
        return redirect(url_for('web.settings_page') + '#cloudflare-tunnels')

    try:
        deletion_success = delete_tunnel_via_api(tunnel_id)
        if deletion_success:
            get_all_account_cloudflare_tunnels(force_refresh=True)
            flash('Tunnel deleted successfully from Cloudflare.', 'success')
        else:
            flash('Failed to delete the tunnel via Cloudflare API. Verify permissions and try again.', 'danger')
    except Exception as deletion_error:
        logging.error(f"Error deleting Cloudflare tunnel {tunnel_id}: {deletion_error}", exc_info=True)
        flash('Unexpected error deleting tunnel. Check logs for details.', 'danger')

    return redirect(url_for('web.settings_page') + '#cloudflare-tunnels')

@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Handles the password change process."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data

        stored_hash = current_app.config.get('DOCKFLARE_PASSWORD_HASH')

        if stored_hash and check_password_hash(stored_hash, current_password):

            data_path = os.path.dirname(config.STATE_FILE_PATH)
            key_file = os.path.join(data_path, 'dockflare.key')
            config_file = os.path.join(data_path, 'dockflare_config.dat')

            try:
                with open(key_file, 'rb') as f:
                    key = f.read()

                fernet = Fernet(key)

                with open(config_file, 'rb') as f:
                    encrypted_data = f.read()

                decrypted_data = fernet.decrypt(encrypted_data)
                config_data = json.loads(decrypted_data)


                config_data['password'] = generate_password_hash(new_password)
                encrypted_payload = fernet.encrypt(json.dumps(config_data).encode('utf-8'))

                with open(config_file, 'wb') as f:
                    f.write(encrypted_payload)


                current_app.config['DOCKFLARE_PASSWORD_HASH'] = config_data['password']
                flash('Password changed successfully.', 'success')

            except Exception as e:
                logging.error(f"Failed to update password in config file: {e}", exc_info=True)
                flash('An error occurred while changing the password.', 'danger')
        else:
            flash('Incorrect current password.', 'danger')
    else:

        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')

    return redirect(url_for('web.settings_page'))

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
        if state_changed_for_revert:
            save_state()
            publish_state_event('snapshot_refresh')

    if app_id_to_delete_if_any:
        if delete_cloudflare_access_application(app_id_to_delete_if_any):
            pass
    
    reconcile_state_threaded() 
    action_status_message += " Reconciliation triggered."
    cloudflared_agent_state["last_action_status"] = action_status_message
    return redirect(url_for('web.status_page'))

@bp.route('/tunnel-dns-records/<tunnel_id>')
def tunnel_dns_records(tunnel_id):
    if not tunnel_id:
        return jsonify({"error": "Tunnel ID is required"}), 400
    all_found_dns_records = []
    zone_ids_to_scan = set()
    cf_zone_id = current_app.config.get('CF_ZONE_ID')
    if cf_zone_id:
        zone_ids_to_scan.add(cf_zone_id)

    scan_zone_names = current_app.config.get('TUNNEL_DNS_SCAN_ZONE_NAMES', [])
    for zone_name in scan_zone_names:
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

@bp.route('/ping')
def ping():
    return jsonify({ "status": "ok", "timestamp": int(time.time()), 
                     "protocol": request.environ.get('wsgi.url_scheme', 'unknown')})

@bp.route('/version/check')
def version_check():
    """
    Check whether the running DockFlare image matches the remote tag (digest comparison).
    Fallback to comparing APP_VERSION to GitHub latest release tag when digest method is not possible.
    Returns JSON:
      - method: "digest" or "version"
      - up_to_date: true/false/null
      - local_digest, remote_digest (when method == "digest")
      - current, latest (when method == "version")
      - repo, tag (when available)
      - error (when any internal error occurred)
    """
    repo = os.getenv('DOCKER_REPO', 'alplat/dockflare')
    tag = os.getenv('DOCKER_TAG', 'stable')
    cache_key = f"version_check:{repo}:{tag}"
    now = time.time()

    
    cache = getattr(current_app, '_version_check_cache', {})
    cached = cache.get(cache_key)
    if cached and cached.get('expires_at', 0) > now:
        return jsonify(cached['data'])

    result = {"method": None, "up_to_date": None}
    local_digest = None
    remote_digest = None

    try:
       
        container_id = None
        try:
            with open('/proc/self/cgroup', 'r') as f:
                cg = f.read()
            import re
            m = re.search(r'([0-9a-f]{64})', cg)
            if m:
                container_id = m.group(1)
        except Exception:
            container_id = None

        if not container_id:
           
            container_id = os.getenv('HOSTNAME')

        
        if docker_client and container_id:
            try:
                
                try:
                    container = docker_client.containers.get(container_id)
                except Exception:
                   
                    containers = docker_client.containers.list(all=True)
                    container = None
                    for c in containers:
                        if c.id.startswith(container_id) or c.name == container_id:
                            container = c
                            break
                    if container is None:
                        raise RuntimeError("Local Docker container not found via docker client.")
                image = container.image
                attrs = getattr(image, 'attrs', {}) or {}
                repo_digests = attrs.get('RepoDigests') or []
                if repo_digests:
                    
                    matched = None
                    for rd in repo_digests:
                        
                        if rd.startswith(repo + "@"):
                            matched = rd
                            break
                    if not matched:
                        matched = repo_digests[0]
                    if "@" in matched:
                        local_digest = matched.split("@", 1)[1]
                else:
                    
                    local_digest = getattr(image, 'id', None)
            except Exception as e_local_img:
                logging.debug(f"Version check: failed to determine local image digest: {e_local_img}")
        
        try:
            
            try:
                hub_api_url = f"https://hub.docker.com/v2/repositories/{repo}/tags/{tag}/"
                r_hub = requests.get(hub_api_url, timeout=10)
                if r_hub.status_code == 200:
                    hub_data = r_hub.json()
                    
                    pushed_at = hub_data.get('tag_last_pushed') or hub_data.get('last_updated')
                    if pushed_at:
                        result['remote_pushed_at'] = pushed_at
                        logging.debug(f"Version check: found remote_pushed_at via Docker Hub API v2: {pushed_at}")
            except Exception as e_hub:
                logging.debug(f"Version check: Docker Hub API v2 lookup failed, will proceed with manifest check. Error: {e_hub}")
            
            token = None
            auth_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
            r_tok = requests.get(auth_url, timeout=10)
            if r_tok.status_code == 200:
                token = r_tok.json().get('token')
            
            headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
            if token:
                headers['Authorization'] = f"Bearer {token}"
            
            manifest_url = f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}"
            r = requests.get(manifest_url, headers=headers, timeout=10)
            
            if r.status_code == 200:
                remote_digest = r.headers.get('Docker-Content-Digest')
                
                
                if 'remote_pushed_at' not in result:
                    logging.debug("Version check: remote_pushed_at not found via Hub API, attempting manifest blob inspection.")
                    try:
                        manifest_json = r.json()
                        config_digest = None
                        if isinstance(manifest_json, dict):
                            cfg = manifest_json.get('config') or {}
                            config_digest = cfg.get('digest')
                        
                        if config_digest:
                            blob_url = f"https://registry-1.docker.io/v2/{repo}/blobs/{config_digest}"
                            
                            r_blob = requests.get(blob_url, headers=headers, timeout=10)
                            if r_blob.status_code == 200:
                                try:
                                    cfg_json = r_blob.json()
                                    created = None
                                    if isinstance(cfg_json, dict):
                                        created = cfg_json.get('created')
                                        
                                        if not created:
                                            history = cfg_json.get('history')
                                            if isinstance(history, list) and history:
                                                created = history[0].get('created')
                                    if created:
                                        result['remote_pushed_at'] = created
                                        logging.debug(f"Version check: found remote_pushed_at via manifest blob: {created}")
                                except Exception as e_blob_parse:
                                    logging.debug(f"Version check: failed to parse config blob for timestamp: {e_blob_parse}")
                    except Exception as e_manifest_parse:
                        logging.debug(f"Version check: failed to parse manifest for timestamp fallback: {e_manifest_parse}")
        except Exception as e_remote:
            logging.debug(f"Version check: failed to fetch remote manifest/digest: {e_remote}")

        if local_digest and remote_digest:
            result['method'] = 'digest'
            result['local_digest'] = local_digest
            result['remote_digest'] = remote_digest
            result['repo'] = repo
            result['tag'] = tag
            result['up_to_date'] = (local_digest == remote_digest)
        else:
            
            result['method'] = 'version'
            result['current'] = config.APP_VERSION
            latest = None
            try:
                gh_url = 'https://api.github.com/repos/ChrispyBacon-dev/DockFlare/releases/latest'
                rgh = requests.get(gh_url, timeout=10, headers={'Accept': 'application/vnd.github.v3+json'})
                if rgh.status_code == 200:
                    latest_release_data = rgh.json()
                    latest = latest_release_data.get('tag_name') or latest_release_data.get('name')
                    if not result.get('remote_pushed_at'):
                        result['remote_pushed_at'] = latest_release_data.get('published_at')
            except Exception as e_gh:
                logging.debug(f"Version check: failed to fetch GitHub latest release: {e_gh}")
            result['latest'] = latest
            result['up_to_date'] = (latest is not None and result['current'] == latest)

    except Exception as e:
        logging.error(f"Error while performing version check: {e}", exc_info=True)
        result['error'] = str(e)
        result['up_to_date'] = None

    
    try:
        ttl = int(os.getenv('VERSION_CHECK_CACHE_TTL_SECONDS', '21600'))
    except Exception:
        ttl = 21600
    cache[cache_key] = {'data': result, 'expires_at': now + ttl}
    setattr(current_app, '_version_check_cache', cache)

    return jsonify(result)

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
        logging.error(f"Error in /debug route: {e}", exc_info=True)
        return jsonify({ "error": "An internal error occurred.", "status": "error", "timestamp": int(time.time()) }), 500

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
    rule_removed_from_state = False
    dns_delete_success = False
    access_app_delete_success = False
    zone_id_for_delete = None
    access_app_id_for_delete = None
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
        if hostname in managed_rules:
            del managed_rules[hostname]
            rule_removed_from_state = True
            save_state()
            publish_state_event('snapshot_refresh')
    if rule_removed_from_state and not config.USE_EXTERNAL_CLOUDFLARED:
        if update_cloudflare_config():
            pass
    return redirect(url_for('web.status_page'))

@bp.route('/stream-logs')
@login_required
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
                        yield ": keepalive\n\n" 
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
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET'
    return response

@bp.route('/stream-state-updates')
@login_required
def stream_state_updates_route():
    from app.core.cache import get_redis_client
    import select
    logging.info("SSE_CONNECT: Client connected to /stream-state-updates")

    def event_stream():
        redis_client = get_redis_client()
        if not redis_client:
            logging.error("SSE: Redis client not available for pub/sub")
            yield "data: {\"type\": \"error\", \"message\": \"Redis unavailable\"}\n\n"
            return

        pubsub = redis_client.pubsub()
        try:
            pubsub.subscribe('dockflare:state_updates')
            logging.info("SSE: Subscribed to Redis channel 'dockflare:state_updates'")
            yield ": connected\n\n"

            while True:
                message = pubsub.get_message(timeout=30)
                if message:
                    if message['type'] == 'message':
                        data = message['data'].decode('utf-8') if isinstance(message['data'], bytes) else message['data']
                        logging.info(f"SSE_SEND: Sending event to client: {data[:100]}...")
                        yield f"data: {data}\n\n"
                else:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            logging.info("SSE_DISCONNECT: State update stream client disconnected.")
        finally:
            pubsub.unsubscribe('dockflare:state_updates')
            pubsub.close()

    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@bp.route('/ui/manual-rules/add', methods=['POST'])
def ui_add_manual_rule_route():
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
        return redirect(url_for('web.status_page'))
    
    default_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    selected_tunnel_id = request.form.get('manual_tunnel_id', '').strip()
    if not default_tunnel_id and not selected_tunnel_id:
        cloudflared_agent_state["last_action_status"] = "Error: No tunnel is available for manual rule creation."
        return redirect(url_for('web.status_page'))

    target_tunnel_id = selected_tunnel_id or default_tunnel_id
    target_tunnel_name = None
    if selected_tunnel_id:
        tunnels = get_all_account_cloudflare_tunnels()
        matching_tunnel = None
        for t in tunnels or []:
            if t.get("id") == selected_tunnel_id:
                matching_tunnel = t
                break
        if not matching_tunnel:
            cloudflared_agent_state["last_action_status"] = "Error: Selected tunnel was not found in this account."
            return redirect(url_for('web.status_page'))
        target_tunnel_name = matching_tunnel.get("name") or "Unnamed Tunnel"
    else:
        target_tunnel_name = tunnel_state.get("name")
        if not target_tunnel_name or target_tunnel_name == "dockflare-tunnel":
            api_tunnel_name = get_tunnel_name_by_id(target_tunnel_id)
            if api_tunnel_name:
                target_tunnel_name = api_tunnel_name
            else:
                target_tunnel_name = "Default Tunnel"

    subdomain_input = request.form.get('manual_subdomain', '').strip()
    domain_name_input = request.form.get('manual_domain_name', '').strip()
    path_input = request.form.get('manual_path', '').strip()
    service_type_input = request.form.get('manual_service_type', '').strip().lower()
    service_address_input = request.form.get('manual_service_address', '').strip()
    zone_name_override_input = request.form.get('manual_zone_name_override', '').strip()
    zone_id_override_input = request.form.get('manual_zone_id', '').strip()
    no_tls_verify = request.form.get('manual_no_tls_verify') == 'on'
    origin_server_name_input = request.form.get('manual_origin_server_name', '').strip()
    manual_http_host_header = request.form.get('manual_http_host_header', '').strip()

    manual_access_group_ids = request.form.getlist('manual_access_groups')
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
    elif service_type_input == "bastion":
        processed_service_for_cf = "bastion"

    if not is_valid_service(processed_service_for_cf):
        cloudflared_agent_state["last_action_status"] = f"Error: Constructed service string '{processed_service_for_cf}' is invalid."
        return redirect(url_for('web.status_page'))
    
    target_zone_id = None
    target_zone_name = None
    if zone_id_override_input:
        target_zone_id = zone_id_override_input
        try:
            zones_list = list_account_zones()
            for zone in zones_list or []:
                if zone.get('id') == target_zone_id:
                    target_zone_name = zone.get('name')
                    break
        except Exception:
            target_zone_name = None
    if not target_zone_id:
        zone_name_to_lookup = zone_name_override_input or '.'.join(domain_name_input.split('.')[-2:])
        if zone_name_to_lookup:
            looked_up_zone_id = get_zone_id_from_name(zone_name_to_lookup)
            if looked_up_zone_id:
                target_zone_id = looked_up_zone_id
                target_zone_name = zone_name_to_lookup
    if not target_zone_id:
        cf_zone_id_default = current_app.config.get('CF_ZONE_ID')
        if cf_zone_id_default:
            target_zone_id = cf_zone_id_default
            if not target_zone_name:
                zone_details = get_zone_details_by_id(cf_zone_id_default)
                if zone_details:
                    target_zone_name = zone_details.get('name')
        else:
            cloudflared_agent_state["last_action_status"] = "Error: Could not determine Zone ID."
            return redirect(url_for('web.status_page'))
        
    access_app_id = None
    access_policy_type = None
    access_app_config_hash = None
    access_group_id = None
    previous_tunnel_id = None

    with state_lock:
        if manual_access_group_ids:
            cf_access_policies_or_ids = []
            desired_session_duration = "24h"
            desired_app_launcher_visible = False
            desired_allowed_idps = None
            desired_auto_redirect = False
            use_reusable = False

            for i, group_id in enumerate(manual_access_group_ids):
                if group_id in access_groups:
                    group = access_groups[group_id]
                    if i == 0:
                        desired_session_duration = group.get("session_duration", "24h")
                        desired_app_launcher_visible = group.get("app_launcher_visible", False)
                        desired_allowed_idps = group.get("allowed_idps")
                        desired_auto_redirect = group.get("auto_redirect_to_identity", False)

                    if config.USE_REUSABLE_POLICIES:
                        use_reusable = True
                        from app.core import reusable_policies

                        existing_policy_id = group.get("cloudflare_policy_id")
                        if existing_policy_id:
                            logging.info(f"Using existing reusable policy ID '{existing_policy_id}' for access group '{group_id}'")
                            cf_access_policies_or_ids.append(existing_policy_id)
                        else:
                            policy_id = reusable_policies.sync_access_group_to_reusable_policy(group_id)
                            if policy_id:
                                logging.info(f"Synced access group '{group_id}' to reusable policy ID '{policy_id}' for manual rule")
                                cf_access_policies_or_ids.append(policy_id)
                            else:
                                logging.error(f"Failed to sync access group '{group_id}' for manual rule - no policy ID returned")
                    else:
                        cf_access_policies_or_ids.extend(group.get("policies", []))
                else:
                    logging.warning(f"Access group '{group_id}' selected but not found in state")

            if cf_access_policies_or_ids:
                access_group_id = manual_access_group_ids
                access_policy_type = "group"
                desired_app_name = f"DockFlare-{full_hostname}"

                access_app_config_hash = generate_access_app_config_hash(
                    policy_type="group", session_duration=desired_session_duration,
                    app_launcher_visible=desired_app_launcher_visible,
                    allowed_idps_str=json.dumps(desired_allowed_idps, sort_keys=True),
                    auto_redirect_to_identity=desired_auto_redirect,
                    custom_access_rules_str=json.dumps(cf_access_policies_or_ids, sort_keys=True),
                    group_id=','.join(access_group_id)
                )

                existing_app = find_cloudflare_access_application_by_hostname(full_hostname)
                if existing_app:
                    app_result = update_cloudflare_access_application(
                        existing_app['id'], full_hostname, desired_app_name, desired_session_duration,
                        desired_app_launcher_visible, [full_hostname], cf_access_policies_or_ids,
                        desired_allowed_idps, desired_auto_redirect, use_reusable
                    )
                else:
                    app_result = create_cloudflare_access_application(
                        full_hostname, desired_app_name, desired_session_duration,
                        desired_app_launcher_visible, [full_hostname], cf_access_policies_or_ids,
                        desired_allowed_idps, desired_auto_redirect, use_reusable
                    )

                if app_result:
                    access_app_id = app_result.get('id')
                else:
                    cloudflared_agent_state["last_action_status"] = "Error: Failed to create/update Access App for group(s)."

        elif manual_access_policy_type and manual_access_policy_type != 'none':
            if manual_access_policy_type == "bypass":
                
                default_bypass_id = "public-default-bypass"
                if default_bypass_id in access_groups:
                    default_bypass_group = access_groups[default_bypass_id]
                    cf_policy_id = default_bypass_group.get("cf_policy_id") or default_bypass_group.get("id")

                    access_group_id = [default_bypass_id]
                    access_policy_type = "group"
                    desired_app_name = f"DockFlare-{full_hostname}"

                    access_app_config_hash = generate_access_app_config_hash(
                        policy_type="group", session_duration="24h",
                        app_launcher_visible=False,
                        allowed_idps_str=None,
                        auto_redirect_to_identity=False,
                        custom_access_rules_str=json.dumps([cf_policy_id], sort_keys=True),
                        group_id=default_bypass_id
                    )

                    existing_app = find_cloudflare_access_application_by_hostname(full_hostname)
                    if existing_app:
                        app_result = update_cloudflare_access_application(
                            existing_app['id'], full_hostname, desired_app_name, "24h",
                            False, [full_hostname], [cf_policy_id],
                            None, False, True
                        )
                    else:
                        app_result = create_cloudflare_access_application(
                            full_hostname, desired_app_name, "24h",
                            False, [full_hostname], [cf_policy_id],
                            None, False, True
                        )

                    if app_result:
                        access_app_id = app_result.get('id')
                    else:
                        cloudflared_agent_state["last_action_status"] = "Error: Failed to create/update Access App with default bypass policy."
                else:
                    cloudflared_agent_state["last_action_status"] = "Error: Default bypass policy not found."
                    return redirect(url_for('web.status_page'))

    with state_lock:
        existing_rule = managed_rules.get(key_for_managed_rules)
        if existing_rule and existing_rule.get("source") == "docker":
            cloudflared_agent_state["last_action_status"] = f"Error: Rule for {full_hostname} is Docker-managed."
            return redirect(url_for('web.status_page'))
        if existing_rule:
            previous_tunnel_id = existing_rule.get("tunnel_id") or default_tunnel_id

        managed_rules[key_for_managed_rules] = {
            "hostname": full_hostname,
            "path": processed_path,
            "service": processed_service_for_cf,
            "container_id": None, "status": "active", "delete_at": None,
            "zone_id": target_zone_id,
            "zone_name": target_zone_name,
            "no_tls_verify": no_tls_verify,
            "origin_server_name": origin_server_name_input or None,
            "http_host_header": manual_http_host_header or None,
            "source": "manual",
            "access_app_id": access_app_id,
            "access_policy_type": access_policy_type,
            "access_app_config_hash": access_app_config_hash,
            "access_group_id": access_group_id,
            "access_policy_ui_override": True,
            "rule_ui_override": False,
            "tunnel_id": target_tunnel_id,
            "tunnel_name": target_tunnel_name
        }
        save_state()
        publish_state_event('snapshot_refresh')
    
    if update_cloudflare_config(target_tunnel_id):
        create_cloudflare_dns_record(target_zone_id, full_hostname, target_tunnel_id)
        if previous_tunnel_id and previous_tunnel_id != target_tunnel_id:
            update_cloudflare_config(previous_tunnel_id)
        if previous_tunnel_id is None and default_tunnel_id and default_tunnel_id != target_tunnel_id:
            update_cloudflare_config(default_tunnel_id)
        cloudflared_agent_state["last_action_status"] = f"Success: Manual rule for {full_hostname} added/updated."
    else:
        cloudflared_agent_state["last_action_status"] = "Error: Failed to update Cloudflare tunnel config."

    return redirect(url_for('web.status_page'))

@bp.route('/ui/docker-rules/revert', methods=['POST'])
def ui_revert_docker_rule_route():
    """
    Reverts a UI-overridden Docker rule back to label-driven configuration.
    """
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
        return redirect(url_for('web.status_page'))

    rule_key = request.form.get('rule_key')
    if not rule_key:
        cloudflared_agent_state["last_action_status"] = "Error: Missing rule key for revert."
        return redirect(url_for('web.status_page'))

    with state_lock:
        existing = managed_rules.get(rule_key)
        if not existing:
            cloudflared_agent_state["last_action_status"] = f"Error: Rule '{rule_key}' not found."
            return redirect(url_for('web.status_page'))

        if existing.get("source") != "docker":
            cloudflared_agent_state["last_action_status"] = f"Error: Rule '{rule_key}' is not a Docker rule."
            return redirect(url_for('web.status_page'))

        if not existing.get("rule_ui_override", False):
            cloudflared_agent_state["last_action_status"] = f"Info: Rule '{rule_key}' is not UI-overridden."
            return redirect(url_for('web.status_page'))

        # Revert the rule back to Docker label control
        existing["rule_ui_override"] = False
        save_state()

        cloudflared_agent_state["last_action_status"] = f"Success: Rule '{rule_key}' reverted to Docker label control. Reconciliation will update it based on container labels."

    # Trigger reconciliation to pick up Docker labels
    try:
        from app.core.reconciler import reconcile_state_threaded
        reconcile_state_threaded()
    except Exception as e:
        logging.error(f"Failed to trigger reconciliation after Docker rule revert: {e}")

    return redirect(url_for('web.status_page'))

@bp.route('/ui/manual-rules/edit', methods=['POST'])
def ui_edit_manual_rule_route():
    """
    Handles editing an existing manual rule submitted from the UI.
    Expects a hidden 'edit_rule_key' form field identifying the rule key to edit.
    Only rules with source != 'docker' (manual or agent) are editable via UI.
    """
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
        return redirect(url_for('web.status_page'))

    rule_key = request.form.get('edit_rule_key')
    if not rule_key:
        cloudflared_agent_state["last_action_status"] = "Error: Missing rule key for edit."
        return redirect(url_for('web.status_page'))

    with state_lock:
        existing = managed_rules.get(rule_key)
        if not existing:
            cloudflared_agent_state["last_action_status"] = f"Error: Rule '{rule_key}' not found."
            return redirect(url_for('web.status_page'))

        # Allow editing Docker rules but mark them as UI-overridden
        is_docker_rule = existing.get("source") == "docker"
    
    subdomain_input = request.form.get('edit_subdomain', '').strip()
    domain_name_input = request.form.get('edit_domain_name', '').strip()
    path_input = request.form.get('edit_path', '').strip()
    service_address_input = request.form.get('edit_service_address', '').strip()
    service_type_input = request.form.get('edit_service_type', '').strip().lower()
    zone_name_override_input = request.form.get('edit_zone_name_override', '').strip()
    no_tls_verify = request.form.get('edit_no_tls_verify') == 'on'
    origin_server_name_input = request.form.get('edit_origin_server_name', '').strip()
    manual_http_host_header = request.form.get('edit_http_host_header', '').strip()
    
    if not domain_name_input or not service_type_input:
        cloudflared_agent_state["last_action_status"] = "Error: Domain and service type required."
        return redirect(url_for('web.status_page'))

    full_hostname = f"{subdomain_input}.{domain_name_input}" if subdomain_input else domain_name_input
    if not is_valid_hostname(full_hostname):
        cloudflared_agent_state["last_action_status"] = f"Error: Invalid hostname '{full_hostname}'."
        return redirect(url_for('web.status_page'))

    processed_path = f"/{path_input.lstrip('/')}" if path_input else None

    processed_service_for_cf = ""
    if service_type_input in ["http", "https"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input in ["tcp", "ssh", "rdp"]:
        processed_service_for_cf = f"{service_type_input}://{service_address_input}"
    elif service_type_input == "http_status":
        processed_service_for_cf = f"http_status:{service_address_input}"
    elif service_type_input == "bastion":
        processed_service_for_cf = "bastion"

    if not is_valid_service(processed_service_for_cf):
        cloudflared_agent_state["last_action_status"] = f"Error: Invalid service string '{processed_service_for_cf}'."
        return redirect(url_for('web.status_page'))

    zone_name_to_lookup = zone_name_override_input or '.'.join(domain_name_input.split('.')[-2:])
    target_zone_id = get_zone_id_from_name(zone_name_to_lookup) or current_app.config.get('CF_ZONE_ID')
    if not target_zone_id:
        cloudflared_agent_state["last_action_status"] = "Error: Could not determine Zone ID."
        return redirect(url_for('web.status_page'))

    manual_access_group_ids = request.form.getlist('edit_access_groups')
    manual_access_policy_type = request.form.get('edit_access_policy_type', 'none').strip().lower()
    manual_auth_email = request.form.get('edit_auth_email', '').strip()

    access_app_id = existing.get('access_app_id')
    access_policy_type = existing.get('access_policy_type')
    access_app_config_hash = existing.get('access_app_config_hash')
    access_group_id = existing.get('access_group_id')

    try:
        if manual_access_group_ids:
            cf_access_policies_or_ids = []
            desired_session_duration = "24h"
            desired_app_launcher_visible = False
            desired_allowed_idps = None
            desired_auto_redirect = False
            use_reusable = False

            for i, group_id in enumerate(manual_access_group_ids):
                if group_id in access_groups:
                    group = access_groups[group_id]
                    if i == 0:
                        desired_session_duration = group.get("session_duration", "24h")
                        desired_app_launcher_visible = group.get("app_launcher_visible", False)
                        desired_allowed_idps = group.get("allowed_idps")
                        desired_auto_redirect = group.get("auto_redirect_to_identity", False)

                    if config.USE_REUSABLE_POLICIES:
                        use_reusable = True
                        from app.core import reusable_policies

                        existing_policy_id = group.get("cloudflare_policy_id")
                        if existing_policy_id:
                            logging.info(f"Using existing reusable policy ID '{existing_policy_id}' for access group '{group_id}' in edit")
                            cf_access_policies_or_ids.append(existing_policy_id)
                        else:
                            policy_id = reusable_policies.sync_access_group_to_reusable_policy(group_id)
                            if policy_id:
                                logging.info(f"Synced access group '{group_id}' to reusable policy ID '{policy_id}' for manual edit")
                                cf_access_policies_or_ids.append(policy_id)
                            else:
                                logging.error(f"Failed to sync access group '{group_id}' for manual edit - no policy ID returned")
                    else:
                        cf_access_policies_or_ids.extend(group.get("policies", []))
                else:
                    logging.warning(f"Access group '{group_id}' selected in edit but not found in state")

            if cf_access_policies_or_ids:
                access_group_id = manual_access_group_ids
                access_policy_type = "group"
                desired_app_name = f"DockFlare-{full_hostname}"
                access_app_config_hash = generate_access_app_config_hash(
                    policy_type="group", session_duration=desired_session_duration,
                    app_launcher_visible=desired_app_launcher_visible,
                    allowed_idps_str=json.dumps(desired_allowed_idps, sort_keys=True),
                    auto_redirect_to_identity=desired_auto_redirect,
                    custom_access_rules_str=json.dumps(cf_access_policies_or_ids, sort_keys=True),
                    group_id=','.join(access_group_id)
                )
                existing_app = find_cloudflare_access_application_by_hostname(full_hostname)
                if existing_app:
                    app_result = update_cloudflare_access_application(
                        existing_app['id'], full_hostname, desired_app_name, desired_session_duration,
                        desired_app_launcher_visible, [full_hostname], cf_access_policies_or_ids,
                        desired_allowed_idps, desired_auto_redirect, use_reusable
                    )
                else:
                    app_result = create_cloudflare_access_application(
                        full_hostname, desired_app_name, desired_session_duration,
                        desired_app_launcher_visible, [full_hostname], cf_access_policies_or_ids,
                        desired_allowed_idps, desired_auto_redirect, use_reusable
                    )
                if app_result:
                    access_app_id = app_result.get('id')
        elif manual_access_policy_type and manual_access_policy_type != 'none':
            if manual_access_policy_type == "bypass":
                # Use the default bypass reusable policy
                default_bypass_id = "public-default-bypass"
                if default_bypass_id in access_groups:
                    default_bypass_group = access_groups[default_bypass_id]
                    cf_policy_id = default_bypass_group.get("cf_policy_id") or default_bypass_group.get("id")

                    access_group_id = [default_bypass_id]
                    access_policy_type = "group"
                    desired_app_name = f"DockFlare-{full_hostname}"

                    access_app_config_hash = generate_access_app_config_hash(
                        policy_type="group", session_duration="24h",
                        app_launcher_visible=False,
                        allowed_idps_str=None,
                        auto_redirect_to_identity=False,
                        custom_access_rules_str=json.dumps([cf_policy_id], sort_keys=True),
                        group_id=default_bypass_id
                    )

                    existing_app = find_cloudflare_access_application_by_hostname(full_hostname)
                    if existing_app:
                        app_result = update_cloudflare_access_application(
                            existing_app['id'], full_hostname, desired_app_name, "24h",
                            False, [full_hostname], [cf_policy_id],
                            None, False, True
                        )
                    else:
                        app_result = create_cloudflare_access_application(
                            full_hostname, desired_app_name, "24h",
                            False, [full_hostname], [cf_policy_id],
                            None, False, True
                        )

                    if app_result:
                        access_app_id = app_result.get('id')
                    else:
                        cloudflared_agent_state["last_action_status"] = "Error: Failed to update Access App with default bypass policy."
                else:
                    cloudflared_agent_state["last_action_status"] = "Error: Default bypass policy not found."
                    return redirect(url_for('web.status_page'))
    except Exception as e:
        logging.error(f"Error updating access app during manual edit: {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = "Error: Failed to update access app."

    with state_lock:
     
        new_key = get_rule_key(full_hostname, processed_path)
        rule_entry = {
            "hostname": full_hostname,
            "path": processed_path,
            "service": processed_service_for_cf,
            "container_id": existing.get("container_id"),
            "status": "active",
            "delete_at": None,
            "zone_id": target_zone_id,
            "no_tls_verify": no_tls_verify,
            "origin_server_name": origin_server_name_input or None,
            "http_host_header": manual_http_host_header or None,
            "access_app_id": access_app_id,
            "access_policy_type": access_policy_type,
            "access_app_config_hash": access_app_config_hash,
            "access_group_id": access_group_id,
            "access_policy_ui_override": True,
            "rule_ui_override": is_docker_rule,
            "source": existing.get("source", "manual")
        }

      
        if new_key != rule_key and rule_key in managed_rules:
            del managed_rules[rule_key]
        managed_rules[new_key] = rule_entry
        save_state()
        publish_state_event('snapshot_refresh')

    
    effective_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID
    if update_cloudflare_config():
        if effective_tunnel_id:
            create_cloudflare_dns_record(target_zone_id, full_hostname, effective_tunnel_id)
        cloudflared_agent_state["last_action_status"] = f"Success: Manual rule '{full_hostname}' updated."
    else:
        cloudflared_agent_state["last_action_status"] = "Error: Failed to update Cloudflare tunnel config."

    return redirect(url_for('web.status_page'))


@bp.route('/ui/manual-rules/delete/<path:rule_key_from_url>', methods=['POST'])
def ui_delete_manual_rule_route(rule_key_from_url):
    if not docker_client:
        cloudflared_agent_state["last_action_status"] = "Error: Docker client unavailable."
        return redirect(url_for('web.status_page'))

    default_tunnel_id = tunnel_state.get("id") if not config.USE_EXTERNAL_CLOUDFLARED else config.EXTERNAL_TUNNEL_ID

    zone_id_for_delete = None
    access_app_id_for_delete = None
    hostname_for_dns = None
    rule_tunnel_id = None

    with state_lock:
        rule_details = managed_rules.get(rule_key_from_url)
        if not rule_details or rule_details.get("source") != "manual":
            cloudflared_agent_state["last_action_status"] = "Error: Manual rule not found."
            return redirect(url_for('web.status_page'))

        zone_id_for_delete = rule_details.get("zone_id")
        access_app_id_for_delete = rule_details.get("access_app_id")
        hostname_for_dns = rule_details.get("hostname")
        rule_tunnel_id = rule_details.get("tunnel_id") or default_tunnel_id

        del managed_rules[rule_key_from_url]
        save_state()
        publish_state_event('snapshot_refresh')

    dns_deleted_ok = True
    if hostname_for_dns and zone_id_for_delete and rule_tunnel_id:
        should_delete_dns = True
        with state_lock:
            for other_rule in managed_rules.values():
                if other_rule.get("hostname") == hostname_for_dns:
                    should_delete_dns = False
                    break
        if should_delete_dns:
            if not delete_cloudflare_dns_record(zone_id_for_delete, hostname_for_dns, rule_tunnel_id):
                dns_deleted_ok = False

    if access_app_id_for_delete:
        delete_cloudflare_access_application(access_app_id_for_delete)

    config_updated = update_cloudflare_config(rule_tunnel_id) if rule_tunnel_id else update_cloudflare_config()

    if dns_deleted_ok and config_updated:
        cloudflared_agent_state["last_action_status"] = "Success: Manual rule deleted."
    else:
        issues = []
        if not dns_deleted_ok:
            issues.append("DNS not removed")
        if not config_updated:
            issues.append("tunnel config update failed")
        cloudflared_agent_state["last_action_status"] = "Warning: Manual rule removed (" + ", ".join(issues) + ")"

    return redirect(url_for('web.status_page'))

def _parse_and_build_policy_from_form(email_str, ip_ranges_str=None, countries_list=None, idp_list=None, public_mode=False):
    from app.core.state_manager import get_idp_id_by_name
    policies = []
    email_rules = []
    ip_rules = []
    idp_rules = []

    if email_str and email_str.strip():
        email_parts = [part.strip() for part in email_str.split(',') if part.strip()]
        for part in email_parts:
            if part.startswith('@'):
                email_rules.append({"email_domain": {"domain": part[1:]}})
            else:
                email_rules.append({"email": {"email": part}})

    if idp_list:
        for idp_friendly_name in idp_list:
            if idp_friendly_name.strip():
                idp_id = get_idp_id_by_name(idp_friendly_name)
                if idp_id:
                    idp_rules.append({"login_method": {"id": idp_id}})
                else:
                    logging.warning(f"IdP friendly name '{idp_friendly_name}' not found in state, skipping")

    if idp_rules and not email_rules and not public_mode:
        raise ValueError("When using Identity Providers, you must specify allowed email addresses to prevent unauthorized access.")

    if ip_ranges_str and ip_ranges_str.strip():
        ip_parts = [part.strip() for part in ip_ranges_str.split(',') if part.strip()]
        for ip in ip_parts:
            ip_rules.append({"ip": {"ip": ip}})

    if ip_rules:
        policies.append({"name": "Bypass for defined IPs", "decision": "bypass", "include": ip_rules})

    if public_mode:
        # PUBLIC MODE: Bypass for everyone except blocked countries
        if countries_list:
            blocked_country_rules = [{"geo": {"country_code": country.upper()}} for country in countries_list]
            policies.append({
                "name": "Public Access (Bypass) with geo-blocking",
                "decision": "bypass",
                "include": [{"everyone": {}}],
                "exclude": blocked_country_rules
            })
        else:
            # Full public access, no restrictions
            policies.append({
                "name": "Public Access (Bypass)",
                "decision": "bypass",
                "include": [{"everyone": {}}]
            })
    else:
        include_rules = email_rules + idp_rules
        if include_rules:
            policy = {
                "name": "Allow defined users",
                "decision": "allow",
                "include": include_rules
            }

            if countries_list:
                blocked_country_rules = [{"geo": {"country_code": country.upper()}} for country in countries_list]
                policy["exclude"] = blocked_country_rules

            policies.append(policy)
            policies.append({"name": "Default Deny", "decision": "deny", "include": [{"everyone": {}}]})
        else:
            policies.append({"name": "Default Deny (No rules defined)", "decision": "deny", "include": [{"everyone": {}}]})

    return policies

@bp.route('/ui/access-groups/create', methods=['POST'])
def create_access_group():
    form = request.form
    group_id = form.get('group_id', '').strip()
    display_name = form.get('display_name', '').strip()

    if not group_id or not display_name:
        flash("Error: Group ID and Display Name are required.", "error")
        return redirect(url_for('web.access_policies_page'))

    with state_lock:
        if group_id in access_groups:
            flash(f"Error: Access Group with ID '{group_id}' already exists.", "error")
            return redirect(url_for('web.access_policies_page'))

        public_mode = form.get('public_mode', 'false').lower() == 'true'

        try:
            policies = _parse_and_build_policy_from_form(
                form.get('emails', ''),
                form.get('ip_ranges', ''),
                request.form.getlist('countries'),
                request.form.getlist('identity_providers'),
                public_mode=public_mode
            )
        except ValueError as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('web.access_policies_page'))

        new_group = {
            "id": group_id,
            "display_name": display_name,
            "session_duration": form.get('session_duration', '24h').strip(),
            "app_launcher_visible": form.get('app_launcher_visible') == 'on',
            "auto_redirect_to_identity": form.get('auto_redirect') == 'on',
            "public_mode": public_mode,
            "policies": policies
        }
        access_groups[group_id] = new_group
        save_state()

        from app import config
        if config.USE_REUSABLE_POLICIES:
            from app.core import reusable_policies
            try:
                policy_id = reusable_policies.sync_access_group_to_reusable_policy(group_id)
                if policy_id:
                    logging.info(f"Created reusable policy '{policy_id}' for access group '{group_id}'")
            except Exception as e:
                logging.error(f"Failed to sync access group '{group_id}' to reusable policy: {e}", exc_info=True)

        publish_state_event('snapshot_refresh')

    flash(f"Success: Access Group '{display_name}' created.", "success")
    return redirect(url_for('web.access_policies_page'))

@bp.route('/ui/access-groups/edit/<group_id>', methods=['POST'])
def edit_access_group(group_id):
    with state_lock:
        if group_id not in access_groups:
            flash(f"Error: Access Group with ID '{group_id}' not found.", "error")
            return redirect(url_for('web.access_policies_page'))
    
    form = request.form
    display_name = form.get('display_name', '').strip()
    if not display_name:
        flash("Error: Display Name is required.", "error")
        return redirect(url_for('web.access_policies_page'))
    
    with state_lock:
        public_mode = form.get('public_mode', 'false').lower() == 'true'

        try:
            policies = _parse_and_build_policy_from_form(
                form.get('emails', ''),
                form.get('ip_ranges', ''),
                request.form.getlist('countries'),
                request.form.getlist('identity_providers'),
                public_mode=public_mode
            )
        except ValueError as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for('web.access_policies_page'))

        updated_group = {
            "id": group_id,
            "display_name": display_name,
            "session_duration": form.get('session_duration', '24h').strip(),
            "app_launcher_visible": form.get('app_launcher_visible') == 'on',
            "auto_redirect_to_identity": form.get('auto_redirect') == 'on',
            "public_mode": public_mode,
            "policies": policies
        }
        access_groups[group_id] = updated_group
        save_state()

        from app import config
        if config.USE_REUSABLE_POLICIES:
            from app.core import reusable_policies
            try:
                policy_id = reusable_policies.sync_access_group_to_reusable_policy(group_id)
                if policy_id:
                    logging.info(f"Updated reusable policy '{policy_id}' for access group '{group_id}'")
            except Exception as e:
                logging.error(f"Failed to sync updated access group '{group_id}' to reusable policy: {e}", exc_info=True)

        publish_state_event('snapshot_refresh')

    flash(f"Success: Access Group '{display_name}' updated. Triggering reconciliation.", "success")
    reconcile_state_threaded()
    return redirect(url_for('web.access_policies_page'))

@bp.route('/ui/access-groups/delete/<group_id>', methods=['POST'])
def delete_access_group(group_id):
    with state_lock:
        if group_id not in access_groups:
            flash(f"Error: Access Group with ID '{group_id}' not found.", "error")
            return redirect(url_for('web.access_policies_page'))

        # Check if this is a system policy that cannot be deleted
        if access_groups[group_id].get('system_policy') or not access_groups[group_id].get('deletable', True):
            flash(f"Error: Cannot delete system policy '{access_groups[group_id]['display_name']}'.", "error")
            return redirect(url_for('web.access_policies_page'))

        is_in_use = any(
            (isinstance(rule.get('access_group_id'), list) and group_id in rule.get('access_group_id')) or \
            (rule.get('access_group_id') == group_id)
            for rule in managed_rules.values()
        )

        if is_in_use:
            flash(f"Error: Cannot delete Access Group '{access_groups[group_id]['display_name']}' because it is currently in use.", "error")
            return redirect(url_for('web.access_policies_page'))

        display_name = access_groups[group_id]['display_name']

        from app import config
        if config.USE_REUSABLE_POLICIES:
            from app.core import reusable_policies
            try:
                reusable_policies.delete_access_group_and_policy(group_id)
                logging.info(f"Deleted access group '{group_id}' and associated Cloudflare policy")
            except Exception as e:
                logging.error(f"Error deleting Cloudflare policy for '{group_id}': {e}", exc_info=True)
                del access_groups[group_id]
                save_state()
        else:
            del access_groups[group_id]
            save_state()

        publish_state_event('snapshot_refresh')

    flash(f"Success: Access Group '{display_name}' has been deleted.", "success")
    return redirect(url_for('web.access_policies_page'))

@bp.route('/ui/zone-policies/create', methods=['POST'])
def create_zone_default_policy():
    """Creates a wildcard *.zone.com Access Application using a selected access group."""
    zone_name = request.form.get('zone_name', '').strip()
    zone_id = request.form.get('zone_id', '').strip()
    access_group_id = request.form.get('access_group_id', '').strip()

    if not zone_name or not access_group_id:
        flash("Error: Zone name and access policy are required.", "error")
        return redirect(url_for('web.access_policies_page'))

    with state_lock:
        if access_group_id not in access_groups:
            flash(f"Error: Access policy '{access_group_id}' not found.", "error")
            return redirect(url_for('web.access_policies_page'))

        group = access_groups[access_group_id]

    wildcard_hostname = f"*.{zone_name}"

    try:
        # Check if it already exists
        existing = find_cloudflare_access_application_by_hostname(wildcard_hostname)
        if existing:
            flash(f"A wildcard policy for '{wildcard_hostname}' already exists.", "warning")
            return redirect(url_for('web.access_policies_page'))

        # Get the Cloudflare policy ID
        from app.core import reusable_policies
        cf_policy_id = group.get("cf_policy_id") or group.get("id")

        # Sync to Cloudflare if needed
        if not cf_policy_id or cf_policy_id == access_group_id:
            policy_id = reusable_policies.sync_access_group_to_reusable_policy(access_group_id)
            if policy_id:
                cf_policy_id = policy_id
                with state_lock:
                    access_groups[access_group_id]["cf_policy_id"] = policy_id
                    access_groups[access_group_id]["id"] = policy_id
                    save_state()

        # Create the Access Application
        app_name = f"Zone Default: {wildcard_hostname}"
        session_duration = group.get("session_duration", "24h")
        app_launcher_visible = group.get("app_launcher_visible", False)
        auto_redirect = group.get("auto_redirect_to_identity", False)
        allowed_idps = group.get("allowed_idps")

        app_result = create_cloudflare_access_application(
            wildcard_hostname, app_name, session_duration,
            app_launcher_visible, [wildcard_hostname], [cf_policy_id],
            allowed_idps, auto_redirect, True
        )

        if app_result:
            flash(f"Success: Created zone default policy for '{wildcard_hostname}'.", "success")
            logging.info(f"Created zone default policy for {wildcard_hostname} with Access App ID {app_result.get('id')}")
            
            try:
                from app.core.cache import get_redis_client
                redis_client = get_redis_client()
                if redis_client:
                    redis_client.delete("zone_policies_cache")
                    redis_client.delete(f"tld_policy_check:{zone_name}")
                    logging.info("Invalidated zone policies and TLD check caches after creating zone policy")
            except Exception as cache_err:
                logging.warning(f"Failed to invalidate caches: {cache_err}")
        else:
            flash(f"Error: Failed to create Access Application for '{wildcard_hostname}'.", "error")

    except Exception as e:
        logging.error(f"Error creating zone default policy for {wildcard_hostname}: {e}", exc_info=True)
        flash(f"Error: Failed to create zone policy. {str(e)}", "error")

    return redirect(url_for('web.access_policies_page'))

@bp.route('/ui/access-groups/sync-from-cloudflare', methods=['POST'])
def sync_access_groups_from_cloudflare():
    from app import config
    if not config.USE_REUSABLE_POLICIES:
        flash("Error: Reusable policies feature is not enabled.", "error")
        return redirect(url_for('web.access_policies_page'))

    try:
        from app.core import reusable_policies

        # Get sync_all parameter from form (defaults to false for backward compatibility)
        sync_all = request.form.get('sync_all', 'false').lower() in ['true', '1', 't', 'yes']

        result = reusable_policies.import_cloudflare_reusable_policies(sync_all=sync_all)

        imported = result.get("imported", 0)
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)

        if imported > 0 or updated > 0:
            publish_state_event('snapshot_refresh')
            mode_text = "all policies" if sync_all else "DockFlare- prefixed policies"
            flash(f"Success: Synced {imported} new and {updated} updated access groups from Cloudflare ({mode_text}). {skipped} skipped.", "success")
        else:
            flash(f"No new access groups to import. {skipped} existing policies found.", "info")

    except Exception as e:
        logging.error(f"Error syncing access groups from Cloudflare: {e}", exc_info=True)
        flash(f"Error: Failed to sync access groups from Cloudflare. Check logs for details.", "error")

    return redirect(url_for('web.access_policies_page'))

@bp.route('/backup/download')
def download_state_backup():
    try:
        buffer, filename = backup_manager.create_backup_archive()
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
    except FileNotFoundError as missing_file:
        logging.error("Error generating backup archive: %s", missing_file)
        return "Backup failed: required data file missing.", 400
    except Exception as e:
        logging.error(f"Error generating backup archive: {e}", exc_info=True)
        return "Failed to generate backup.", 500

@bp.route('/backup/restore', methods=['POST'])
def restore_state_backup():
    if 'backup_file' not in request.files:
        cloudflared_agent_state["last_action_status"] = "Error: No backup file provided."
        return redirect(url_for('web.settings_page'))
    
    file = request.files['backup_file']
    if file.filename == '':
        cloudflared_agent_state["last_action_status"] = "Error: No file selected for restore."
        return redirect(url_for('web.settings_page'))

    try:
        result = backup_manager.restore_backup(file, allow_legacy_json=True)
        is_full_archive = result.mode != "legacy_state"
        backup_manager.refresh_runtime_after_restore(result)

        status_parts = ["Success: Backup restored."]
        if is_full_archive:
            status_parts.append("DockFlare will restart automatically to apply the backup.")
        else:
            status_parts.append("(legacy state.json applied – reconfigure secrets manually)")

        cloudflared_agent_state["last_action_status"] = " ".join(status_parts)

        if "state.json" in result.files_applied:
            reconcile_state_threaded()

        if is_full_archive:
            return render_template('restore_restarting.html', countdown_seconds=5)
    except Exception as e:
        logging.error(f"Error restoring backup: {e}", exc_info=True)
        cloudflared_agent_state["last_action_status"] = "Error: Restore failed. The file may be corrupt or invalid. Check logs."

    return redirect(url_for('web.settings_page'))

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("6 per minute", methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.status_page'))

    from .forms import LoginForm
    form = LoginForm()
    password_login_enabled = not current_app.config.get('DISABLE_PASSWORD_LOGIN', False)

    if password_login_enabled and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        stored_username = current_app.config.get('DOCKFLARE_USERNAME')
        stored_hash = current_app.config.get('DOCKFLARE_PASSWORD_HASH')

        from werkzeug.security import check_password_hash
        if (username == stored_username and stored_hash and
            check_password_hash(stored_hash, password)):
            user = User(stored_username, auth_method='password')
            login_user(user)
            next_page = request.args.get('next')
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for('web.status_page'))
        else:
            flash('Invalid username or password.', 'error')

    oauth_providers = [
        p for p in current_app.config.get('OAUTH_PROVIDERS', []) if p.get('enabled', True)
    ]

    return render_template(
        'login.html',
        title="Login",
        form=form,
        password_login_enabled=password_login_enabled,
        oauth_providers=oauth_providers
    )

@bp.route('/login/<provider_id>')
def login_provider(provider_id):
    import secrets
    state_token = secrets.token_urlsafe(32)
    session['oauth_state'] = state_token

    from app import oauth
    public_hostname = current_app.config.get('DOCKFLARE_PUBLIC_HOSTNAME')
    if public_hostname:
        path = url_for('web.auth_callback', provider_id=provider_id)
        callback_url = f"https://{public_hostname}{path}"
        logging.info(f"Constructed OAuth callback URL using public hostname: {callback_url}")
    else:
        callback_url = url_for('web.auth_callback', provider_id=provider_id, _external=True)
    return oauth.create_client(provider_id).authorize_redirect(callback_url, state=state_token)

@bp.route('/auth/<provider_id>/callback')
def auth_callback(provider_id):
    received_state = request.args.get('state')
    expected_state = session.pop('oauth_state', None)

    if not received_state or not expected_state or received_state != expected_state:
        flash('Invalid authentication state. Please try again.', 'error')
        return redirect(url_for('web.login'))

    from app import oauth
    client = oauth.create_client(provider_id)
    try:
        token = client.authorize_access_token()
        userinfo = client.userinfo()
    except Exception as e:
        logging.error(f"OAuth callback error for provider {provider_id}: {e}", exc_info=True)
        flash('Authentication failed.', 'error')
        return redirect(url_for('web.login'))

    user_email = userinfo.get('email')
    if not user_email:
        flash('Could not retrieve email from provider. Cannot log in.', 'error')
        return redirect(url_for('web.login'))

    authorized_emails = current_app.config.get('OAUTH_AUTHORIZED_USERS', [])
    if user_email not in authorized_emails:
        flash(f'Access denied for user {user_email}.', 'error')
        return redirect(url_for('web.login'))

    user = User(user_email, auth_method='oauth')
    login_user(user)

    logging.info(f"OAUTH_SUCCESS: User {user_email} authenticated via {provider_id} from {request.remote_addr}")

    next_page = request.args.get('next')
    if next_page and is_safe_url(next_page):
        return redirect(next_page)
    return redirect(url_for('web.status_page'))

@bp.route('/logout')
@login_required
def logout():
    auth_method = getattr(current_user, 'auth_method', 'password')
    logout_user()

    flash('You have been logged out.', 'success')

    if current_app.config.get('DISABLE_PASSWORD_LOGIN'):
        return redirect(url_for('web.status_page'))

    return redirect(url_for('web.login'))

def is_safe_url(target):
    from urllib.parse import urlparse, urljoin
    from flask import request
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
