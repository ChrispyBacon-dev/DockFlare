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
# dockflare/app/core/access_manager.py
import logging
import json
import hashlib
import requests
import time
import copy
from flask import current_app
from app.core import cloudflare_api
from app.core.state_manager import access_groups, managed_rules, state_lock
from app.core.utils import normalize_path_value

_ACCOUNT_EMAIL_CACHE_TTL = 3600
_cached_account_email = None
_cached_account_email_timestamp = 0

def _build_access_app_payload(application_domain, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies_or_ids, allowed_idps=None, auto_redirect_to_identity=False, use_reusable=False):
    from app import config

    payload = {
        "name": name,
        "domain": application_domain,
        "type": "self_hosted",
        "session_duration": session_duration,
        "app_launcher_visible": app_launcher_visible,
        "self_hosted_domains": self_hosted_domains,
        "auto_redirect_to_identity": auto_redirect_to_identity,
    }

    if access_policies_or_ids is not None:
        payload["policies"] = access_policies_or_ids

    if allowed_idps is not None:
        payload["allowed_idps"] = allowed_idps

    return payload

def check_for_tld_access_policy(zone_name):
    if not zone_name:
        logging.warning("check_for_tld_access_policy called with no zone_name.")
        return False

    tld_hostname = f"*.{zone_name}"
    
    from app.core.cache import get_redis_client
    import json
    redis_client = get_redis_client()
    cache_key = f"tld_policy_check:{zone_name}"
    cache_ttl = 300  # 5 minutes

    if redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result is not None:
                result = json.loads(cached_result)
                logging.debug(f"Returning cached TLD policy check for {tld_hostname}: {result}")
                return result
        except Exception as e:
            logging.warning(f"Failed to read TLD policy cache: {e}")

    logging.info(f"Checking for existing Access Policy for wildcard TLD: {tld_hostname}")

    try:
        
        account_id = current_app.config.get('CF_ACCOUNT_ID')
        endpoint = f"/accounts/{account_id}/access/apps"
        from app.core import cloudflare_api

        response_data = cloudflare_api.cf_api_request("GET", endpoint, params={"domain": tld_hostname})
        apps = response_data.get("result", [])

        existing_app = None
        if apps and isinstance(apps, list):
            for app in apps:
                if app.get("domain") == tld_hostname:
                    existing_app = app
                    break

        if existing_app and existing_app.get("id"):
            logging.info(f"Found existing Access Application ID '{existing_app.get('id')}' for TLD '{tld_hostname}'.")
            result = True
        else:
            logging.info(f"No specific Access Application found for TLD '{tld_hostname}'.")
            result = False
        
        if redis_client:
            try:
                redis_client.setex(cache_key, cache_ttl, json.dumps(result))
                logging.debug(f"Cached TLD policy check for {tld_hostname}")
            except Exception as e:
                logging.warning(f"Failed to cache TLD policy check: {e}")

        return result
    except Exception as e:
        logging.error(f"Error while checking for TLD access policy for '{tld_hostname}': {e}", exc_info=True)
        return False

def get_cloudflare_account_email():
    global _cached_account_email, _cached_account_email_timestamp

    current_time = time.time()
    if _cached_account_email and (current_time - _cached_account_email_timestamp < _ACCOUNT_EMAIL_CACHE_TTL):
        logging.debug(f"Returning cached Cloudflare account email: {_cached_account_email}")
        return _cached_account_email

    logging.info("Fetching Cloudflare account email from API.")
    try:
        response_data = cloudflare_api.cf_api_request("GET", "/user")
        if response_data and response_data.get("success"):
            email = response_data.get("result", {}).get("email")
            if email:
                logging.info(f"Successfully fetched Cloudflare account email: {email}")
                _cached_account_email = email
                _cached_account_email_timestamp = current_time
                return email
            else:
                logging.warning("Cloudflare account email not found in API response.")
                return None
        else:
            logging.warning(f"Failed to fetch Cloudflare account email, API call unsuccessful. Response: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error fetching Cloudflare account email: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error fetching Cloudflare account email: {e}", exc_info=True)
        return None

