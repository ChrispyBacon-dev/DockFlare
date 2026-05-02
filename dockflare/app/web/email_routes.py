import base64
import hmac
import ipaddress
import json
import logging
import os
import secrets
import time
import jwt
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app
from flask_login import login_required, current_user
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from werkzeug.security import generate_password_hash, check_password_hash
from app import config, docker_client, limiter
from app.core import email_manager
from app.core.cloudflare_api import list_account_zones
from app.web.config_loader import load_encrypted_config, load_encrypted_config_with_cipher, config_file_path

_WORKER_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'core', 'worker_templates')

def _read_worker_template(filename):
    with open(os.path.join(_WORKER_TEMPLATE_DIR, filename), 'r') as f:
        return f.read()

email_bp = Blueprint('email', __name__, url_prefix='/email')

def _webmail_origin():
    request_origin = request.headers.get('Origin', '')
    if not request_origin:
        return '*'
        
    # Allow any origin that looks like our mail subdomains
    if '.dockflare.app' in request_origin or 'localhost' in request_origin or '127.0.0.1' in request_origin:
        return request_origin

    # Fallback to the first domain or *
    domains = config.EMAIL_CONFIG.get('domains', {})
    first_domain = next(iter(domains), '')
    return f"https://mail.{first_domain}" if first_domain else '*'

def save_email_config(email_config_data):
    cfg, fernet = load_encrypted_config_with_cipher()
    if not cfg or not fernet:
        return False
    cfg['email_config'] = email_config_data
    try:
        import os
        from app.web.config_loader import config_file_path
        cfg_str = json.dumps(cfg)
        encrypted_data = fernet.encrypt(cfg_str.encode('utf-8'))
        with open(config_file_path(), 'wb') as f:
            f.write(encrypted_data)
        config.EMAIL_CONFIG = email_config_data
        current_app.config['EMAIL_CONFIG'] = email_config_data
        return True
    except Exception as e:
        logging.error(f"Failed to save email config: {e}")
        return False

def _get_mail_manager_state():
    try:
        container = docker_client.containers.get('dockflare-mail-manager')
        return 'running' if container.status == 'running' else 'stopped'
    except Exception:
        return 'missing'

@email_bp.route('', methods=['GET'])
@login_required
def email_page():
    zones = list_account_zones() or []
    mail_manager_state = _get_mail_manager_state()
    return render_template('email.html', zones=zones, email_config=config.EMAIL_CONFIG, email_enabled=config.EMAIL_ENABLED, mail_manager_state=mail_manager_state, cf_account_id=config.CF_ACCOUNT_ID or '')

