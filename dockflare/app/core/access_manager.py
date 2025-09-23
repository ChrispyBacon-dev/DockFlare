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
# app/core/access_manager.py
import logging
import json
import hashlib
import requests
import time
from flask import current_app
from app.core import cloudflare_api
from app.core.state_manager import access_groups

_ACCOUNT_EMAIL_CACHE_TTL = 3600
_cached_account_email = None
_cached_account_email_timestamp = 0

def _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    payload = {
        "name": name,
        "domain": hostname,
        "type": "self_hosted",
        "session_duration": session_duration,
        "app_launcher_visible": app_launcher_visible,
        "self_hosted_domains": self_hosted_domains,
        "auto_redirect_to_identity": auto_redirect_to_identity,
    }
    if access_policies is not None:
        payload["policies"] = access_policies
    if allowed_idps is not None:
        payload["allowed_idps"] = allowed_idps

    return payload

def check_for_tld_access_policy(zone_name):
    if not zone_name:
        logging.warning("check_for_tld_access_policy called with no zone_name.")
        return False

    tld_hostname = f"*.{zone_name}"
    logging.info(f"Checking for existing Access Policy for wildcard TLD: {tld_hostname}")

    try:
        existing_app = find_cloudflare_access_application_by_hostname(tld_hostname)
        if existing_app and existing_app.get("id"):
            logging.info(f"Found existing Access Application ID '{existing_app.get('id')}' for TLD '{tld_hostname}'.")
            return True
        else:
            logging.info(f"No specific Access Application found for TLD '{tld_hostname}'.")
            return False
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

def find_cloudflare_access_application_by_hostname(hostname):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Finding Cloudflare Access Application for hostname '{hostname}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps"
    try:
        response_data_direct = cloudflare_api.cf_api_request("GET", endpoint, params={"domain": hostname})
        apps_direct = response_data_direct.get("result", [])
        if apps_direct and isinstance(apps_direct, list):
            for app in apps_direct:
                if app.get("domain") == hostname:
                    logging.info(f"Found Access Application ID '{app.get('id')}' for hostname '{hostname}' via direct domain query.")
                    return app

        logging.info(f"No exact match for '{hostname}' via domain query. Falling back to listing all Access Applications.")

        all_apps_response = cloudflare_api.cf_api_request("GET", endpoint, params={"per_page": 100})
        all_apps = all_apps_response.get("result", [])
        if all_apps and isinstance(all_apps, list):
            for app in all_apps:
                if app.get("domain") == hostname:
                    logging.info(f"Found Access Application ID '{app.get('id')}' for hostname '{hostname}' via full list scan (domain match).")
                    return app
                if hostname in app.get("self_hosted_domains", []):
                    logging.info(f"Found Access Application ID '{app.get('id')}' for hostname '{hostname}' (in self_hosted_domains) via full list scan.")
                    return app

        logging.info(f"Access Application for hostname '{hostname}' not found after extensive search.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error finding Cloudflare Access Application for '{hostname}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error finding Cloudflare Access Application for '{hostname}': {e}", exc_info=True)
        return None

def create_cloudflare_access_application(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Creating Cloudflare Access Application for hostname '{hostname}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps"
    payload = _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps, auto_redirect_to_identity)
    try:
        response_data = cloudflare_api.cf_api_request("POST", endpoint, json_data=payload)
        app_data = response_data.get("result")
        if app_data and app_data.get("id"):
            logging.info(f"Successfully created Access Application '{app_data.get('id')}' for '{hostname}'")
            return app_data
        else:
            logging.error(f"Access Application creation for '{hostname}' API call successful but no ID in response: {app_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating Access Application for '{hostname}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating Access Application for '{hostname}': {e}", exc_info=True)
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