def find_cloudflare_access_application_by_domain(application_domain):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Finding Cloudflare Access Application for domain '{application_domain}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps"
    try:
        response_data_direct = cloudflare_api.cf_api_request("GET", endpoint, params={"domain": application_domain})
        apps_direct = response_data_direct.get("result", [])
        if apps_direct and isinstance(apps_direct, list):
            for app in apps_direct:
                if app.get("domain") == application_domain:
                    logging.info(f"Found Access Application ID '{app.get('id')}' for domain '{application_domain}' via direct domain query.")
                    return app

        logging.info(f"No exact match for '{application_domain}' via domain query. Falling back to listing all Access Applications.")

        all_apps_response = cloudflare_api.cf_api_request("GET", endpoint, params={"per_page": 100})
        all_apps = all_apps_response.get("result", [])
        if all_apps and isinstance(all_apps, list):
            for app in all_apps:
                if app.get("domain") == application_domain:
                    logging.info(f"Found Access Application ID '{app.get('id')}' for domain '{application_domain}' via full list scan (domain match).")
                    return app
                if application_domain in app.get("self_hosted_domains", []):
                    logging.info(f"Found Access Application ID '{app.get('id')}' for domain '{application_domain}' (in self_hosted_domains) via full list scan.")
                    return app

        logging.info(f"Access Application for domain '{application_domain}' not found after extensive search.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding Cloudflare Access Application for '{application_domain}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error finding Cloudflare Access Application for '{application_domain}': {e}", exc_info=True)
        return None

def create_cloudflare_access_application(application_domain, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False, use_reusable=False):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Creating Cloudflare Access Application for domain '{application_domain}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps"

    payload = _build_access_app_payload(application_domain, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps, auto_redirect_to_identity, use_reusable)

    logging.info(f"Access Application payload for '{application_domain}': use_reusable={use_reusable}, has_policies={'policies' in payload}")
    if 'policies' in payload:
        if use_reusable:
            logging.info(f"Reusable policy IDs: {payload['policies']}")
        else:
            logging.info(f"Inline policies count: {len(payload['policies']) if payload['policies'] else 0}")
    try:
        response_data = cloudflare_api.cf_api_request("POST", endpoint, json_data=payload)
        app_data = response_data.get("result")
        if app_data and app_data.get("id"):
            app_id = app_data.get('id')
            logging.info(f"Successfully created Access Application '{app_id}' for '{application_domain}'")
            return app_data
        else:
            logging.error(f"Access Application creation for '{application_domain}' API call successful but no ID in response: {app_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating Access Application for '{application_domain}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating Access Application for '{application_domain}': {e}", exc_info=True)
        return None

def get_cloudflare_access_application(app_uuid):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Getting Cloudflare Access Application details for ID '{app_uuid}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps/{app_uuid}"
    try:
        response_data = cloudflare_api.cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            app_data = response_data.get("result")
            if app_data:
                logging.info(f"Successfully retrieved Access Application details for ID '{app_uuid}'")
                return app_data
            elif response_data.get("success"):
                logging.warning(f"Successfully called API for Access App ID '{app_uuid}', but no result data found. Response: {response_data}")
                return None
            else:
                logging.error(f"API call failed or returned success=false for Access App ID '{app_uuid}'. Response: {response_data}")
                return None
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            logging.warning(f"Cloudflare Access Application with ID '{app_uuid}' not found (404).")
        else:
            logging.error(f"API error getting Access Application '{app_uuid}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting Access Application '{app_uuid}': {e}", exc_info=True)
        return None