@email_bp.route('/setup-domain', methods=['POST'])
@login_required
def setup_email_domain():
    data = request.get_json(force=True, silent=True) or {}
    zone_id = data.get('zone_id')
    zone_name = data.get('zone_name')
    if not zone_id or not zone_name:
        return jsonify({'success': False, 'error': 'Missing zone info'}), 400

    try:
        try:
            email_manager.enable_email_routing(zone_id)
        except Exception as routing_err:
            logging.warning(f"Could not enable email routing via API (may need manual enable in CF Dashboard): {routing_err}")

        email_manager.setup_email_dns_records(zone_id, zone_name)

        bucket_name = f"dockflare-mail-{zone_name.replace('.', '-')}"
        email_manager.create_r2_bucket(bucket_name)

        r2_creds = email_manager.get_r2_s3_credentials()
        r2_access_key_id = r2_creds['access_key_id']
        r2_secret_access_key = r2_creds['secret_access_key']
        r2_endpoint_url = r2_creds['endpoint_url']

        workers_subdomain = email_manager.get_workers_subdomain()

        email_cfg = config.EMAIL_CONFIG.copy()
        email_cfg['enabled'] = True
        if 'domains' not in email_cfg:
            email_cfg['domains'] = {}

        if 'jwt_signing_key' not in email_cfg:
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            email_cfg['jwt_signing_key'] = private_bytes.decode('utf-8')
            email_cfg['jwt_public_key'] = public_bytes.decode('utf-8')

        if 'vapid_private_key' not in email_cfg:
            vapid_key = ec.generate_private_key(ec.SECP256R1())
            email_cfg['vapid_private_key'] = vapid_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
            email_cfg['vapid_public_key'] = base64.urlsafe_b64encode(
                vapid_key.public_key().public_bytes(
                    encoding=serialization.Encoding.X962,
                    format=serialization.PublicFormat.UncompressedPoint
                )
            ).rstrip(b'=').decode()

        webhook_secret = secrets.token_hex(32)
        outbound_auth_secret = secrets.token_hex(32)
        inbound_worker_name = f"dockflare-mail-inbound-{zone_name.replace('.', '-')}"
        outbound_worker_name = f"dockflare-mail-outbound-{zone_name.replace('.', '-')}"
        webmail_hostname = _get_webmail_hostname() or f"mail.{zone_name}"
        webhook_url = f"https://{webmail_hostname}/api/v1/webhook/inbound"

        quota_kv_ns_id = None
        try:
            quota_kv_ns_id = email_manager.create_kv_namespace(
                f"dockflare-quota-{zone_name.replace('.', '-')}"
            )
        except Exception as e:
            logging.warning(f"Could not create quota KV namespace for {zone_name}: {e}")

        inbound_bindings = [
            {"type": "r2_bucket", "name": "EMAIL_BUCKET", "bucket_name": bucket_name},
            {"type": "plain_text", "name": "WEBHOOK_URL", "text": webhook_url},
            {"type": "secret_text", "name": "WEBHOOK_SECRET", "text": webhook_secret},
            {"type": "plain_text", "name": "ALLOWED_RECIPIENTS", "text": "[]"},
            {"type": "plain_text", "name": "DOMAIN_NAME", "text": zone_name}
        ]
        if quota_kv_ns_id:
            inbound_bindings.append(
                {"type": "kv_namespace", "name": "QUOTA_KV", "namespace_id": quota_kv_ns_id}
            )

        email_manager.deploy_worker(inbound_worker_name, _read_worker_template('inbound_worker.js'), inbound_bindings)
        email_manager.set_worker_cron(inbound_worker_name, ['*/5 * * * *'])
        email_manager.setup_catchall_routing_rule(zone_id, inbound_worker_name)

        try:
            email_manager.enable_email_sending(zone_id, zone_name)
        except Exception as sending_err:
            logging.warning(f"Could not enable email sending for {zone_name} (may need manual enable in CF Dashboard): {sending_err}")

        email_sending_status = email_manager.get_email_sending_status(zone_id, zone_name)

        outbound_bindings = [
            {"type": "send_email", "name": "SEND_EMAIL"},
            {"type": "secret_text", "name": "AUTH_SECRET", "text": outbound_auth_secret}
        ]

        email_manager.deploy_worker(outbound_worker_name, _read_worker_template('outbound_worker.js'), outbound_bindings)

        outbound_worker_url = f"https://{outbound_worker_name}.{workers_subdomain}.workers.dev" if workers_subdomain else ''

        email_cfg['domains'][zone_name] = {
            'zone_id': zone_id,
            'zone_name': zone_name,
            'email_routing_enabled': True,
            'email_sending_status': email_sending_status,
            'r2_bucket': bucket_name,
            'r2_access_key_id': r2_access_key_id,
            'r2_secret_access_key': r2_secret_access_key,
            'r2_endpoint_url': r2_endpoint_url,
            'webhook_secret': webhook_secret,
            'inbound_worker_name': inbound_worker_name,
            'outbound_worker_name': outbound_worker_name,
            'outbound_worker_url': outbound_worker_url,
            'outbound_auth_secret': outbound_auth_secret,
            'quota_kv_namespace_id': quota_kv_ns_id,
            'mailboxes': {}
        }

        save_email_config(email_cfg)
        config.EMAIL_ENABLED = True
        current_app.config['EMAIL_ENABLED'] = True

        _restart_mail_container()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@email_bp.route('/repair-dns', methods=['POST'])
@login_required
def repair_dns():
    data = request.get_json(force=True, silent=True) or {}
    zone_name = data.get('zone_name')
    email_cfg = config.EMAIL_CONFIG
    if not zone_name or zone_name not in email_cfg.get('domains', {}):
        return jsonify({'success': False, 'error': 'Domain not found'}), 404
    try:
        zone_id = email_cfg['domains'][zone_name]['zone_id']
        email_manager.setup_email_dns_records(zone_id, zone_name)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _teardown_domain_remote(domain, domain_cfg):
    errors = []
    zone_id = domain_cfg.get('zone_id')
    for address, mb in domain_cfg.get('mailboxes', {}).items():
        rule_id = mb.get('routing_rule_id')
        if rule_id:
            try:
                email_manager.delete_email_routing_rule(zone_id, rule_id)
            except Exception as e:
                errors.append(f"Routing rule {address}: {e}")
    try:
        email_manager.reset_catchall_to_drop(zone_id)
    except Exception as e:
        errors.append(f"Catchall reset: {e}")
    try:
        email_manager.disable_email_routing(zone_id)
    except Exception as e:
        errors.append(f"Disable routing: {e}")
    try:
        email_manager.delete_worker(domain_cfg.get('inbound_worker_name', ''))
    except Exception as e:
        errors.append(f"Inbound worker: {e}")
    try:
        email_manager.delete_worker(domain_cfg.get('outbound_worker_name', ''))
    except Exception as e:
        errors.append(f"Outbound worker: {e}")
    try:
        email_manager.empty_and_delete_r2_bucket(
            domain_cfg.get('r2_bucket', ''),
            domain_cfg.get('r2_endpoint_url', ''),
            domain_cfg.get('r2_access_key_id', ''),
            domain_cfg.get('r2_secret_access_key', ''),
        )
    except Exception as e:
        errors.append(f"R2 bucket: {e}")
    try:
        errors.extend(email_manager.scrub_email_dns_records(zone_id, domain))
    except Exception as e:
        errors.append(f"DNS scrub: {e}")
    return errors

