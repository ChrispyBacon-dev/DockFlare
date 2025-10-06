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
# dockflare/app/core/reusable_policies.py
import logging
import requests
import copy
from flask import current_app
from app.core import cloudflare_api

def create_reusable_policy(name, decision, include_rules, exclude_rules=None, require_rules=None, purpose_justification_required=False, purpose_justification_prompt=None):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Creating reusable Access Policy '{name}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/policies"

    payload = {
        "name": name,
        "decision": decision,
        "include": include_rules,
    }

    if exclude_rules:
        payload["exclude"] = exclude_rules
    if require_rules:
        payload["require"] = require_rules
    if purpose_justification_required:
        payload["purpose_justification_required"] = purpose_justification_required
    if purpose_justification_prompt:
        payload["purpose_justification_prompt"] = purpose_justification_prompt

    try:
        response_data = cloudflare_api.cf_api_request("POST", endpoint, json_data=payload)
        policy_data = response_data.get("result")
        if policy_data and policy_data.get("id"):
            logging.info(f"Successfully created reusable policy '{name}' with ID '{policy_data.get('id')}'")
            return policy_data
        else:
            logging.error(f"Reusable policy creation for '{name}' API call successful but no ID in response: {policy_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error creating reusable policy '{name}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating reusable policy '{name}': {e}", exc_info=True)
        return None

def get_reusable_policy(policy_id):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Getting reusable Access Policy ID '{policy_id}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/policies/{policy_id}"

    try:
        response_data = cloudflare_api.cf_api_request("GET", endpoint)
        if response_data and response_data.get("success"):
            policy_data = response_data.get("result")
            if policy_data:
                logging.info(f"Successfully retrieved reusable policy ID '{policy_id}'")
                return policy_data
            else:
                logging.warning(f"Successfully called API for reusable policy ID '{policy_id}', but no result data found. Response: {response_data}")
                return None
        else:
            logging.error(f"API call failed for reusable policy ID '{policy_id}'. Response: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            logging.warning(f"Reusable policy with ID '{policy_id}' not found (404).")
        else:
            logging.error(f"API error getting reusable policy '{policy_id}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error getting reusable policy '{policy_id}': {e}", exc_info=True)
        return None

def update_reusable_policy(policy_id, name, decision, include_rules, exclude_rules=None, require_rules=None, purpose_justification_required=False, purpose_justification_prompt=None):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Updating reusable Access Policy ID '{policy_id}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/policies/{policy_id}"

    payload = {
        "name": name,
        "decision": decision,
        "include": include_rules,
    }

    if exclude_rules:
        payload["exclude"] = exclude_rules
    if require_rules:
        payload["require"] = require_rules
    if purpose_justification_required:
        payload["purpose_justification_required"] = purpose_justification_required
    if purpose_justification_prompt:
        payload["purpose_justification_prompt"] = purpose_justification_prompt

    try:
        response_data = cloudflare_api.cf_api_request("PUT", endpoint, json_data=payload)
        policy_data = response_data.get("result")
        if policy_data and policy_data.get("id"):
            logging.info(f"Successfully updated reusable policy ID '{policy_id}'")
            return policy_data
        else:
            logging.error(f"Reusable policy update for '{policy_id}' API call successful but no ID in response: {policy_data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API error updating reusable policy '{policy_id}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error updating reusable policy '{policy_id}': {e}", exc_info=True)
        return None

def delete_reusable_policy(policy_id):
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Deleting reusable Access Policy ID '{policy_id}' on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/policies/{policy_id}"

    try:
        response_data = cloudflare_api.cf_api_request("DELETE", endpoint)
        if response_data and response_data.get("success"):
            logging.info(f"Successfully deleted reusable policy ID '{policy_id}'")
            return True
        elif response_data and response_data.get("success") and not response_data.get("result"):
            logging.info(f"Reusable policy ID '{policy_id}' deletion API call succeeded (success:true, no specific result).")
            return True

        logging.warning(f"Reusable policy deletion for '{policy_id}' API call did not confirm success clearly. Response: {response_data}")
        return False
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            logging.warning(f"Reusable policy with ID '{policy_id}' not found during delete attempt (404). Treating as success.")
            return True
        logging.error(f"API error deleting reusable policy '{policy_id}': {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error deleting reusable policy '{policy_id}': {e}", exc_info=True)
        return False

def list_reusable_policies():
    account_id = current_app.config.get('CF_ACCOUNT_ID')
    logging.info(f"Listing reusable Access Policies on account {account_id}")
    endpoint = f"/accounts/{account_id}/access/policies"

    try:
        response_data = cloudflare_api.cf_api_request("GET", endpoint, params={"per_page": 100})
        policies = response_data.get("result", [])
        if policies and isinstance(policies, list):
            logging.info(f"Successfully retrieved {len(policies)} reusable policies")
            return policies
        else:
            logging.info("No reusable policies found or unexpected response format")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"API error listing reusable policies: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error listing reusable policies: {e}", exc_info=True)
        return []

