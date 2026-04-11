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
from cryptography.hazmat.primitives.asymmetric import ed25519
from app import config, docker_client
from app.core import email_manager
from app.core.cloudflare_api import list_account_zones
from app.web.config_loader import load_encrypted_config, load_encrypted_config_with_cipher, config_file_path

_WORKER_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'core', 'worker_templates')

def _read_worker_template(filename):
    with open(os.path.join(_WORKER_TEMPLATE_DIR, filename), 'r') as f:
        return f.read()

email_bp = Blueprint('email', __name__, url_prefix='/email')

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

@email_bp.route('', methods=['GET'])
@login_required
def email_page():
    zones = list_account_zones() or []
    return render_template('email.html', zones=zones, email_config=config.EMAIL_CONFIG, email_enabled=config.EMAIL_ENABLED)

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
            
        webhook_secret = secrets.token_hex(32)
        outbound_auth_secret = secrets.token_hex(32)
        inbound_worker_name = f"dockflare-mail-inbound-{zone_name.replace('.', '-')}"
        outbound_worker_name = f"dockflare-mail-outbound-{zone_name.replace('.', '-')}"
        webmail_hostname = f"mail.{zone_name}"
        webhook_url = f"https://{webmail_hostname}/api/v1/webhook/inbound"

        inbound_bindings = [
            {"type": "r2_bucket", "name": "EMAIL_BUCKET", "bucket_name": bucket_name},
            {"type": "plain_text", "name": "WEBHOOK_URL", "text": webhook_url},
            {"type": "secret_text", "name": "WEBHOOK_SECRET", "text": webhook_secret},
            {"type": "plain_text", "name": "ALLOWED_RECIPIENTS", "text": "[]"}
        ]
        email_manager.deploy_worker(inbound_worker_name, _read_worker_template('inbound_worker.js'), inbound_bindings)
        email_manager.set_worker_cron(inbound_worker_name, ['*/5 * * * *'])
        email_manager.setup_catchall_routing_rule(zone_id, inbound_worker_name)

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
            'r2_bucket': bucket_name,
            'r2_access_key_id': r2_access_key_id,
            'r2_secret_access_key': r2_secret_access_key,
            'r2_endpoint_url': r2_endpoint_url,
            'webhook_secret': webhook_secret,
            'inbound_worker_name': inbound_worker_name,
            'outbound_worker_name': outbound_worker_name,
            'outbound_worker_url': outbound_worker_url,
            'outbound_auth_secret': outbound_auth_secret,
            'mailboxes': {}
        }

        save_email_config(email_cfg)
        config.EMAIL_ENABLED = True
        current_app.config['EMAIL_ENABLED'] = True
        _restart_mail_container()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@email_bp.route('/teardown-domain', methods=['POST'])
@login_required
def teardown_domain():
    data = request.get_json(force=True, silent=True) or {}
    zone_name = data.get('zone_name')
    email_cfg = config.EMAIL_CONFIG.copy()
    if 'domains' in email_cfg and zone_name in email_cfg['domains']:
        del email_cfg['domains'][zone_name]
        save_email_config(email_cfg)
        _restart_mail_container()
    return jsonify({'success': True})

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
    webmail_hostname = f"mail.{domain}"
    webhook_url = f"https://{webmail_hostname}/api/v1/webhook/inbound"
    inbound_bindings = [
        {"type": "r2_bucket", "name": "EMAIL_BUCKET", "bucket_name": d['r2_bucket']},
        {"type": "plain_text", "name": "WEBHOOK_URL", "text": webhook_url},
        {"type": "secret_text", "name": "WEBHOOK_SECRET", "text": d['webhook_secret']},
        {"type": "plain_text", "name": "ALLOWED_RECIPIENTS", "text": json.dumps(all_addresses)}
    ]
    email_manager.deploy_worker(d['inbound_worker_name'], _read_worker_template('inbound_worker.js'), inbound_bindings)
    email_manager.set_worker_cron(d['inbound_worker_name'], ['*/5 * * * *'])

@email_bp.route('/mailbox/create', methods=['POST'])
@login_required
def create_mailbox():
    data = request.get_json(force=True, silent=True) or {}
    address = data.get('address')
    display_name = data.get('display_name')
    domain = data.get('domain')

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

@email_bp.route('/redeploy-workers', methods=['POST'])
@login_required
def redeploy_workers():
    email_cfg = config.EMAIL_CONFIG.copy()
    domains = email_cfg.get('domains', {})
    for domain in domains:
        try:
            _redeploy_inbound_worker(email_cfg, domain)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Inbound redeploy failed for {domain}: {e}'}), 500
        try:
            _redeploy_outbound_worker(email_cfg, domain)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Outbound redeploy failed for {domain}: {e}'}), 500
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

@email_bp.route('/sso/callback', methods=['GET'])
@login_required
def sso_callback():
    username = current_user.get_id()
    token = _generate_jwt(username)
    if not token:
        return "JWT configuration missing. Please setup email first.", 500
    return_to = request.args.get('return_to', '')
    allowed_domains = set()
    for zone_name in config.EMAIL_CONFIG.get('domains', {}).keys():
        allowed_domains.add(f"mail.{zone_name}")
    if not return_to or return_to not in allowed_domains:
        return_to = next(iter(allowed_domains), '')
    if not return_to:
        return "No webmail domain configured.", 500
    return redirect(f"https://{return_to}/auth/callback?token={token}")

def _generate_jwt(username):
    email_cfg = config.EMAIL_CONFIG
    if not email_cfg or 'jwt_signing_key' not in email_cfg:
        return None
        
    private_key_pem = email_cfg['jwt_signing_key']
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None
    )
    
    mailboxes = []
    for d, d_data in email_cfg.get('domains', {}).items():
        for m in d_data.get('mailboxes', {}).keys():
            mailboxes.append(m)
            
    now = int(time.time())
    payload = {
        "sub": username,
        "iss": config.EMAIL_JWT_ISSUER,
        "aud": config.EMAIL_JWT_AUDIENCE,
        "iat": now,
        "exp": now + config.EMAIL_JWT_EXPIRY_SECONDS,
        "mailboxes": mailboxes,
        "role": "admin"
    }
    
    token = jwt.encode(payload, private_key, algorithm=config.EMAIL_JWT_ALGORITHM)
    return token

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
            'mailboxes': {
                addr: {'display_name': m.get('display_name', '')}
                for addr, m in d.get('mailboxes', {}).items()
            }
        }
    return jsonify({
        'configured': True,
        'jwt_public_key': cfg.get('jwt_public_key', ''),
        'jwt_algorithm': config.EMAIL_JWT_ALGORITHM,
        'jwt_issuer': config.EMAIL_JWT_ISSUER,
        'jwt_audience': config.EMAIL_JWT_AUDIENCE,
        'domains': domains_out
    })

def _restart_mail_container():
    try:
        container = docker_client.containers.get('dockflare-mail-manager')
        container.restart()
        logging.info("Restarted dockflare-mail-manager")
    except Exception as e:
        logging.warning(f"Could not restart dockflare-mail-manager: {e}")