@email_bp.route('/teardown-domain', methods=['POST'])
@login_required
def teardown_domain():
    import requests as req_lib
    data = request.get_json(force=True, silent=True) or {}
    zone_name = data.get('zone_name')
    include_local = data.get('include_local_data', False)
    email_cfg = config.EMAIL_CONFIG.copy()
    if 'domains' not in email_cfg or zone_name not in email_cfg['domains']:
        return jsonify({'success': False, 'error': 'Domain not found'}), 404

    domain_cfg = email_cfg['domains'][zone_name]

    errors = _teardown_domain_remote(zone_name, domain_cfg)

    if include_local:
        token = _generate_jwt(current_user.get_id(), role='admin')
        if token:
            try:
                resp = req_lib.post(
                    f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/wipe-domain",
                    headers={'Authorization': f'Bearer {token}'},
                    json={'domain': zone_name},
                    timeout=120
                )
                if not resp.ok:
                    errors.append(f"Local wipe: {resp.text}")
            except Exception as e:
                errors.append(f"Local wipe: {e}")

    del email_cfg['domains'][zone_name]
    if not email_cfg.get('domains'):
        config.EMAIL_ENABLED = False
        current_app.config['EMAIL_ENABLED'] = False
    save_email_config(email_cfg)

    _restart_mail_container()
    return jsonify({'success': True, 'errors': errors})

@email_bp.route('/teardown-all', methods=['POST'])
@login_required
def teardown_all():
    import requests as req_lib
    data = request.get_json(force=True, silent=True) or {}
    include_local = data.get('include_local_data', False)
    email_cfg = config.EMAIL_CONFIG.copy()
    errors = []

    for domain, domain_cfg in list(email_cfg.get('domains', {}).items()):
        errors.extend(_teardown_domain_remote(domain, domain_cfg))

    if include_local:
        token = _generate_jwt(current_user.get_id(), role='admin')
        if token:
            try:
                resp = req_lib.post(
                    f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/wipe-all",
                    headers={'Authorization': f'Bearer {token}'},
                    timeout=120
                )
                if not resp.ok:
                    errors.append(f"Local wipe-all: {resp.text}")
            except Exception as e:
                errors.append(f"Local wipe-all: {e}")

    email_cfg['domains'] = {}
    config.EMAIL_ENABLED = False
    current_app.config['EMAIL_ENABLED'] = False
    save_email_config(email_cfg)

    _restart_mail_container()
    return jsonify({'success': True, 'errors': errors})

@email_bp.route('/wipe-local', methods=['POST'])
@login_required
def wipe_local():
    import requests as req_lib
    data = request.get_json(force=True, silent=True) or {}
    domain = data.get('domain')
    if not domain:
        return jsonify({'success': False, 'error': 'domain required'}), 400
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'success': False, 'error': 'JWT configuration missing'}), 500
    try:
        resp = req_lib.post(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/wipe-domain",
            headers={'Authorization': f'Bearer {token}'},
            json={'domain': domain},
            timeout=120
        )
        resp.raise_for_status()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@email_bp.route('/local-domains', methods=['GET'])
@login_required
def local_domains():
    import requests as req_lib
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'active': [], 'orphaned': []})
    try:
        resp = req_lib.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/local-domains",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10
        )
        resp.raise_for_status()
        local = resp.json()
        active_domains = set((config.EMAIL_CONFIG or {}).get('domains', {}).keys())
        result = {'active': [], 'orphaned': []}
        for d in local:
            if d['domain'] in active_domains:
                result['active'].append(d)
            else:
                result['orphaned'].append(d)
        return jsonify(result)
    except Exception:
        return jsonify({'active': [], 'orphaned': []})

def _redeploy_outbound_worker(email_cfg, domain):
    d = email_cfg['domains'][domain]
    outbound_bindings = [
        {"type": "send_email", "name": "SEND_EMAIL"},
        {"type": "secret_text", "name": "AUTH_SECRET", "text": d['outbound_auth_secret']}
    ]
    email_manager.deploy_worker(d['outbound_worker_name'], _read_worker_template('outbound_worker.js'), outbound_bindings)

def _redeploy_inbound_worker(email_cfg, domain):
    d = email_cfg['domains'][domain]
    all_addresses = list(d['mailboxes'].keys())
    webmail_hostname = _get_webmail_hostname() or f"mail.{domain}"
    webhook_url = f"https://{webmail_hostname}/api/v1/webhook/inbound"

    kv_ns_id = d.get('quota_kv_namespace_id')
    if not kv_ns_id:
        kv_ns_id = email_manager.get_or_create_kv_namespace(
            f"dockflare-quota-{domain.replace('.', '-')}"
        )
        if kv_ns_id:
            email_cfg['domains'][domain]['quota_kv_namespace_id'] = kv_ns_id
            save_email_config(email_cfg)
            logging.info(f"Resolved quota KV namespace for {domain}: {kv_ns_id}")
        else:
            logging.warning(f"Could not resolve quota KV namespace for {domain}")

    catch_all_address = d.get('catch_all_address', '')
    catch_all_enabled = 'true' if catch_all_address else 'false'

    inbound_bindings = [
        {"type": "r2_bucket", "name": "EMAIL_BUCKET", "bucket_name": d['r2_bucket']},
        {"type": "plain_text", "name": "WEBHOOK_URL", "text": webhook_url},
        {"type": "secret_text", "name": "WEBHOOK_SECRET", "text": d['webhook_secret']},
        {"type": "plain_text", "name": "ALLOWED_RECIPIENTS", "text": json.dumps(all_addresses)},
        {"type": "plain_text", "name": "DOMAIN_NAME", "text": domain},
        {"type": "plain_text", "name": "CATCH_ALL_ENABLED", "text": catch_all_enabled}
    ]
    if kv_ns_id:
        inbound_bindings.append(
            {"type": "kv_namespace", "name": "QUOTA_KV", "namespace_id": kv_ns_id}
        )

    email_manager.deploy_worker(d['inbound_worker_name'], _read_worker_template('inbound_worker.js'), inbound_bindings)
    email_manager.set_worker_cron(d['inbound_worker_name'], ['*/5 * * * *'])

