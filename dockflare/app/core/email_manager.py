import logging
import requests
import json
import boto3
from botocore.config import Config as BotoConfig
from app import config
from app.core.cloudflare_api import cf_api_request, dns_semaphore

def check_token_permissions():
    try:
        perms = {
            "email_routing": False,
            "workers": False,
            "r2": False,
            "workers_kv": False
        }
        token = getattr(config, 'CF_API_TOKEN', '') or ''
        if token.startswith('cfat_'):
            verify_res = cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/tokens/verify')
        else:
            verify_res = cf_api_request('GET', '/user/tokens/verify')
        if not verify_res or not verify_res.get('success'):
            return perms
        try:
            cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/email/routing/addresses')
            perms["email_routing"] = True
        except Exception:
            perms["email_routing"] = False
        try:
            cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/workers/scripts')
            perms["workers"] = True
        except Exception:
            perms["workers"] = False
        try:
            cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/r2/buckets')
            perms["r2"] = True
        except Exception as e:
            perms["r2"] = False
            if '10042' in str(e):
                perms["r2_note"] = "R2 must be enabled in the Cloudflare Dashboard before use"
        try:
            cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces?per_page=1')
            perms["workers_kv"] = True
        except Exception:
            perms["workers_kv"] = False
        return perms
    except Exception as e:
        logging.error(f"Error checking token permissions: {e}")
        return {"email_routing": False, "workers": False, "r2": False, "workers_kv": False}

def enable_email_routing(zone_id):
    try:
        return cf_api_request('POST', f'/zones/{zone_id}/email/routing/enable', log_errors=False)
    except Exception as e:
        err_str = str(e)
        if '2004' in err_str or 'already enabled' in err_str.lower() or 'Unprocessable' in err_str:
            logging.info(f"Email routing already enabled on zone {zone_id}, continuing")
            return {}
        if '403' in err_str or 'Forbidden' in err_str or '10000' in err_str or 'Authentication' in err_str:
            logging.info(f"Email routing enable not permitted (zone {zone_id}); CF auto-activates via MX records")
            return {}
        logging.warning(f"Could not enable email routing on zone {zone_id}: {e}")
        raise

def enable_email_sending(zone_id, zone_name):
    try:
        subdomain = f"mail.{zone_name}"
        res = cf_api_request('POST', f'/zones/{zone_id}/email/sending/subdomains', json_data={"name": subdomain})
        logging.info(f"Email sending enabled for {zone_name} (subdomain: {subdomain})")
        return res
    except Exception as e:
        err_str = str(e)
        if 'already exists' in err_str.lower() or '2004' in err_str or 'duplicate' in err_str.lower():
            logging.info(f"Email sending subdomain already exists for {zone_name}, continuing")
            return {}
        logging.warning(f"Could not enable email sending for {zone_name} (may require manual activation in CF Dashboard): {e}")
        return None

def get_email_routing_status(zone_id):
    try:
        res = cf_api_request('GET', f'/zones/{zone_id}/email/routing')
        return res.get('result', {})
    except Exception as e:
        logging.error(f"Error getting email routing status: {e}")
        return {}

def create_dns_record_generic(zone_id, type, name, content, priority=None):
    with dns_semaphore:
        data = {
            "type": type,
            "name": name,
            "content": content,
            "proxied": False,
            "ttl": 1
        }
        if priority is not None:
            data["priority"] = priority
        return cf_api_request('POST', f'/zones/{zone_id}/dns_records', json_data=data)

def find_dns_record_generic(zone_id, type, name):
    with dns_semaphore:
        res = cf_api_request('GET', f'/zones/{zone_id}/dns_records?type={type}&name={name}')
        if res.get('success') and res.get('result'):
            return res['result'][0]
        return None

def delete_dns_record_generic(zone_id, record_id):
    with dns_semaphore:
        return cf_api_request('DELETE', f'/zones/{zone_id}/dns_records/{record_id}')