def update_cloudflare_access_application(app_uuid, application_domain, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False, use_reusable=False):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Updating Cloudflare Access Application ID '{app_uuid}' for domain '{application_domain}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps/{app_uuid}"

    payload = _build_access_app_payload(application_domain, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps, auto_redirect_to_identity, use_reusable)

    logging.info(f"Access Application update payload for '{application_domain}': use_reusable={use_reusable}, has_policies={'policies' in payload}")
    if 'policies' in payload:
        if use_reusable:
            logging.info(f"Reusable policy IDs for update: {payload['policies']}")
        else:
            logging.info(f"Inline policies count for update: {len(payload['policies']) if payload['policies'] else 0}")

    try:
        response_data = cloudflare_api.cf_api_request("PUT", endpoint, json_data=payload)
        app_data = response_data.get("result")
        if app_data and app_data.get("id"):
            logging.info(f"Successfully updated Access Application '{app_data.get('id')}' for '{application_domain}'")
            return app_data
        else:
            logging.error(f"Access Application update for '{app_uuid}' API call successful but no ID in response: {app_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error updating Access Application '{app_uuid}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error updating Access Application '{app_uuid}': {e}", exc_info=True)
        return None

def delete_cloudflare_access_application(app_uuid):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Deleting Cloudflare Access Application ID '{app_uuid}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps/{app_uuid}"
    try:
        response_data = cloudflare_api.cf_api_request("DELETE", endpoint)
        if response_data and response_data.get("success"):
            deleted_id = response_data.get("result", {}).get("id") if isinstance(response_data.get("result"), dict) else app_uuid
            logging.info(f"Successfully submitted deletion for Access Application ID '{deleted_id if deleted_id else app_uuid}'")
            return True

        elif response_data and response_data.get("success") and not response_data.get("result"):
            logging.info(f"Access Application ID '{app_uuid}' deletion API call succeeded (success:true, no specific result ID).")
            return True

        elif response_data is None and "success" not in str(response_data): 
            logging.info(f"Access Application ID '{app_uuid}' deletion API call likely succeeded (no content/error).")
            return True

        logging.warning(f"Access Application deletion for '{app_uuid}' API call did not confirm success clearly. Response: {response_data}")
        return False
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            logging.warning(f"Cloudflare Access Application with ID '{app_uuid}' not found during delete attempt (404). Treating as success.")
            return True
        logging.error(f"API error deleting Access Application '{app_uuid}': {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error deleting Access Application '{app_uuid}': {e}", exc_info=True)
        return False

def generate_access_app_config_hash(policy_type, session_duration, app_launcher_visible, allowed_idps_str, auto_redirect_to_identity, custom_access_rules_str=None, group_id=None):
    
    if isinstance(group_id, list):
        group_id.sort()

    config_items = {
        "group_id": group_id,
        "policy_type": policy_type,
        "session_duration": str(session_duration), 
        "app_launcher_visible": bool(app_launcher_visible),
        "allowed_idps_str": str(allowed_idps_str) if allowed_idps_str is not None else None,
        "auto_redirect_to_identity": bool(auto_redirect_to_identity),
        "custom_access_rules_str": str(custom_access_rules_str) if custom_access_rules_str is not None else None
    }
    consistent_config_string = json.dumps(config_items, sort_keys=True)
    hasher = hashlib.sha256()
    hasher.update(consistent_config_string.encode('utf-8'))
    return hasher.hexdigest()