@email_bp.route('/mailbox/create', methods=['POST'])
@login_required
def create_mailbox():
    data = request.get_json(force=True, silent=True) or {}
    address = data.get('address')
    display_name = data.get('display_name')
    domain = data.get('domain')

    quota_bytes = data.get('quota_bytes', 10737418240)

    email_cfg = config.EMAIL_CONFIG.copy()
    if 'domains' not in email_cfg or domain not in email_cfg['domains']:
        return jsonify({'success': False, 'error': 'Domain not configured'}), 400

    zone_id = email_cfg['domains'][domain]['zone_id']
    worker_name = f"dockflare-mail-inbound-{domain.replace('.', '-')}"

    try:
        res = email_manager.create_email_routing_rule(zone_id, address, worker_name)
        rule_id = res.get('result', {}).get('id', '')
        email_cfg['domains'][domain]['mailboxes'][address] = {
            'display_name': display_name,
            'routing_rule_id': rule_id,
            'quota_bytes': quota_bytes,
            'created_at': time.time()
        }
        save_email_config(email_cfg)
        _redeploy_inbound_worker(email_cfg, domain)
        _restart_mail_container()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@email_bp.route('/mailbox/delete', methods=['POST'])
@login_required
def delete_mailbox():
    data = request.get_json(force=True, silent=True) or {}
    address = data.get('address')
    domain = data.get('domain')

    email_cfg = config.EMAIL_CONFIG.copy()
    if 'domains' in email_cfg and domain in email_cfg['domains']:
        if address in email_cfg['domains'][domain]['mailboxes']:
            rule_id = email_cfg['domains'][domain]['mailboxes'][address].get('routing_rule_id')
            zone_id = email_cfg['domains'][domain]['zone_id']
            if rule_id:
                try:
                    email_manager.delete_email_routing_rule(zone_id, rule_id)
                except Exception:
                    pass
            del email_cfg['domains'][domain]['mailboxes'][address]
            save_email_config(email_cfg)
            _redeploy_inbound_worker(email_cfg, domain)
            _restart_mail_container()
    return jsonify({'success': True})

@email_bp.route('/mailbox/set-quota', methods=['POST'])
@login_required
def set_mailbox_quota():
    import requests
    data = request.get_json(force=True, silent=True) or {}
    address = data.get('address')
    domain = data.get('domain')
    quota_bytes = data.get('quota_bytes')
    if not address or not domain or quota_bytes is None:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    email_cfg = config.EMAIL_CONFIG.copy()
    if 'domains' not in email_cfg or domain not in email_cfg['domains']:
        return jsonify({'success': False, 'error': 'Domain not configured'}), 404
    if address not in email_cfg['domains'][domain].get('mailboxes', {}):
        return jsonify({'success': False, 'error': 'Mailbox not found'}), 404
    email_cfg['domains'][domain]['mailboxes'][address]['quota_bytes'] = quota_bytes
    save_email_config(email_cfg)
    token = _generate_jwt(current_user.get_id(), role='admin')
    if token:
        try:
            requests.patch(
                f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/mailboxes/{address}",
                headers={'Authorization': f'Bearer {token}'},
                json={'quota_bytes': quota_bytes},
                timeout=5,
            )
        except Exception:
            pass

    kv_ns_id = email_cfg['domains'][domain].get('quota_kv_namespace_id')
    if kv_ns_id:
        try:
            email_manager.delete_kv_entry(kv_ns_id, address)
        except Exception as e:
            logging.warning(f"Could not unblock quota KV for {address}: {e}")

    return jsonify({'success': True})

@email_bp.route('/mailbox-stats', methods=['GET'])
@login_required
def mailbox_stats():
    import requests
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/mailboxes",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502

@email_bp.route('/redeploy-workers', methods=['POST'])
@login_required
def redeploy_workers():
    email_cfg = config.EMAIL_CONFIG.copy()
    domains = email_cfg.get('domains', {})
    for domain in list(domains.keys()):
        try:
            _redeploy_inbound_worker(email_cfg, domain)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Inbound redeploy failed for {domain}: {e}'}), 500
        try:
            _redeploy_outbound_worker(email_cfg, domain)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Outbound redeploy failed for {domain}: {e}'}), 500
        zone_id = domains[domain].get('zone_id')
        if zone_id:
            email_cfg['domains'][domain]['email_sending_status'] = email_manager.get_email_sending_status(zone_id, domain)
        try:
            r2_creds = email_manager.get_r2_s3_credentials()
            email_cfg['domains'][domain]['r2_access_key_id'] = r2_creds['access_key_id']
            email_cfg['domains'][domain]['r2_secret_access_key'] = r2_creds['secret_access_key']
            email_cfg['domains'][domain]['r2_endpoint_url'] = r2_creds['endpoint_url']
        except Exception as e:
            logging.warning(f"Could not refresh R2 credentials for {domain} on redeploy: {e}")
    save_email_config(email_cfg)
    _restart_mail_container()
    return jsonify({'success': True, 'domains': list(domains.keys())})