def _safe_create_dns(zone_id, type, name, content, priority=None):
    try:
        create_dns_record_generic(zone_id, type, name, content, priority)
    except Exception as e:
        cf_codes = []
        err_text = str(e)
        try:
            resp = getattr(e, 'response', None)
            if resp is not None:
                raw = resp.text
                err_text = err_text + ' ' + raw
                cf_codes = [err.get('code') for err in json.loads(raw).get('errors', [])]
        except Exception:
            pass
        cf_code = getattr(e, 'cf_error_code', None)
        if cf_code:
            cf_codes.append(cf_code)
        skip_codes = {81057, 81053, 81058, 890190}
        if cf_codes and any(c in skip_codes for c in cf_codes):
            logging.info(f"DNS record {type} {name} skipped (already exists or managed by CF Email Routing, codes={cf_codes})")
        elif '890190' in err_text or 'already exists' in err_text.lower() or 'managed by Email Routing' in err_text:
            logging.info(f"DNS record {type} {name} skipped: {err_text[:200]}")
        else:
            logging.error(f"DNS record {type} {name} failed, cf_codes={cf_codes}, err={err_text[:500]}")
            raise

def setup_email_dns_records(zone_id, zone_name):
    try:
        res = cf_api_request('GET', f'/zones/{zone_id}/email/routing/dns', log_errors=False)
        required = res.get('result', [])
        for record in required:
            rtype = record.get('type')
            rname = record.get('name')
            rcontent = record.get('content')
            rpriority = record.get('priority')
            if rtype and rname and rcontent:
                _safe_create_dns(zone_id, rtype, rname, rcontent, priority=rpriority)
    except Exception as e:
        logging.info(f"Could not fetch email routing DNS from CF API (falling back to defaults): {e}")
        _safe_create_dns(zone_id, 'MX', zone_name, 'route1.mx.cloudflare.net', priority=14)
        _safe_create_dns(zone_id, 'MX', zone_name, 'route2.mx.cloudflare.net', priority=36)
        _safe_create_dns(zone_id, 'MX', zone_name, 'route3.mx.cloudflare.net', priority=88)
        _safe_create_dns(zone_id, 'TXT', zone_name, 'v=spf1 include:_spf.mx.cloudflare.net ~all')
        _safe_create_dns(zone_id, 'TXT', f'_dmarc.{zone_name}', f'v=DMARC1; p=quarantine; rua=mailto:dmarc@{zone_name}')

def get_email_sending_status(zone_id, zone_name):
    try:
        res = cf_api_request('GET', f'/zones/{zone_id}/dns_records?type=TXT&search=_domainkey', log_errors=False)
        records = res.get('result', [])
        suffix = f'._domainkey.{zone_name}'
        for r in records:
            if r.get('name', '').endswith(suffix):
                return 'configured'
        return 'not_configured'
    except Exception:
        return 'unknown'

def verify_email_dns_records(zone_id, zone_name):
    res = cf_api_request('GET', f'/zones/{zone_id}/dns_records')
    records = res.get('result', [])
    status = {'mx': False, 'spf': False, 'dmarc': False}
    mx_count = 0
    for r in records:
        if r['type'] == 'MX' and r['name'] == zone_name and 'mx.cloudflare.net' in r['content']:
            mx_count += 1
        if r['type'] == 'TXT' and r['name'] == zone_name and 'v=spf1' in r['content']:
            status['spf'] = True
        if r['type'] == 'TXT' and r['name'] == f'_dmarc.{zone_name}' and 'v=DMARC1' in r['content']:
            status['dmarc'] = True
    if mx_count >= 3:
        status['mx'] = True
    return status

def create_r2_bucket(bucket_name):
    try:
        return cf_api_request('PUT', f'/accounts/{config.CF_ACCOUNT_ID}/r2/buckets/{bucket_name}')
    except Exception as e:
        cf_codes = []
        err_text = str(e)
        try:
            resp = getattr(e, 'response', None)
            if resp is not None:
                raw = resp.text
                err_text = err_text + ' ' + raw
                cf_codes = [err.get('code') for err in json.loads(raw).get('errors', [])]
                if resp.status_code == 409:
                    logging.info(f"R2 bucket {bucket_name} already exists (409), continuing")
                    return {"success": True, "result": {"name": bucket_name}}
        except Exception:
            pass
        if 10006 in cf_codes or 'already exists' in err_text.lower() or '409' in err_text:
            logging.info(f"R2 bucket {bucket_name} already exists, continuing")
            return {"success": True, "result": {"name": bucket_name}}
        raise

