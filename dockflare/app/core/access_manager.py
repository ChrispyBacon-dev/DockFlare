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
import copy
import logging
import json
import hashlib
import requests 
import time
from app import config
from app.core import cloudflare_api

_ACCOUNT_EMAIL_CACHE_TTL = 3600 
_cached_account_email = None
_cached_account_email_timestamp = 0

def _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, auto_redirect_to_identity=False):
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
    logging.info(f"Finding Cloudflare Access Application for hostname '{hostname}' on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/access/apps"
    try:
        response_data_direct = cloudflare_api.cf_api_request("GET", endpoint, params={"domain": hostname})
        apps_direct = response_data_direct.get("result", [])
        if apps_direct and isinstance(apps_direct, list):
            for app in apps_direct:
                if app.get("domain") == hostname: # Exact domain match
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

def create_cloudflare_access_application(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, auto_redirect_to_identity=False):
    logging.info(f"Creating Cloudflare Access Application for hostname '{hostname}' on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/access/apps"
    payload = _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, auto_redirect_to_identity)
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
    logging.info(f"Getting Cloudflare Access Application details for ID '{app_uuid}' on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/access/apps/{app_uuid}"
    try:
        response_data = cloudflare_api.cf_api_request("GET", endpoint)
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

def update_cloudflare_access_application(app_uuid, hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, auto_redirect_to_identity=False):
    logging.info(f"Updating Cloudflare Access Application ID '{app_uuid}' for hostname '{hostname}' on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/access/apps/{app_uuid}"
    payload = _build_access_app_payload(hostname, name, session_duration, app_launcher_visible, self_hosted_domains, access_policies, auto_redirect_to_identity)
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
    logging.info(f"Deleting Cloudflare Access Application ID '{app_uuid}' on account {config.CF_ACCOUNT_ID}")
    endpoint = f"/accounts/{config.CF_ACCOUNT_ID}/access/apps/{app_uuid}"
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

def generate_access_app_config_hash(policy_type, session_duration, app_launcher_visible, allowed_idps_str, auto_redirect_to_identity, custom_access_rules_str=None):
    config_items = {
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
    
    desired_access_policy_type_from_label = hostname_config_item.get("access_policy_type")
    desired_access_app_name_from_label = hostname_config_item.get("access_app_name") or f"DockFlare-{hostname}"
    desired_session_duration_from_label = hostname_config_item.get("access_session_duration", "24h")
    desired_app_launcher_visible_from_label = hostname_config_item.get("access_app_launcher_visible", False)
    desired_allowed_idps_str_from_label = hostname_config_item.get("access_allowed_idps_str")
    desired_auto_redirect_from_label = hostname_config_item.get("access_auto_redirect", False)
    desired_custom_rules_str_from_label = hostname_config_item.get("access_custom_rules_str")

    local_state_changed_by_access_policy = False
    current_access_app_id_from_state = current_rule_in_state.get("access_app_id") 
    current_access_policy_type_in_state = current_rule_in_state.get("access_policy_type")
    current_access_app_config_hash_in_state = current_rule_in_state.get("access_app_config_hash")

    if desired_access_policy_type_from_label: 
        desired_access_app_config_hash_from_label = generate_access_app_config_hash(
            desired_access_policy_type_from_label,
            desired_session_duration_from_label,
            desired_app_launcher_visible_from_label,
            desired_allowed_idps_str_from_label,
            desired_auto_redirect_from_label,
            desired_custom_rules_str_from_label
        )

        if desired_access_policy_type_from_label == "default_tld":
            if current_access_app_id_from_state: 
                logging.info(f"Label policy for {hostname} is 'default_tld'. Deleting existing Access App {current_access_app_id_from_state}.")
                if delete_cloudflare_access_application(current_access_app_id_from_state):
                    current_rule_in_state["access_app_id"] = None
                    current_rule_in_state["access_policy_type"] = "default_tld"
                    current_rule_in_state["access_app_config_hash"] = None
                    local_state_changed_by_access_policy = True
                else:
                    logging.error(f"Failed to delete Access App {current_access_app_id_from_state} for {hostname} as per label 'default_tld'.")
            elif current_access_policy_type_in_state != "default_tld": 
                current_rule_in_state["access_app_id"] = None 
                current_rule_in_state["access_policy_type"] = "default_tld"
                current_rule_in_state["access_app_config_hash"] = None
                local_state_changed_by_access_policy = True
                logging.info(f"Label policy for {hostname} set to 'default_tld'. No specific app managed or was previously managed.")


        elif desired_access_policy_type_from_label in ["bypass", "authenticate"]:
            cf_access_policies = []
            if desired_custom_rules_str_from_label:
                try:
                    parsed_rules = json.loads(desired_custom_rules_str_from_label)
                    if isinstance(parsed_rules, list): cf_access_policies = parsed_rules
                    else: logging.error(f"Parsed 'custom_rules' label for {hostname} is not a list...")
                except json.JSONDecodeError as json_err: logging.error(f"Error parsing 'custom_rules' JSON for {hostname}: {json_err}...")
            
            if not cf_access_policies: 
                if desired_access_policy_type_from_label == "bypass": cf_access_policies = [{"name": "Label Default Bypass", "decision": "bypass", "include": [{"everyone": {}}]}]
                elif desired_access_policy_type_from_label == "authenticate":
                    policy_include_rules = []
                    if desired_allowed_idps_str_from_label:
                        idp_ids = [idp.strip() for idp in desired_allowed_idps_str_from_label.split(',') if idp.strip()]
                        for an_idp_id in idp_ids:
                            policy_include_rules.append({"login_method": {"id": an_idp_id}})
                    if not policy_include_rules: policy_include_rules.append({"everyone": {}}) 
                    cf_access_policies = [{"name": "Label Default Authenticated Access", "decision": "allow", "include": policy_include_rules}]

            needs_api_action = False
            
            if current_access_app_id_from_state: 
                if current_access_policy_type_in_state != desired_access_policy_type_from_label or \
                   current_access_app_config_hash_in_state != desired_access_app_config_hash_from_label:
                    needs_api_action = True
                    logging.info(f"Access App {current_access_app_id_from_state} for {hostname} (from local state) needs update/re-evaluation.")
            else: 
                needs_api_action = True
                logging.info(f"No Access App ID for {hostname} in local state. API action required (find or create).")

            if needs_api_action:
                effective_app_id_for_operation = current_access_app_id_from_state 
                
                if not effective_app_id_for_operation: 
                    logging.info(f"No local Access App ID for {hostname}. Checking Cloudflare API...")
                    existing_cf_app = find_cloudflare_access_application_by_hostname(hostname)
                    if existing_cf_app and existing_cf_app.get("id"):
                        effective_app_id_for_operation = existing_cf_app.get("id")
                        logging.info(f"Found existing Access App ID '{effective_app_id_for_operation}' on Cloudflare for {hostname}. Will attempt update.")
                        
                        current_rule_in_state["access_app_id"] = effective_app_id_for_operation
                                                
                        local_state_changed_by_access_policy = True 
                
                if effective_app_id_for_operation: 
                    logging.info(f"Updating Access App {effective_app_id_for_operation} for {hostname} based on labels (type: {desired_access_policy_type_from_label}).")
                    updated_app = update_cloudflare_access_application(
                        effective_app_id_for_operation, hostname, desired_access_app_name_from_label,
                        desired_session_duration_from_label, desired_app_launcher_visible_from_label,
                        [hostname], cf_access_policies, desired_auto_redirect_from_label
                    )
                    if updated_app:
                        current_rule_in_state["access_app_id"] = updated_app.get("id") 
                        current_rule_in_state["access_policy_type"] = desired_access_policy_type_from_label
                        current_rule_in_state["access_app_config_hash"] = desired_access_app_config_hash_from_label
                        local_state_changed_by_access_policy = True
                    else:
                        logging.error(f"Failed to update Access App {effective_app_id_for_operation} for {hostname} based on labels.")
                
                else: 
                    logging.info(f"Creating new Access App for {hostname} based on labels (type: '{desired_access_policy_type_from_label}').")
                    created_app = create_cloudflare_access_application(
                        hostname, desired_access_app_name_from_label,
                        desired_session_duration_from_label, desired_app_launcher_visible_from_label,
                        [hostname], cf_access_policies, desired_auto_redirect_from_label
                    )
                    if created_app and created_app.get("id"):
                        current_rule_in_state["access_app_id"] = created_app.get("id")
                        current_rule_in_state["access_policy_type"] = desired_access_policy_type_from_label
                        current_rule_in_state["access_app_config_hash"] = desired_access_app_config_hash_from_label
                        local_state_changed_by_access_policy = True
                    else:
                        logging.error(f"Failed to create Access App for {hostname} based on labels.")
        else: 
            logging.warning(f"Unknown access.policy type '{desired_access_policy_type_from_label}' from label for {hostname}. No Access App action taken.")
    
    else: 
        if current_access_app_id_from_state: 
            logging.info(f"No access policy label for {hostname}, but found managed Access App {current_access_app_id_from_state}. Deleting it.")
            if delete_cloudflare_access_application(current_access_app_id_from_state):
                current_rule_in_state["access_app_id"] = None
                current_rule_in_state["access_policy_type"] = None
                current_rule_in_state["access_app_config_hash"] = None
                local_state_changed_by_access_policy = True
            else:
                logging.error(f"Failed to delete Access App {current_access_app_id_from_state} for {hostname} during label cleanup.")
        elif current_rule_in_state.get("access_policy_type") is not None : 
            current_rule_in_state["access_app_id"] = None 
            current_rule_in_state["access_policy_type"] = None
            current_rule_in_state["access_app_config_hash"] = None
            local_state_changed_by_access_policy = True
            logging.debug(f"Ensuring access policy type is None for {hostname} as no access labels are present.")
            
    if local_state_changed_by_access_policy and state_manager_save_func:
        logging.debug(f"Access policy changes for {hostname} indicate state should be saved by caller.")

    return local_state_changed_by_access_policy