def update_cloudflare_access_application(app_uuid, hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps=None, auto_redirect_to_identity=False):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Updating Cloudflare Access Application ID '{app_uuid}' for hostname '{hostname}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/apps/{app_uuid}"
    payload = _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, allowed_idps, auto_redirect_to_identity)
    try:
        response_data = cloudflare_api.cf_api_request("PUT", endpoint, json_data=payload)
        app_data = response_data.get("result")
        if app_data and app_data.get("id"):
            logging.info(f"Successfully updated Access Application '{app_data.get('id')}' for '{hostname}'")
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

def handle_access_policy_from_labels(hostname_config_item, current_rule_in_state, state_manager_save_func):
    hostname = hostname_config_item["hostname"]
    local_state_changed_by_access_policy = False
    
    current_access_app_id_from_state = current_rule_in_state.get("access_app_id")
    
    desired_access_group_ids = hostname_config_item.get("access_group")  # This is now a list
    
    desired_app_name = f"DockFlare-{hostname}"
    desired_session_duration = "24h"
    desired_app_launcher_visible = False
    desired_allowed_idps = None
    desired_auto_redirect = False
    cf_access_policies = []
    new_config_hash = None
    policy_source_type = None

    if desired_access_group_ids and isinstance(desired_access_group_ids, list):
        logging.info(f"Processing Access Groups {desired_access_group_ids} for {hostname}.")
        policy_source_type = "group"
        cf_access_policies = []
   
        first_group_id = desired_access_group_ids[0]
        first_group_def = access_groups.get(first_group_id)
        
        if first_group_def:
            desired_session_duration = first_group_def.get("session_duration", "24h")
            desired_app_launcher_visible = first_group_def.get("app_launcher_visible", False)
            desired_allowed_idps = first_group_def.get("allowed_idps")
            desired_auto_redirect = first_group_def.get("auto_redirect_to_identity", False)


        for group_id in desired_access_group_ids:
            group_definition = access_groups.get(group_id)
            if group_definition and group_definition.get("policies"):
                for policy in group_definition.get("policies"):
                    is_default_deny = (
                        policy.get("decision") == "deny" and
                        isinstance(policy.get("include"), list) and
                        len(policy.get("include")) == 1 and
                        policy.get("include")[0] == {"everyone": {}}
                    )
                    if not is_default_deny:
                        cf_access_policies.append(policy)
            else:
                logging.warning(f"Access Group '{group_id}' not found or has no policies.")

        has_allow_policy = any(p.get('decision') == 'allow' for p in cf_access_policies)
        if has_allow_policy:
            cf_access_policies.append({"name": "Default Deny", "decision": "deny", "include": [{"everyone": {}}]})

        new_config_hash = generate_access_app_config_hash(
            policy_type=policy_source_type, session_duration=desired_session_duration,
            app_launcher_visible=desired_app_launcher_visible,
            allowed_idps_str=json.dumps(desired_allowed_idps, sort_keys=True),
            auto_redirect_to_identity=desired_auto_redirect,
            custom_access_rules_str=json.dumps(cf_access_policies, sort_keys=True),
            group_id=desired_access_group_ids 
        )
    else:
        policy_source_type = hostname_config_item.get("access_policy_type")
        if not policy_source_type:

            if current_access_app_id_from_state:
                logging.info(f"No access policy label for {hostname}, but found managed Access App {current_access_app_id_from_state}. Deleting it.")
                if delete_cloudflare_access_application(current_access_app_id_from_state):
                    current_rule_in_state.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                    local_state_changed_by_access_policy = True
            elif current_rule_in_state.get("access_policy_type") or current_rule_in_state.get("access_group_id"):
                current_rule_in_state.update({"access_app_id": None, "access_policy_type": None, "access_app_config_hash": None, "access_group_id": None})
                local_state_changed_by_access_policy = True
            return local_state_changed_by_access_policy

        if policy_source_type == "default_tld":
            if current_access_app_id_from_state:
                logging.info(f"Label policy for {hostname} is 'default_tld'. Deleting existing Access App {current_access_app_id_from_state}.")
                if delete_cloudflare_access_application(current_access_app_id_from_state):
                    current_rule_in_state.update({"access_app_id": None, "access_policy_type": "default_tld", "access_app_config_hash": None, "access_group_id": None})
                    local_state_changed_by_access_policy = True
            elif current_rule_in_state.get("access_policy_type") != "default_tld" or current_rule_in_state.get("access_group_id"):
                current_rule_in_state.update({"access_policy_type": "default_tld", "access_group_id": None, "access_app_config_hash": None})
                local_state_changed_by_access_policy = True
            return local_state_changed_by_access_policy

        desired_app_name = hostname_config_item.get("access_app_name") or f"DockFlare-{hostname}"
        desired_session_duration = hostname_config_item.get("access_session_duration", "24h")
        desired_app_launcher_visible = hostname_config_item.get("access_app_launcher_visible", False)
        desired_allowed_idps_str = hostname_config_item.get("access_allowed_idps_str")
        desired_auto_redirect = hostname_config_item.get("access_auto_redirect", False)
        desired_custom_rules_str = hostname_config_item.get("access_custom_rules_str")
        desired_allowed_idps = [idp.strip() for idp in desired_allowed_idps_str.split(',')] if desired_allowed_idps_str else None

        if desired_custom_rules_str:
            try:
                cf_access_policies = json.loads(desired_custom_rules_str)
            except json.JSONDecodeError:
                logging.error(f"Error parsing 'custom_rules' JSON for {hostname}")
        
        if not cf_access_policies:
            if policy_source_type == "bypass":
                cf_access_policies = [{"name": "Label Default Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
            elif policy_source_type == "authenticate":
                include_rules = [{"everyone": {}}]
                if desired_allowed_idps_str:
                    include_rules = [{"login_method": {"id": idp.strip()}} for idp in desired_allowed_idps_str.split(',') if idp.strip()]
                cf_access_policies = [{"name": "Label Default Authenticated Access", "decision": "allow", "include": include_rules}]

        new_config_hash = generate_access_app_config_hash(
            policy_source_type, desired_session_duration, desired_app_launcher_visible,
            desired_allowed_idps_str, desired_auto_redirect, desired_custom_rules_str
        )

    needs_api_action = current_rule_in_state.get("access_app_config_hash") != new_config_hash

    if needs_api_action:
        effective_app_id = current_access_app_id_from_state
        if not effective_app_id:
            existing_cf_app = find_cloudflare_access_application_by_hostname(hostname)
            if existing_cf_app and existing_cf_app.get("id"):
                effective_app_id = existing_cf_app.get("id")
                logging.info(f"Found existing Access App ID '{effective_app_id}' on Cloudflare for {hostname}. Will update.")
                current_rule_in_state["access_app_id"] = effective_app_id
                local_state_changed_by_access_policy = True

        app_result = None
        if effective_app_id:
            logging.info(f"Updating Access App {effective_app_id} for {hostname}.")
            app_result = update_cloudflare_access_application(
                effective_app_id, hostname, desired_app_name, desired_session_duration,
                desired_app_launcher_visible, [hostname], cf_access_policies,
                desired_allowed_idps, desired_auto_redirect
            )
        else:
            logging.info(f"Creating new Access App for {hostname}.")
            app_result = create_cloudflare_access_application(
                hostname, desired_app_name, desired_session_duration,
                desired_app_launcher_visible, [hostname], cf_access_policies,
                desired_allowed_idps, desired_auto_redirect
            )

        if app_result and app_result.get("id"):
            current_rule_in_state.update({
                "access_app_id": app_result.get("id"),
                "access_app_config_hash": new_config_hash,
                "access_group_id": desired_access_group_ids,
                "access_policy_type": policy_source_type
            })
            local_state_changed_by_access_policy = True
        else:
            logging.error(f"Failed to create/update Access App for {hostname}.")

    return local_state_changed_by_access_policy