def get_r2_s3_credentials():
    import hashlib
    token = getattr(config, 'CF_API_TOKEN', '') or ''
    if token.startswith('cfat_'):
        token_verify = cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/tokens/verify')
    else:
        token_verify = cf_api_request('GET', '/user/tokens/verify')
    token_id = token_verify.get('result', {}).get('id', '')
    secret = hashlib.sha256(config.CF_API_TOKEN.encode()).hexdigest()
    return {
        'access_key_id': token_id,
        'secret_access_key': secret,
        'endpoint_url': f"https://{config.CF_ACCOUNT_ID}.r2.cloudflarestorage.com"
    }

def get_workers_subdomain():
    res = cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/workers/subdomain')
    return res.get('result', {}).get('subdomain', '')

def deploy_worker(script_name, script_content, bindings):
    url = f"{config.CF_API_BASE_URL}/accounts/{config.CF_ACCOUNT_ID}/workers/scripts/{script_name}"
    metadata = {
        "main_module": "worker.js",
        "bindings": bindings,
        "compatibility_date": "2024-01-01"
    }
    files = {
        "metadata": (None, json.dumps(metadata), "application/json"),
        "worker.js": ("worker.js", script_content, "application/javascript+module")
    }
    headers = {
        "Authorization": f"Bearer {config.CF_API_TOKEN}"
    }
    response = requests.put(url, files=files, headers=headers)
    response.raise_for_status()
    result = response.json()
    try:
        subdomain_url = f"{config.CF_API_BASE_URL}/accounts/{config.CF_ACCOUNT_ID}/workers/scripts/{script_name}/subdomain"
        requests.post(subdomain_url, headers=headers, json={"enabled": True})
    except Exception as e:
        logging.warning(f"Could not enable workers.dev for {script_name}: {e}")
    return result

def set_worker_cron(script_name, cron_expressions):
    """Set cron triggers for a worker via the Schedules API.
    cron_expressions: list of cron strings, e.g. ['*/5 * * * *']
    Passing an empty list removes all cron triggers.
    """
    schedules = [{"cron": c} for c in cron_expressions]
    try:
        result = cf_api_request(
            'PUT',
            f'/accounts/{config.CF_ACCOUNT_ID}/workers/scripts/{script_name}/schedules',
            json_data=schedules
        )
        logging.info(f"Cron triggers set for worker {script_name}: {cron_expressions}")
        return result
    except Exception as e:
        logging.error(f"Failed to set cron triggers for {script_name}: {e}")
        raise

def delete_worker(script_name):
    return cf_api_request('DELETE', f'/accounts/{config.CF_ACCOUNT_ID}/workers/scripts/{script_name}')

def _find_email_routing_rule(zone_id, address):
    try:
        response = list_email_routing_rules(zone_id)
        rules = response.get('result') or []
    except Exception as e:
        logging.warning(f"Could not list email routing rules for zone {zone_id}: {e}")
        return None
    target = str(address or '').strip().lower()
    for rule in rules:
        for matcher in rule.get('matchers') or []:
            if (
                matcher.get('type') == 'literal'
                and matcher.get('field') == 'to'
                and str(matcher.get('value', '')).strip().lower() == target
            ):
                return rule
    return None