def find_policy_by_name(name):
    policies = list_reusable_policies()
    for policy in policies:
        if policy.get("name") == name:
            logging.info(f"Found reusable policy '{name}' with ID '{policy.get('id')}'")
            return policy
    logging.info(f"Reusable policy '{name}' not found")
    return None

def sync_access_group_to_reusable_policy(group_id):
    from app.core.state_manager import access_groups, save_state, state_lock

    with state_lock:
        group_definition = access_groups.get(group_id)
        if not group_definition or not group_definition.get("policies"):
            logging.warning(f"Access group '{group_id}' has no policies to sync")
            return None
        local_definition = copy.deepcopy(group_definition)

    is_system_policy = local_definition.get("system_policy", False)
    if is_system_policy and local_definition.get("policies"):
        policy_name = local_definition["policies"][0].get("name", f"DockFlare-AccessGroup-{group_id}")
    else:
        policy_name = f"DockFlare-AccessGroup-{group_id}"

    existing_policy_id = local_definition.get("cloudflare_policy_id")
    policies = local_definition.get("policies", [])
    if not policies:
        logging.warning(f"No policies found in access group '{group_id}'")
        return None

    primary_policy = policies[0]
    decision = primary_policy.get("decision", "allow")
    include_rules = primary_policy.get("include", [])
    exclude_rules = primary_policy.get("exclude")
    require_rules = primary_policy.get("require")

    if decision == "block":
        logging.info(f"Access group '{group_id}' uses 'block' decision. Converting to 'deny' for reusable policy.")
        decision = "deny"

    policy_data = None
    if existing_policy_id:
        existing_policy = get_reusable_policy(existing_policy_id)
        if existing_policy:
            
            def normalize_rules(val):
                return None if (val is None or val == []) else val

            needs_update = False
            update_reason = []
            if existing_policy.get("name") != policy_name:
                needs_update = True
                update_reason.append(f"name: '{existing_policy.get('name')}' → '{policy_name}'")
            if existing_policy.get("decision") != decision:
                needs_update = True
                update_reason.append(f"decision: '{existing_policy.get('decision')}' → '{decision}'")
            if normalize_rules(existing_policy.get("include")) != normalize_rules(include_rules):
                needs_update = True
                update_reason.append(f"include: {existing_policy.get('include')} → {include_rules}")
            if normalize_rules(existing_policy.get("exclude")) != normalize_rules(exclude_rules):
                needs_update = True
                update_reason.append(f"exclude: {existing_policy.get('exclude')} → {exclude_rules}")
            if normalize_rules(existing_policy.get("require")) != normalize_rules(require_rules):
                needs_update = True
                update_reason.append(f"require: {existing_policy.get('require')} → {require_rules}")

            if needs_update:
                logging.info(f"Policy '{policy_name}' needs update - syncing to Cloudflare. Changes: {', '.join(update_reason)}")
                policy_data = update_reusable_policy(
                    existing_policy_id,
                    policy_name,
                    decision,
                    include_rules,
                    exclude_rules=exclude_rules,
                    require_rules=require_rules
                )
            else:
                logging.debug(f"Policy '{policy_name}' already up-to-date - skipping update")
                policy_data = existing_policy
        else:
            logging.warning(f"Existing policy ID '{existing_policy_id}' not found on Cloudflare. Creating new policy.")
            existing_policy_id = None

    if not existing_policy_id:
        existing_by_name = find_policy_by_name(policy_name)
        if existing_by_name:
            policy_id = existing_by_name.get("id")
            logging.info(f"Found existing policy by name '{policy_name}' with ID '{policy_id}'. Updating.")
            policy_data = update_reusable_policy(
                policy_id,
                policy_name,
                decision,
                include_rules,
                exclude_rules=exclude_rules,
                require_rules=require_rules
            )
        else:
            policy_data = create_reusable_policy(
                policy_name,
                decision,
                include_rules,
                exclude_rules=exclude_rules,
                require_rules=require_rules
            )

    if policy_data and policy_data.get("id"):
        policy_id = policy_data.get("id")
        needs_save = False
        with state_lock:
            group_definition = access_groups.get(group_id)
            if group_definition and group_definition.get("cloudflare_policy_id") != policy_id:
                group_definition = copy.deepcopy(group_definition)
                group_definition["cloudflare_policy_id"] = policy_id
                access_groups[group_id] = group_definition
                needs_save = True
        if needs_save:
            save_state()
            logging.info(f"Synced access group '{group_id}' to reusable policy ID '{policy_id}'")
        return policy_id

    logging.error(f"Failed to sync access group '{group_id}' to reusable policy")
    return None

def _slugify_policy_name(name):
    if not name:
        return None
    import re
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', name).strip('-')
    return slug or None

