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
        return cf_api_request('POST', f'/zones/{zone_id}/email/routing/enable')
    except Exception as e:
        # 422/conflict means already enabled — safe to continue
        err_str = str(e)
        if '2004' in err_str or 'already enabled' in err_str.lower() or 'Unprocessable' in err_str:
            logging.info(f"Email routing already enabled on zone {zone_id}, continuing")
            return {}
        logging.error(f"Error enabling email routing: {e}")
        raise

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
        res = cf_api_request('GET', f'/zones/{zone_id}/email/routing/dns')
        required = res.get('result', [])
        for record in required:
            rtype = record.get('type')
            rname = record.get('name')
            rcontent = record.get('content')
            rpriority = record.get('priority')
            if rtype and rname and rcontent:
                _safe_create_dns(zone_id, rtype, rname, rcontent, priority=rpriority)
    except Exception as e:
        logging.warning(f"Could not fetch required email routing DNS records from CF API: {e}, falling back to defaults")
        _safe_create_dns(zone_id, 'MX', zone_name, 'route1.mx.cloudflare.net', priority=14)
        _safe_create_dns(zone_id, 'MX', zone_name, 'route2.mx.cloudflare.net', priority=36)
        _safe_create_dns(zone_id, 'MX', zone_name, 'route3.mx.cloudflare.net', priority=88)
        _safe_create_dns(zone_id, 'TXT', zone_name, 'v=spf1 include:_spf.mx.cloudflare.net ~all')
        _safe_create_dns(zone_id, 'TXT', f'_dmarc.{zone_name}', f'v=DMARC1; p=quarantine; rua=mailto:dmarc@{zone_name}')

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
    token_verify = cf_api_request('GET', f'/accounts/{config.CF_ACCOUNT_ID}/tokens/verify')
    token_id = token_verify.get('result', {}).get('id', '')
    return {
        'access_key_id': token_id,
        'secret_access_key': config.CF_API_TOKEN,
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

def create_email_routing_rule(zone_id, address, worker_name):
    data = {
        "matchers": [{"type": "literal", "field": "to", "value": address}],
        "actions": [{"type": "worker", "value": [worker_name]}],
        "enabled": True,
        "name": f"DockFlare: {address}"
    }
    return cf_api_request('POST', f'/zones/{zone_id}/email/routing/rules', json_data=data)

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