def create_email_routing_rule(zone_id, address, worker_name):
    data = {
        "matchers": [{"type": "literal", "field": "to", "value": address}],
        "actions": [{"type": "worker", "value": [worker_name]}],
        "enabled": True,
        "name": f"DockFlare: {address}"
    }
    existing = _find_email_routing_rule(zone_id, address)
    if existing and existing.get('id'):
        logging.info(f"Email routing rule for {address} already exists; updating it instead of creating")
        return cf_api_request('PUT', f'/zones/{zone_id}/email/routing/rules/{existing["id"]}', json_data=data)
    try:
        return cf_api_request('POST', f'/zones/{zone_id}/email/routing/rules', json_data=data)
    except Exception as e:
        error_text = str(e).lower()
        if '409' not in error_text and 'duplicated' not in error_text and 'already exists' not in error_text:
            raise
        existing = _find_email_routing_rule(zone_id, address)
        if not existing or not existing.get('id'):
            raise
        logging.info(f"Email routing rule for {address} already exists (409); updating it")
        return cf_api_request('PUT', f'/zones/{zone_id}/email/routing/rules/{existing["id"]}', json_data=data)

def delete_email_routing_rule(zone_id, rule_id):
    return cf_api_request('DELETE', f'/zones/{zone_id}/email/routing/rules/{rule_id}')

def list_email_routing_rules(zone_id):
    return cf_api_request('GET', f'/zones/{zone_id}/email/routing/rules')

def disable_email_routing(zone_id):
    try:
        return cf_api_request('POST', f'/zones/{zone_id}/email/routing/disable', json_data={})
    except Exception as e:
        logging.warning(f"Could not disable email routing for zone {zone_id}: {e}")

def reset_catchall_to_drop(zone_id):
    data = {
        "matchers": [{"type": "all"}],
        "actions": [{"type": "drop"}],
        "enabled": True,
        "name": "DockFlare: Drop All"
    }
    try:
        return cf_api_request('PUT', f'/zones/{zone_id}/email/routing/rules/catch_all', json_data=data)
    except Exception as e:
        logging.warning(f"Could not reset catch_all to drop for zone {zone_id}: {e}")

def empty_and_delete_r2_bucket(bucket_name, r2_endpoint, r2_key_id, r2_secret):
    try:
        client = boto3.client(
            's3',
            endpoint_url=r2_endpoint,
            aws_access_key_id=r2_key_id,
            aws_secret_access_key=r2_secret,
            config=BotoConfig(signature_version='s3v4'),
        )
        paginator = client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            objects = page.get('Contents', [])
            if objects:
                client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': [{'Key': o['Key']} for o in objects]}
                )
    except Exception as e:
        logging.warning(f"Could not empty R2 bucket {bucket_name}: {e}")
    try:
        cf_api_request('DELETE', f'/accounts/{config.CF_ACCOUNT_ID}/r2/buckets/{bucket_name}')
    except Exception as e:
        logging.warning(f"Could not delete R2 bucket {bucket_name}: {e}")

def scrub_email_dns_records(zone_id, zone_name):
    errors = []
    for rtype, name in [('MX', zone_name), ('TXT', zone_name), ('TXT', f'_dmarc.{zone_name}')]:
        try:
            res = cf_api_request('GET', f'/zones/{zone_id}/dns_records?type={rtype}&name={name}')
            for record in res.get('result', []):
                if rtype == 'TXT' and name == zone_name and 'v=spf1' not in record.get('content', ''):
                    continue
                try:
                    delete_dns_record_generic(zone_id, record['id'])
                except Exception as e:
                    errors.append(f"DNS {rtype} {name}: {e}")
        except Exception as e:
            errors.append(f"DNS list {rtype} {name}: {e}")
    try:
        res = cf_api_request('GET', f'/zones/{zone_id}/dns_records?type=CNAME')
        for record in res.get('result', []):
            if '_domainkey' in record.get('name', ''):
                try:
                    delete_dns_record_generic(zone_id, record['id'])
                except Exception as e:
                    errors.append(f"DNS CNAME {record['name']}: {e}")
    except Exception as e:
        errors.append(f"DNS list CNAME: {e}")
    return errors

def create_kv_namespace(title):
    res = cf_api_request('POST', f'/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces',
                         json_data={'title': title})
    return res.get('result', {}).get('id')


def _list_kv_namespaces_tagged(title):
    page = 1
    while True:
        res = cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces',
                             params={'per_page': 100, 'page': page})
        for ns in res.get('result') or []:
            if ns.get('title') == title:
                return ns.get('id')
        info = res.get('result_info', {})
        if page >= info.get('total_pages', 1):
            break
        page += 1
    return None