@email_bp.route('/update-r2-credentials', methods=['POST'])
@login_required
def update_r2_credentials():
    data = request.get_json(force=True, silent=True) or {}
    zone_name = data.get('zone_name')
    access_key_id = data.get('r2_access_key_id', '').strip()
    secret_access_key = data.get('r2_secret_access_key', '').strip()
    if not zone_name or not access_key_id or not secret_access_key:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    email_cfg = config.EMAIL_CONFIG.copy()
    if 'domains' not in email_cfg or zone_name not in email_cfg['domains']:
        return jsonify({'success': False, 'error': 'Domain not configured'}), 404

    email_cfg['domains'][zone_name]['r2_access_key_id'] = access_key_id
    email_cfg['domains'][zone_name]['r2_secret_access_key'] = secret_access_key
    save_email_config(email_cfg)
    _restart_mail_container()
    return jsonify({'success': True})

@email_bp.route('/status', methods=['GET'])
@login_required
def email_status_api():
    return jsonify({'success': True, 'config': config.EMAIL_CONFIG})

@email_bp.route('/verify-dns', methods=['POST'])
@login_required
def verify_dns():
    data = request.get_json(force=True, silent=True) or {}
    zone_name = data.get('zone_name')
    email_cfg = config.EMAIL_CONFIG
    if 'domains' in email_cfg and zone_name in email_cfg['domains']:
        zone_id = email_cfg['domains'][zone_name]['zone_id']
        status = email_manager.verify_email_dns_records(zone_id, zone_name)
        return jsonify({'success': True, 'status': status})
    return jsonify({'success': False, 'error': 'Domain not found'}), 404

@email_bp.route('/check-permissions', methods=['POST'])
@login_required
def check_permissions():
    perms = email_manager.check_token_permissions()
    return jsonify({'success': True, 'permissions': perms})

@email_bp.route('/generate-jwt', methods=['POST'])
@login_required
def generate_jwt_route():
    username = current_user.get_id()
    token = _generate_jwt(username)
    if not token:
        return jsonify({'success': False, 'error': 'JWT config missing'}), 500
    return jsonify({'success': True, 'token': token})

def _get_webmail_hostname():
    from app.core.utils import get_label
    try:
        containers = docker_client.containers.list()
        for c in containers:
            labels = c.labels or {}
            if get_label(labels, 'enable', '').lower() not in ('true', '1', 'yes'):
                continue
            hostname = get_label(labels, 'hostname', '')
            service = get_label(labels, 'service', '')
            if hostname and 'webmail' in service.lower():
                return hostname
        for c in containers:
            labels = c.labels or {}
            if get_label(labels, 'enable', '').lower() not in ('true', '1', 'yes'):
                continue
            hostname = get_label(labels, 'hostname', '')
            if hostname and c.name and 'webmail' in c.name.lower():
                return hostname
    except Exception:
        pass
    return None


@email_bp.route('/sso/callback', methods=['GET'])
@login_required
def sso_callback():
    username = current_user.get_id()
    token = _generate_jwt(username)
    if not token:
        return "JWT configuration missing. Please setup email first.", 500
    return_to = request.args.get('return_to', '')
    webmail_hostname = _get_webmail_hostname()
    if webmail_hostname:
        allowed_domains = {webmail_hostname}
        if not return_to or return_to not in allowed_domains:
            return_to = webmail_hostname
    else:
        allowed_domains = set()
        for zone_name in config.EMAIL_CONFIG.get('domains', {}).keys():
            allowed_domains.add(f"mail.{zone_name}")
        if not return_to or return_to not in allowed_domains:
            return_to = next(iter(allowed_domains), '')
    if not return_to:
        return "No webmail domain configured.", 500
    return redirect(f"https://{return_to}/auth/callback?token={token}")

def _generate_jwt(username, mailboxes=None, role='admin', expiry_seconds=None):
    email_cfg = config.EMAIL_CONFIG
    if not email_cfg or 'jwt_signing_key' not in email_cfg:
        return None

    private_key = serialization.load_pem_private_key(
        email_cfg['jwt_signing_key'].encode('utf-8'),
        password=None
    )

    if mailboxes is None:
        mailboxes = [
            m for d in email_cfg.get('domains', {}).values()
            for m in d.get('mailboxes', {}).keys()
        ]

    if expiry_seconds is None:
        expiry_seconds = config.EMAIL_JWT_EXPIRY_SECONDS

    now = int(time.time())
    payload = {
        "sub": username,
        "iss": config.EMAIL_JWT_ISSUER,
        "aud": config.EMAIL_JWT_AUDIENCE,
        "iat": now,
        "exp": now + expiry_seconds,
        "mailboxes": mailboxes,
        "role": role,
    }

    return jwt.encode(payload, private_key, algorithm=config.EMAIL_JWT_ALGORITHM)