def handle_access_policy_from_labels(rule_key, hostname_config_item):
    from app import config
    from app.core import reusable_policies

    with state_lock:
        rule_reference = managed_rules.get(rule_key)
        if not rule_reference:
            return False
        if rule_reference.get("access_policy_ui_override", False):
            return False
        rule_working = copy.deepcopy(rule_reference)

    hostname = hostname_config_item["hostname"]
    normalized_path = normalize_path_value(hostname_config_item.get("path"))
    is_path_rule = bool(normalized_path)
    application_domain = hostname if not is_path_rule else f"{hostname}{normalized_path}"

    path_identifier = ""
    if is_path_rule:
        path_identifier = normalized_path.lstrip('/') or "root"
        path_identifier = path_identifier.replace('/', '-').replace(' ', '-')
    local_state_changed_by_access_policy = False

    current_access_app_id_from_state = rule_working.get("access_app_id")

    desired_access_group_ids = hostname_config_item.get("access_group")

    desired_app_name = f"DockFlare-{hostname}"
    if path_identifier:
        desired_app_name = f"{desired_app_name}-{path_identifier}"
    desired_session_duration = "24h"
    desired_app_launcher_visible = False
    desired_allowed_idps = None
    desired_auto_redirect = False
    cf_access_policies_or_ids = []
    new_config_hash = None
    policy_source_type = None
    use_reusable = False

    if desired_access_group_ids and isinstance(desired_access_group_ids, list):
        logging.info(f"Processing Access Groups {desired_access_group_ids} for {application_domain}.")
        policy_source_type = "group"

        first_group_id = desired_access_group_ids[0]
        first_group_def = None
        with state_lock:
            group_entry = access_groups.get(first_group_id)
            if group_entry:
                first_group_def = copy.deepcopy(group_entry)

        if first_group_def:
            desired_session_duration = first_group_def.get("session_duration", "24h")
            desired_app_launcher_visible = first_group_def.get("app_launcher_visible", False)
            desired_allowed_idps = first_group_def.get("allowed_idps")
            desired_auto_redirect = first_group_def.get("auto_redirect_to_identity", False)

        if config.USE_REUSABLE_POLICIES:
            use_reusable = True
            policy_ids = []
            for group_id in desired_access_group_ids:
                policy_id = reusable_policies.sync_access_group_to_reusable_policy(group_id)
                if policy_id:
                    policy_ids.append(policy_id)
                else:
                    logging.warning(f"Failed to sync access group '{group_id}' to reusable policy for {application_domain}")
            cf_access_policies_or_ids = policy_ids
        else:
            aggregated_policies = []
            for group_id in desired_access_group_ids:
                with state_lock:
                    group_definition = access_groups.get(group_id)
                    group_copy = copy.deepcopy(group_definition) if group_definition else None
                if group_copy and group_copy.get("policies"):
                    for policy in group_copy.get("policies"):
                        is_default_deny = (
                            policy.get("decision") == "deny" and
                            isinstance(policy.get("include"), list) and
                            len(policy.get("include")) == 1 and
                            policy.get("include")[0] == {"everyone": {}}
                        )
                        if not is_default_deny:
                            aggregated_policies.append(policy)
                else:
                    logging.warning(f"Access Group '{group_id}' not found or has no policies.")

            cf_access_policies_or_ids = aggregated_policies
            has_allow_policy = any(p.get('decision') == 'allow' for p in cf_access_policies_or_ids)
            if has_allow_policy:
                cf_access_policies_or_ids.append({"name": "Default Deny", "decision": "deny", "include": [{"everyone": {}}]})

        if not cf_access_policies_or_ids:
            logging.warning(f"Skipping access app creation for {application_domain}; no policies resolved for groups {desired_access_group_ids}")
            if current_access_app_id_from_state:
                if delete_cloudflare_access_application(current_access_app_id_from_state):
                    rule_working.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                    local_state_changed_by_access_policy = True
            elif rule_working.get("access_policy_type") or rule_working.get("access_group_id"):
                rule_working.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                local_state_changed_by_access_policy = True
            if local_state_changed_by_access_policy:
                with state_lock:
                    current_rule = managed_rules.get(rule_key)
                    if current_rule:
                        current_rule.update({"access_app_id": rule_working.get("access_app_id"), "access_policy_type": rule_working.get("access_policy_type"), "access_app_config_hash": rule_working.get("access_app_config_hash"), "access_group_id": rule_working.get("access_group_id")})
            return local_state_changed_by_access_policy

        new_config_hash = generate_access_app_config_hash(
            policy_type=policy_source_type, session_duration=desired_session_duration,
            app_launcher_visible=desired_app_launcher_visible,
            allowed_idps_str=json.dumps(desired_allowed_idps, sort_keys=True),
            auto_redirect_to_identity=desired_auto_redirect,
            custom_access_rules_str=json.dumps(cf_access_policies_or_ids, sort_keys=True),
            group_id=desired_access_group_ids
        )
    else:
        policy_source_type = hostname_config_item.get("access_policy_type")
        if not policy_source_type:
            if current_access_app_id_from_state:
                logging.info(f"No access policy label for {application_domain}, but found managed Access App {current_access_app_id_from_state}. Deleting it.")
                if delete_cloudflare_access_application(current_access_app_id_from_state):
                    rule_working.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                    local_state_changed_by_access_policy = True
            elif rule_working.get("access_policy_type") or rule_working.get("access_group_id"):
                rule_working.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                local_state_changed_by_access_policy = True
            if local_state_changed_by_access_policy:
                with state_lock:
                    current_rule = managed_rules.get(rule_key)
                    if current_rule:
                        current_rule.update({"access_app_id": rule_working.get("access_app_id"), "access_policy_type": rule_working.get("access_policy_type"), "access_app_config_hash": rule_working.get("access_app_config_hash"), "access_group_id": rule_working.get("access_group_id")})
                return local_state_changed_by_access_policy
            return False

        if policy_source_type == "default_tld":
            if current_access_app_id_from_state:
                logging.info(f"Label policy for {hostname} is 'default_tld'. Deleting existing Access App {current_access_app_id_from_state}.")
                if delete_cloudflare_access_application(current_access_app_id_from_state):
                    rule_working.update({"access_app_id": None, "access_policy_type": "default_tld", "access_app_config_hash": None, "access_group_id": None})
                    local_state_changed_by_access_policy = True
            elif rule_working.get("access_policy_type") != "default_tld" or rule_working.get("access_group_id"):
                rule_working.update({"access_policy_type": "default_tld", "access_group_id": None, "access_app_config_hash": None})
                local_state_changed_by_access_policy = True
            if local_state_changed_by_access_policy:
                with state_lock:
                    current_rule = managed_rules.get(rule_key)
                    if current_rule:
                        current_rule.update({"access_app_id": rule_working.get("access_app_id"), "access_policy_type": rule_working.get("access_policy_type"), "access_app_config_hash": rule_working.get("access_app_config_hash"), "access_group_id": rule_working.get("access_group_id")})
                return True
            return False

        desired_app_name = hostname_config_item.get("access_app_name") or f"DockFlare-{hostname}"
        desired_session_duration = hostname_config_item.get("access_session_duration", "24h")
        desired_app_launcher_visible = hostname_config_item.get("access_app_launcher_visible", False)
        desired_allowed_idps_str = hostname_config_item.get("access_allowed_idps_str")
        desired_auto_redirect = hostname_config_item.get("access_auto_redirect", False)
        desired_custom_rules_str = hostname_config_item.get("access_custom_rules_str")
        desired_allowed_idps = [idp.strip() for idp in desired_allowed_idps_str.split(',')] if desired_allowed_idps_str else None

        if desired_custom_rules_str:
            try:
                cf_access_policies_or_ids = json.loads(desired_custom_rules_str)
            except json.JSONDecodeError:
                logging.error(f"Error parsing 'custom_rules' JSON for {application_domain}")

        if not cf_access_policies_or_ids:
            if policy_source_type == "bypass":
                logging.warning(f"ACCESS_MANAGER: Unexpected 'bypass' policy type reached access_manager for {application_domain}. This should have been migrated to access.group=bypass. Skipping access policy creation.")
                if current_access_app_id_from_state:
                    logging.info(f"Deleting existing Access App {current_access_app_id_from_state} for {application_domain} since bypass should not have an access app.")
                    if delete_cloudflare_access_application(current_access_app_id_from_state):
                        rule_working.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                        local_state_changed_by_access_policy = True
                if local_state_changed_by_access_policy:
                    with state_lock:
                        current_rule = managed_rules.get(rule_key)
                        if current_rule:
                            current_rule.update({"access_app_id": rule_working.get("access_app_id"), "access_policy_type": rule_working.get("access_policy_type"), "access_app_config_hash": rule_working.get("access_app_config_hash"), "access_group_id": rule_working.get("access_group_id")})
                return local_state_changed_by_access_policy
            elif policy_source_type == "authenticate":
                logging.warning(f"ACCESS_MANAGER: Unexpected 'authenticate' policy type reached access_manager for {application_domain}. This should have been migrated to access.group=authenticated-default. Skipping access policy creation.")
                if current_access_app_id_from_state:
                    logging.info(f"Deleting existing Access App {current_access_app_id_from_state} for {application_domain} since it should use authenticated-default group.")
                    if delete_cloudflare_access_application(current_access_app_id_from_state):
                        rule_working.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                        local_state_changed_by_access_policy = True
                if local_state_changed_by_access_policy:
                    with state_lock:
                        current_rule = managed_rules.get(rule_key)
                        if current_rule:
                            current_rule.update({"access_app_id": rule_working.get("access_app_id"), "access_policy_type": rule_working.get("access_policy_type"), "access_app_config_hash": rule_working.get("access_app_config_hash"), "access_group_id": rule_working.get("access_group_id")})
                return local_state_changed_by_access_policy

        new_config_hash = generate_access_app_config_hash(
            policy_source_type, desired_session_duration, desired_app_launcher_visible,
            desired_allowed_idps_str, desired_auto_redirect, desired_custom_rules_str
        )

    needs_api_action = rule_working.get("access_app_config_hash") != new_config_hash

    if needs_api_action:
        effective_app_id = rule_working.get("access_app_id")
        if not effective_app_id:
            existing_cf_app = find_cloudflare_access_application_by_domain(application_domain)
            if existing_cf_app and existing_cf_app.get("id"):
                effective_app_id = existing_cf_app.get("id")
                logging.info(f"Found existing Access App ID '{effective_app_id}' on Cloudflare for {application_domain}. Will update.")
                rule_working["access_app_id"] = effective_app_id
                local_state_changed_by_access_policy = True

        app_result = None
        app_update_failed = False
        if effective_app_id:
            logging.info(f"Updating Access App {effective_app_id} for {application_domain}.")
            try:
                app_result = update_cloudflare_access_application(
                    effective_app_id, application_domain, desired_app_name, desired_session_duration,
                    desired_app_launcher_visible, [application_domain], cf_access_policies_or_ids,
                    desired_allowed_idps, desired_auto_redirect, use_reusable
                )
            except Exception as update_error:
                error_text = str(update_error)
                if "access.api.error.unknown_application" in error_text or "404" in error_text:
                    logging.info(f"Existing Access App {effective_app_id} not found in Cloudflare (404); will recreate for {application_domain}.")
                    app_update_failed = True
                else:
                    logging.error(f"Error updating access app during reconciliation: {update_error}", exc_info=True)
                    raise

        if not effective_app_id or app_update_failed or not app_result:
            logging.info(f"Creating new Access App for {application_domain}.")
            app_result = create_cloudflare_access_application(
                application_domain, desired_app_name, desired_session_duration,
                desired_app_launcher_visible, [application_domain], cf_access_policies_or_ids,
                desired_allowed_idps, desired_auto_redirect, use_reusable
            )

        if app_result and app_result.get("id"):
            rule_working.update({
                "access_app_id": app_result.get("id"),
                "access_app_config_hash": new_config_hash,
                "access_group_id": desired_access_group_ids,
                "access_policy_type": policy_source_type
            })
            local_state_changed_by_access_policy = True
        else:
            logging.error(f"Failed to create/update Access App for {hostname}.")

    if local_state_changed_by_access_policy:
        updated_fields = {
            "access_app_id": rule_working.get("access_app_id"),
            "access_policy_type": rule_working.get("access_policy_type"),
            "access_app_config_hash": rule_working.get("access_app_config_hash"),
            "access_group_id": rule_working.get("access_group_id")
        }
        with state_lock:
            current_rule = managed_rules.get(rule_key)
            if not current_rule:
                return False
            current_rule.update(updated_fields)
        return True

    return False