def get_or_create_kv_namespace(title):
    existing = _list_kv_namespaces_tagged(title)
    if existing:
        return existing
    try:
        ns_id = create_kv_namespace(title)
        if ns_id:
            return ns_id
    except Exception as e:
        logging.warning(f"Could not create KV namespace '{title}': {e}")
    return _list_kv_namespaces_tagged(title)

def update_kv_entry(namespace_id, key, value_dict):
    url = f"{config.CF_API_BASE_URL}/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces/{namespace_id}/values/{key}"
    headers = {"Authorization": f"Bearer {config.CF_API_TOKEN}", "Content-Type": "text/plain"}
    response = requests.put(url, data=json.dumps(value_dict), headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def delete_kv_entry(namespace_id, key):
    try:
        cf_api_request('DELETE',
                       f'/accounts/{config.CF_ACCOUNT_ID}/storage/kv/namespaces/{namespace_id}/values/{key}')
    except Exception as e:
        logging.warning(f"Could not delete KV entry {key} from {namespace_id}: {e}")

def setup_catchall_routing_rule(zone_id, worker_name):
    data = {
        "matchers": [{"type": "all"}],
        "actions": [{"type": "worker", "value": [worker_name]}],
        "enabled": True,
        "name": "DockFlare: Email Worker Catch-All"
    }
    try:
        current = cf_api_request('GET', f'/zones/{zone_id}/email/routing/rules/catch_all')
        current_actions = (current.get('result') or {}).get('actions', [])
        current_worker = None
        for a in current_actions:
            if a.get('type') == 'worker':
                vals = a.get('value', [])
                current_worker = vals[0] if vals else None
        if current_worker == worker_name:
            logging.info(f"Catch-all worker routing rule already correct for zone {zone_id}")
            return current
    except Exception as e:
        logging.warning(f"Could not GET catch_all rule: {e}")
    logging.info(f"Setting catch-all routing rule to worker {worker_name} via dedicated endpoint")
    return cf_api_request('PUT', f'/zones/{zone_id}/email/routing/rules/catch_all', json_data=data)


WEBHOOK_ACCESS_PATH = "/api/v1/webhook/inbound"
WEBHOOK_ACCESS_APP_NAME = "DockFlare Mail Webhook Bypass"


def _normalize_access_destination(value):
    text = str(value or "").strip().lower()
    if text.startswith("https://"):
        text = text[len("https://"):]
    elif text.startswith("http://"):
        text = text[len("http://"):]
    return text.rstrip("/")


def _access_app_destinations(app):
    destinations = []
    domain = app.get("domain")
    path = app.get("path")
    if domain:
        domain_text = _normalize_access_destination(domain)
        if path and not domain_text.endswith("/" + str(path).strip("/").lower()):
            destinations.append(f"{domain_text}/{str(path).strip('/')}")
        else:
            destinations.append(domain_text)
    for extra in app.get("self_hosted_domains") or []:
        destinations.append(_normalize_access_destination(extra))
    return [d for d in destinations if d]


def _access_destination_covers(destination, host, path):
    destination = _normalize_access_destination(destination)
    if not destination:
        return False
    if "/" in destination:
        dest_host, _, dest_path = destination.partition("/")
        dest_path = "/" + dest_path.lstrip("/")
    else:
        dest_host, dest_path = destination, "/"
    host = _normalize_access_destination(host)
    if dest_host.startswith("*."):
        host_matches = host.endswith(dest_host[1:])
    else:
        host_matches = dest_host == host
    if not host_matches:
        return False
    if dest_path in ("", "/"):
        return True
    return path == dest_path or path.startswith(dest_path.rstrip("/") + "/")


def _find_webhook_bypass_app(apps, host, path):
    target = f"{_normalize_access_destination(host)}{path}"
    for app in apps:
        for destination in _access_app_destinations(app):
            if destination == target:
                return app
    return None


def _app_has_bypass_policy(account_id, app_uuid):
    try:
        response = cf_api_request(
            'GET', f'/accounts/{account_id}/access/apps/{app_uuid}/policies'
        )
        for policy in response.get('result') or []:
            if policy.get('decision') == 'bypass':
                return True
    except Exception as e:
        logging.warning(f"Could not read Access policies for app {app_uuid}: {e}")
    return False


def _create_webhook_bypass_policy(account_id, app_uuid):
    cf_api_request(
        'POST',
        f'/accounts/{account_id}/access/apps/{app_uuid}/policies',
        json_data={
            "name": "DockFlare Webhook Bypass",
            "decision": "bypass",
            "precedence": 1,
            "include": [{"everyone": {}}],
        },
    )


def ensure_webhook_access_bypass(webmail_hostname):
    account_id = getattr(config, 'CF_ACCOUNT_ID', None)
    if not account_id or not webmail_hostname:
        return None

    host = _normalize_access_destination(webmail_hostname)
    path = WEBHOOK_ACCESS_PATH

    try:
        response = cf_api_request(
            'GET', f'/accounts/{account_id}/access/apps', params={"per_page": 100}
        )
        apps = response.get('result') or []
    except Exception as e:
        logging.warning(
            f"Could not check Cloudflare Access for webhook bypass on {host}: {e}. "
            f"The email webhook may be blocked if {host} sits behind Access."
        )
        return None

    existing = _find_webhook_bypass_app(apps, host, path)
    if existing:
        app_uuid = existing.get('id') or existing.get('uid')
        if app_uuid and not _app_has_bypass_policy(account_id, app_uuid):
            try:
                _create_webhook_bypass_policy(account_id, app_uuid)
                logging.info(f"Added missing webhook bypass policy to Access app {app_uuid}")
            except Exception as e:
                logging.warning(f"Could not add webhook bypass policy to {app_uuid}: {e}")
        return app_uuid

    covered = any(
        _access_destination_covers(destination, host, path)
        for app in apps
        for destination in _access_app_destinations(app)
    )
    if not covered:
        return None

    try:
        app_response = cf_api_request(
            'POST',
            f'/accounts/{account_id}/access/apps',
            json_data={
                "name": WEBHOOK_ACCESS_APP_NAME,
                "domain": f"{host}{path}",
                "type": "self_hosted",
                "session_duration": "24h",
                "app_launcher_visible": False,
            },
        )
        app_result = app_response.get('result') or {}
        app_uuid = app_result.get('id') or app_result.get('uid')
        if not app_uuid:
            logging.warning(f"Cloudflare did not return an Access app id for {host}{path}")
            return None
        _create_webhook_bypass_policy(account_id, app_uuid)
        logging.info(
            f"Created Cloudflare Access webhook bypass app for {host}{path} "
            f"(inbound email worker can now reach mail-manager)"
        )
        return app_uuid
    except Exception as e:
        logging.warning(
            f"Could not create Access webhook bypass app for {host}{path}: {e}. "
            f"Ensure the API token has 'Access: Apps and Policies: Edit'."
        )
        return None


def delete_webhook_access_bypass(webmail_hostname):
    account_id = getattr(config, 'CF_ACCOUNT_ID', None)
    if not account_id or not webmail_hostname:
        return False

    host = _normalize_access_destination(webmail_hostname)
    path = WEBHOOK_ACCESS_PATH

    try:
        response = cf_api_request('GET', f'/accounts/{account_id}/access/apps', params={"per_page": 100})
        apps = response.get('result') or []
    except Exception as e:
        logging.warning(f"Could not list Access apps to remove webhook bypass for {host}: {e}")
        return False

    existing = _find_webhook_bypass_app(apps, host, path)
    if not existing:
        return False

    app_uuid = existing.get('id') or existing.get('uid')
    if not app_uuid:
        return False

    try:
        cf_api_request('DELETE', f'/accounts/{account_id}/access/apps/{app_uuid}')
        logging.info(f"Deleted Cloudflare Access webhook bypass app for {host}{path}")
        return True
    except Exception as e:
        logging.warning(f"Could not delete Access webhook bypass app {app_uuid}: {e}")
        return False