@email_bp.route('/mailbox/set-password', methods=['POST'])
@login_required
def set_mailbox_password():
    data = request.get_json(force=True, silent=True) or {}
    address = data.get('address', '')
    domain = data.get('domain', '')
    password = data.get('password', '')

    if len(password) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters'}), 400

    email_cfg = config.EMAIL_CONFIG
    if domain not in email_cfg.get('domains', {}) or address not in email_cfg['domains'][domain].get('mailboxes', {}):
        return jsonify({'success': False, 'error': 'Mailbox not found'}), 404

    email_cfg['domains'][domain]['mailboxes'][address]['password_hash'] = generate_password_hash(password)
    save_email_config(email_cfg)
    return jsonify({'success': True})


@email_bp.route('/auth/login', methods=['POST', 'OPTIONS'])
@limiter.limit("5 per 5 minutes")
def mailbox_login():
    origin = _webmail_origin()

    if request.method == 'OPTIONS':
        response = current_app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'POST'
        return response

    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email', '').lower().strip()
    password = data.get('password', '')

    email_cfg = config.EMAIL_CONFIG
    mailbox_data = None

    for d in email_cfg.get('domains', {}).values():
        if email in d.get('mailboxes', {}):
            mailbox_data = d['mailboxes'][email]
            break

    _dummy = 'pbkdf2:sha256:600000$dummy$' + 'a' * 64
    stored_hash = mailbox_data.get('password_hash', '') if mailbox_data else _dummy

    if not stored_hash or not check_password_hash(stored_hash, password) or mailbox_data is None:
        response = jsonify({'success': False, 'error': 'Invalid email or password'})
        response.headers['Access-Control-Allow-Origin'] = origin
        return response, 401

    token = _generate_jwt(email, mailboxes=[email], role='user', expiry_seconds=28800)
    if not token:
        return jsonify({'success': False, 'error': 'Auth configuration error'}), 500

    response = jsonify({'success': True, 'token': token})
    response.headers['Access-Control-Allow-Origin'] = origin
    return response

@email_bp.route('/backup', methods=['GET'])
@login_required
def email_backup():
    import requests
    from flask import Response, stream_with_context
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    url = f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/backup"
    try:
        req = requests.get(url, headers={'Authorization': f'Bearer {token}'}, stream=True, timeout=30)
        req.raise_for_status()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return Response(
        stream_with_context(req.iter_content(chunk_size=8192)),
        content_type=req.headers.get('content-type', 'application/zip'),
        headers={'Content-Disposition': req.headers.get('content-disposition', 'attachment; filename="dockflare_email_backup.zip"')}
    )

@email_bp.route('/restore', methods=['POST'])
@login_required
def email_restore():
    import requests
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename.endswith('.zip'):
        return jsonify({'success': False, 'error': 'Must be a ZIP file'}), 400
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'success': False, 'error': 'JWT configuration missing'}), 500
    url = f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/restore"
    try:
        resp = requests.post(url, headers={'Authorization': f'Bearer {token}'}, files={'file': (file.filename, file.stream, file.mimetype)}, timeout=300)
        resp.raise_for_status()
        return jsonify({'success': True})
    except Exception as e:
        try:
            err_data = resp.json()
            return jsonify({'success': False, 'error': err_data.get('error', str(e))}), 500
        except Exception:
            return jsonify({'success': False, 'error': str(e)}), 500