def import_cloudflare_reusable_policies(sync_all=None):
    from app.core.state_manager import access_groups, save_state, state_lock
    from app import config
    
    if sync_all is None:
        sync_all = config.SYNC_ALL_CLOUDFLARE_POLICIES

    logging.info(f"Starting import of Cloudflare reusable policies (sync_all={sync_all})")
    policies = list_reusable_policies()

    imported_count = 0
    updated_count = 0
    skipped_count = 0

    for policy in policies:
        policy_id = policy.get("id")
        policy_name = policy.get("name", "")

        is_dockflare_managed = policy_name.startswith("DockFlare-AccessGroup-") or policy_name.startswith("DockFlare-")

        if not is_dockflare_managed and not sync_all:
            logging.debug(f"Skipping external policy (sync_all=false): {policy_name}")
            skipped_count += 1
            continue

        # Detect system policies
        is_system_policy = False
        system_policy_mapping = {
            "DockFlare-Default-Public-Access-Bypass": {
                "id": "public-default-bypass",
                "display_name": "Public Access (Bypass)"
            },
            "DockFlare-Default-Authenticated-Access": {
                "id": "authenticated-default",
                "display_name": "Authenticated Access"
            }
        }

        if policy_name in system_policy_mapping:
            is_system_policy = True
            group_id = system_policy_mapping[policy_name]["id"]
            display_name = system_policy_mapping[policy_name]["display_name"]
            logging.info(f"Detected system policy '{policy_name}' -> group_id '{group_id}'")
        elif is_dockflare_managed and policy_name.startswith("DockFlare-AccessGroup-"):
            group_id = policy_name.replace("DockFlare-AccessGroup-", "")
            display_name = group_id.replace("-", " ").title()
        else:
            slug = _slugify_policy_name(policy_name)
            if slug:
                base_id = slug
                counter = 1
                with state_lock:
                    while base_id in access_groups and access_groups[base_id].get("cloudflare_policy_id") != policy_id:
                        counter += 1
                        base_id = f"{slug}-{counter}"
                group_id = base_id
            else:
                group_id = policy_id
            display_name = policy_name

        decision = policy.get("decision", "allow")
        include_rules = policy.get("include", [])
        exclude_rules = policy.get("exclude", [])
        require_rules = policy.get("require", [])

        policy_definition = {
            "decision": decision,
            "include": include_rules,
            "name": policy_name
        }
        if exclude_rules:
            policy_definition["exclude"] = exclude_rules
        if require_rules:
            policy_definition["require"] = require_rules

        if group_id in access_groups:
            existing_group = access_groups[group_id]
            if existing_group.get("cloudflare_policy_id") == policy_id:
                logging.debug(f"Access group '{group_id}' already linked to policy '{policy_id}'")
                skipped_count += 1
                continue
            else:
                existing_group["cloudflare_policy_id"] = policy_id
                if not is_dockflare_managed:
                    existing_group["external_policy"] = True
                # Update system_policy flag if this is a system policy
                if is_system_policy:
                    existing_group["system_policy"] = True
                    existing_group["display_name"] = display_name
                logging.info(f"Updated existing access group '{group_id}' with policy ID '{policy_id}'")
                updated_count += 1
        else:
            new_group = {
                "id": group_id,
                "display_name": display_name,
                "session_duration": "24h",
                "app_launcher_visible": False,
                "auto_redirect_to_identity": False,
                "policies": [policy_definition],
                "cloudflare_policy_id": policy_id
            }
            if not is_dockflare_managed:
                new_group["external_policy"] = True
            if is_system_policy:
                new_group["system_policy"] = True
                new_group["deletable"] = False
                logging.info(f"Imported system policy '{group_id}' from Cloudflare policy '{policy_id}'")
            else:
                logging.info(f"Imported {'external' if not is_dockflare_managed else ''} access group '{group_id}' from Cloudflare policy '{policy_id}'")
            access_groups[group_id] = new_group
            imported_count += 1

    if imported_count > 0 or updated_count > 0:
        save_state()

    logging.info(f"Import complete: {imported_count} new, {updated_count} updated, {skipped_count} skipped")
    return {
        "imported": imported_count,
        "updated": updated_count,
        "skipped": skipped_count,
        "total": len(policies)
    }

def delete_access_group_and_policy(group_id):
    from app.core.state_manager import access_groups, save_state

    if group_id not in access_groups:
        logging.warning(f"Access group '{group_id}' not found in state")
        return False

    group = access_groups[group_id]
    policy_id = group.get("cloudflare_policy_id")

    if policy_id:
        logging.info(f"Deleting Cloudflare reusable policy '{policy_id}' for access group '{group_id}'")
        success = delete_reusable_policy(policy_id)
        if not success:
            logging.warning(f"Failed to delete Cloudflare policy '{policy_id}', but will remove from state")
    else:
        logging.info(f"No Cloudflare policy ID found for access group '{group_id}', removing from state only")

    del access_groups[group_id]
    save_state()
    logging.info(f"Removed access group '{group_id}' from state")
    return True