@email_bp.route('/mail-stats', methods=['GET'])
@login_required
def mail_stats():
    import requests
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/stats",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/catch-all/status', methods=['GET'])
@login_required
def catch_all_status():
    import requests
    domain = request.args.get('domain', '')
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/catch-all/{domain}",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/catch-all/enable', methods=['POST'])
@login_required
def catch_all_enable():
    import requests
    data = request.get_json(force=True, silent=True) or {}
    domain = data.get('domain', '')
    target = data.get('target_address', '')
    email_cfg = config.EMAIL_CONFIG
    if domain not in email_cfg.get('domains', {}):
        return jsonify({'success': False, 'error': 'Domain not found'}), 404
    if target not in email_cfg['domains'][domain].get('mailboxes', {}):
        return jsonify({'success': False, 'error': 'Target mailbox not found in this domain'}), 400
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.post(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/catch-all/{domain}",
            json={'mailbox_address': target},
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        if resp.ok:
            email_cfg['domains'][domain]['catch_all_address'] = target
            save_email_config(email_cfg)
            try:
                _redeploy_inbound_worker(email_cfg, domain)
            except Exception as e:
                logging.warning(f"catch_all_enable: worker redeploy failed: {e}")
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/catch-all/disable', methods=['POST'])
@login_required
def catch_all_disable():
    import requests
    data = request.get_json(force=True, silent=True) or {}
    domain = data.get('domain', '')
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.delete(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/catch-all/{domain}",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        if resp.ok:
            email_cfg = config.EMAIL_CONFIG
            if domain in email_cfg.get('domains', {}):
                email_cfg['domains'][domain].pop('catch_all_address', None)
                save_email_config(email_cfg)
                try:
                    _redeploy_inbound_worker(email_cfg, domain)
                except Exception as e:
                    logging.warning(f"catch_all_disable: worker redeploy failed: {e}")
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/mailbox/auto-responder', methods=['GET'])
@login_required
def get_mailbox_auto_responder():
    import requests
    address = request.args.get('address', '')
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/mailboxes/{address}/auto-responder",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/mailbox/auto-responder', methods=['POST'])
@login_required
def set_mailbox_auto_responder():
    import requests
    data = request.get_json(force=True, silent=True) or {}
    address = data.pop('address', '')
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.post(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/mailboxes/{address}/auto-responder",
            json=data,
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/mailbox/auto-responder', methods=['DELETE'])
@login_required
def delete_mailbox_auto_responder():
    import requests
    data = request.get_json(force=True, silent=True) or {}
    address = data.get('address', '')
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.delete(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/mailboxes/{address}/auto-responder",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/auto-responders', methods=['GET'])
@login_required
def list_auto_responders():
    import requests
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/auto-responders",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/auth/change-password', methods=['POST', 'OPTIONS'])
@limiter.limit("5 per 5 minutes")
def mailbox_change_password():
    origin = _webmail_origin()
    if request.method == 'OPTIONS':
        response = current_app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'POST'
        return response
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    token_str = auth_header[7:]
    email_cfg = config.EMAIL_CONFIG
    try:
        private_key = serialization.load_pem_private_key(
            email_cfg['jwt_signing_key'].encode('utf-8'), password=None
        )
        public_key = private_key.public_key()
        payload = jwt.decode(
            token_str, public_key,
            algorithms=[config.EMAIL_JWT_ALGORITHM],
            audience=config.EMAIL_JWT_AUDIENCE,
            issuer=config.EMAIL_JWT_ISSUER,
        )
        mailbox_address = payload.get('sub', '')
        if mailbox_address not in payload.get('mailboxes', []):
            raise ValueError('mailbox not in token claims')
    except Exception:
        response = jsonify({'success': False, 'error': 'Invalid or expired token'})
        response.headers['Access-Control-Allow-Origin'] = origin
        return response, 401
    data = request.get_json(force=True, silent=True) or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    if len(new_password) < 8:
        response = jsonify({'success': False, 'error': 'New password must be at least 8 characters'})
        response.headers['Access-Control-Allow-Origin'] = origin
        return response, 400
    mailbox_data = None
    domain_key = None
    for domain, dcfg in email_cfg.get('domains', {}).items():
        if mailbox_address in dcfg.get('mailboxes', {}):
            mailbox_data = dcfg['mailboxes'][mailbox_address]
            domain_key = domain
            break
    if not mailbox_data:
        response = jsonify({'success': False, 'error': 'Mailbox not found'})
        response.headers['Access-Control-Allow-Origin'] = origin
        return response, 404
    stored_hash = mailbox_data.get('password_hash', '')
    if not stored_hash or not check_password_hash(stored_hash, current_password):
        response = jsonify({'success': False, 'error': 'Current password is incorrect'})
        response.headers['Access-Control-Allow-Origin'] = origin
        return response, 401
    email_cfg['domains'][domain_key]['mailboxes'][mailbox_address]['password_hash'] = generate_password_hash(new_password)
    save_email_config(email_cfg)
    response = jsonify({'success': True})
    response.headers['Access-Control-Allow-Origin'] = origin
    return response


@email_bp.route('/logs/send-log', methods=['GET'])
@login_required
def email_send_log():
    import requests
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/logs/send-log",
            headers={'Authorization': f'Bearer {token}'},
            params=request.args,
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/logs/bounce-log', methods=['GET'])
@login_required
def email_bounce_log():
    import requests
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/logs/bounce-log",
            headers={'Authorization': f'Bearer {token}'},
            params=request.args,
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


@email_bp.route('/logs/stats', methods=['GET'])
@login_required
def email_log_stats():
    import requests
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = requests.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/logs/stats",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 502


def _check_internal_request():
    # Block any request that carries Cloudflare edge headers (all public internet
    # requests via the CF tunnel have CF-Ray; internal Docker requests never do)
    if request.headers.get('CF-Ray') or request.headers.get('CF-Connecting-IP'):
        return False

    # Block non-private IPs
    try:
        ip = ipaddress.ip_address(request.remote_addr or '')
        if not ip.is_private:
            return False
    except ValueError:
        return False

    # If a shared secret is configured, require it
    expected = os.environ.get('INTERNAL_BOOTSTRAP_SECRET', '')
    if expected:
        provided = request.headers.get('X-Bootstrap-Token', '')
        if not provided or not hmac.compare_digest(provided, expected):
            return False

    return True


@email_bp.route('/internal/config', methods=['GET'])
def internal_mail_config():
    if not _check_internal_request():
        return jsonify({'error': 'forbidden'}), 403

    cfg = config.EMAIL_CONFIG
    if not cfg or not cfg.get('enabled') or not cfg.get('domains'):
        return jsonify({'configured': False})

    if 'vapid_private_key' not in cfg or not cfg.get('vapid_private_key'):
        vapid_key = ec.generate_private_key(ec.SECP256R1())
        cfg['vapid_private_key'] = vapid_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        cfg['vapid_public_key'] = base64.urlsafe_b64encode(
            vapid_key.public_key().public_bytes(
                encoding=serialization.Encoding.X962,
                format=serialization.PublicFormat.UncompressedPoint
            )
        ).rstrip(b'=').decode()
        save_email_config(cfg)
        logging.info("Generated VAPID keys for existing email config")

    domains_out = {}
    for zone_name, d in cfg['domains'].items():
        domains_out[zone_name] = {
            'r2_bucket': d.get('r2_bucket', ''),
            'r2_access_key_id': d.get('r2_access_key_id', ''),
            'r2_secret_access_key': d.get('r2_secret_access_key', ''),
            'r2_endpoint_url': d.get('r2_endpoint_url', ''),
            'webhook_secret': d.get('webhook_secret', ''),
            'outbound_worker_url': d.get('outbound_worker_url', ''),
            'outbound_auth_secret': d.get('outbound_auth_secret', ''),
            'quota_kv_namespace_id': d.get('quota_kv_namespace_id', ''),
            'mailboxes': {
                addr: {'display_name': m.get('display_name', ''), 'quota_bytes': m.get('quota_bytes', 10737418240)}
                for addr, m in d.get('mailboxes', {}).items()
            }
        }
    return jsonify({
        'configured': True,
        'jwt_public_key': cfg.get('jwt_public_key', ''),
        'jwt_algorithm': config.EMAIL_JWT_ALGORITHM,
        'jwt_issuer': config.EMAIL_JWT_ISSUER,
        'jwt_audience': config.EMAIL_JWT_AUDIENCE,
        'vapid_private_key': cfg.get('vapid_private_key', ''),
        'vapid_public_key': cfg.get('vapid_public_key', ''),
        'domains': domains_out
    })

@email_bp.route('/internal/quota-kv-sync', methods=['POST'])
def quota_kv_sync():
    if not _check_internal_request():
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True, silent=True) or {}
    domain = data.get('domain')
    address = data.get('address')
    action = data.get('action')
    if not domain or not address or action not in ('block', 'unblock'):
        return jsonify({'error': 'missing domain, address, or valid action'}), 400
    cfg = config.EMAIL_CONFIG
    if not cfg or domain not in cfg.get('domains', {}):
        return jsonify({'status': 'domain_not_found'}), 200
    kv_ns_id = cfg['domains'][domain].get('quota_kv_namespace_id')
    if not kv_ns_id:
        return jsonify({'status': 'no_kv'}), 200
    try:
        if action == 'block':
            email_manager.update_kv_entry(kv_ns_id, address, {"blocked": True})
        else:
            email_manager.delete_kv_entry(kv_ns_id, address)
    except Exception as e:
        logging.warning(f"quota-kv-sync {action} failed for {address}: {e}")
        return jsonify({'error': str(e)}), 500
    return jsonify({'status': 'ok', 'action': action})


@email_bp.route('/internal/alias-kv-sync', methods=['POST'])
def alias_kv_sync():
    if not _check_internal_request():
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True, silent=True) or {}
    domain = data.get('domain')
    alias_address = data.get('alias_address')
    action = data.get('action')
    mailbox_address = data.get('mailbox_address')
    if not domain or not alias_address or action not in ('put', 'delete'):
        return jsonify({'error': 'missing domain, alias_address, or valid action'}), 400
    if action == 'put' and not mailbox_address:
        return jsonify({'error': 'mailbox_address required for put'}), 400
    cfg = config.EMAIL_CONFIG
    if not cfg or domain not in cfg.get('domains', {}):
        return jsonify({'status': 'domain_not_found'}), 200
    kv_ns_id = cfg['domains'][domain].get('quota_kv_namespace_id')
    if not kv_ns_id:
        return jsonify({'status': 'no_kv'}), 200
    kv_key = f"alias::{alias_address}"
    try:
        if action == 'put':
            email_manager.update_kv_entry(kv_ns_id, kv_key, {"mailbox": mailbox_address})
        else:
            email_manager.delete_kv_entry(kv_ns_id, kv_key)
    except Exception as e:
        logging.warning(f"alias-kv-sync {action} failed for {alias_address}: {e}")
        return jsonify({'error': str(e)}), 500
    return jsonify({'status': 'ok', 'action': action})


@email_bp.route('/domain/<domain>/aliases', methods=['GET'])
@login_required
def domain_aliases(domain):
    import requests as req_lib
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = req_lib.get(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/system/aliases",
            headers={'Authorization': f'Bearer {token}'},
            params={'domain': domain},
            timeout=10,
        )
        if resp.ok:
            return jsonify(resp.json())
        return jsonify({'error': 'mail-manager unreachable'}), 502
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@email_bp.route('/alias/<path:address>/delete', methods=['POST'])
@login_required
def admin_delete_alias(address):
    import requests as req_lib
    token = _generate_jwt(current_user.get_id(), role='admin')
    if not token:
        return jsonify({'error': 'JWT configuration missing'}), 500
    try:
        resp = req_lib.delete(
            f"{config.MAIL_MANAGER_INTERNAL_URL}/api/v1/aliases/{address}",
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )
        if resp.ok:
            return jsonify({'status': 'deleted'})
        return jsonify({'error': resp.text[:200]}), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _restart_mail_container():
    try:
        container = docker_client.containers.get('dockflare-mail-manager')
        container.restart()
        logging.info("Restarted dockflare-mail-manager")
    except Exception as e:
        logging.warning(f"Could not restart dockflare-mail-manager: {e}")
