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
# dockflare/app/core/state_manager.py
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List
from app import config
from app.core import agent_key_store
from app.core.utils import get_rule_key

managed_rules = {}
access_groups = {}
agents = {}
identity_providers = {}
state_lock = threading.RLock()
logging.info(
    "STATE_MANAGER_INIT: managed_rules ID: %s, access_groups ID: %s, agents ID: %s, identity_providers ID: %s",
    id(managed_rules),
    id(access_groups),
    id(agents),
    id(identity_providers)
)

def _deserialize_datetime(dt_str):
    if not dt_str:
        return None
    try:
        if dt_str.endswith('Z'):
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError as date_err:
        logging.warning(f"Could not parse datetime string '{dt_str}': {date_err}. Returning None.")
        return None

def load_state():
    logging.info(f"LOAD_STATE: Start. Initial managed_rules ID: {id(managed_rules)}, Current len: {len(managed_rules)}")
    state_dir = os.path.dirname(config.STATE_FILE_PATH)
    
    with state_lock:
        managed_rules.clear()
        access_groups.clear()
        identity_providers.clear()
        logging.info(
            "LOAD_STATE: After .clear(), managed_rules ID: %s, len: %s",
            id(managed_rules),
            len(managed_rules)
        )

        if not os.path.exists(state_dir):
            try:
                os.makedirs(state_dir, exist_ok=True)
                logging.info(f"LOAD_STATE: Created directory for state file: {state_dir}")
            except OSError as e:
                logging.error(f"LOAD_STATE: FATAL - Could not create directory {state_dir}: {e}. State will be empty.")
                return

        if not os.path.exists(config.STATE_FILE_PATH):
            logging.info(f"LOAD_STATE: State file '{config.STATE_FILE_PATH}' not found, starting fresh (already cleared).")
            return

        try:
            logging.info(f"LOAD_STATE: Reading from {config.STATE_FILE_PATH}.")
            with open(config.STATE_FILE_PATH, 'r') as f:
                loaded_data = json.load(f)

            rules_to_load = {}
            groups_to_load = {}

            if isinstance(loaded_data, dict) and "managed_rules" in loaded_data:
                logging.info("Loading state from new format (with access_groups and agents).")
                rules_to_load = loaded_data.get("managed_rules", {})
                groups_to_load = loaded_data.get("access_groups", {})
                agents_to_load = loaded_data.get("agents", {})
                idps_to_load = loaded_data.get("identity_providers", {})
            else:
                logging.info("Loading state from old format (rules only). Will migrate on next save.")
                rules_to_load = loaded_data
                agents_to_load = {}
                idps_to_load = {}

            access_groups.update(groups_to_load)
            agents.update(agents_to_load)
            identity_providers.update(idps_to_load)
            key_count = len(agent_key_store.list_keys())
            logging.info(
                "LOAD_STATE: Loaded %s access groups, %s agents and %s agent keys (encrypted backing store).",
                len(access_groups),
                len(agents),
                key_count
            )

            migrated_count = 0
            tunnel_name_migration_count = 0
            for key, rule_data in rules_to_load.items():
                rule_copy = rule_data.copy()

                final_key = key
                if '|' not in key:
                    hostname_from_key = key
                    path_from_data = rule_copy.get("path")
                    if "hostname" not in rule_copy:
                        rule_copy["hostname"] = hostname_from_key
                    final_key = get_rule_key(hostname_from_key, path_from_data)
                    migrated_count += 1
                    logging.info(f"Migrating old rule key '{key}' to new key '{final_key}'")

                delete_at_val = rule_copy.get("delete_at")
                if isinstance(delete_at_val, str):
                    rule_copy["delete_at"] = _deserialize_datetime(delete_at_val)
                elif not isinstance(delete_at_val, (datetime, type(None))):
                    rule_copy["delete_at"] = None

                rule_copy.setdefault("zone_id", None)
                rule_copy.setdefault("access_app_id", None)
                rule_copy.setdefault("access_policy_type", None)
                rule_copy.setdefault("access_app_config_hash", None)
                rule_copy.setdefault("access_policy_ui_override", False)
                rule_copy.setdefault("rule_ui_override", False)
                rule_copy.setdefault("source", "docker")
                rule_copy.setdefault("path", None)
                rule_copy.setdefault("http_host_header", None)
                rule_copy.setdefault("access_group_id", None)
                rule_copy.setdefault("tunnel_id", None)
                rule_copy.setdefault("zone_name", None)
                rule_copy.setdefault("no_tls_verify", False)
                rule_copy.setdefault("origin_server_name", None)
                rule_copy.setdefault("http2_origin", False)
                rule_copy.setdefault("disable_chunked_encoding", False)
                rule_copy.setdefault("match_sni_to_host", False)

                tunnel_name = rule_copy.get("tunnel_name")
                if not tunnel_name or tunnel_name == "dockflare-tunnel":
                    tunnel_name_migration_count += 1
                    logging.debug(f"Rule '{final_key}' missing or has default tunnel name, will be updated later")
                rule_copy.setdefault("tunnel_name", None)

                managed_rules[final_key] = rule_copy

            migration_needed = migrated_count > 0 or tunnel_name_migration_count > 0
            if migrated_count > 0:
                logging.info(f"LOAD_STATE: Migrated {migrated_count} rules to the new key format.")
            if tunnel_name_migration_count > 0:
                logging.info(f"LOAD_STATE: Found {tunnel_name_migration_count} rules with missing/default tunnel names, will update after tunnel initialization.")
            if migration_needed:
                save_state()
            
            logging.info(f"LOAD_STATE: Loaded {len(managed_rules)} rules. managed_rules ID after populating: {id(managed_rules)}")
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"LOAD_STATE: Error loading state from {config.STATE_FILE_PATH}: {e}. Starting fresh (already cleared).", exc_info=True)
        except Exception as e_load_unexp:
            logging.error(f"LOAD_STATE: Unexpected error loading state: {e_load_unexp}. Starting fresh (already cleared).", exc_info=True)

def ensure_default_bypass_policy(flask_app=None):
    
    from app.core import reusable_policies

    default_bypass_id = "public-default-bypass"
    cf_policy_name = "DockFlare-Default-Public-Access-Bypass"
    display_name = "Public Access (Bypass)"

    with state_lock:
        # Check if policy exists in local state
        if default_bypass_id not in access_groups:
            logging.info(f"Creating default bypass access group in state: {default_bypass_id}")

            
            cf_policy_id = None
            if flask_app:
                with flask_app.app_context():
                    try:
                        
                        existing_by_name = reusable_policies.find_policy_by_name(cf_policy_name)
                        if existing_by_name:
                            cf_policy_id = existing_by_name.get("id")
                            logging.info(f"Found existing bypass policy in Cloudflare by name with ID: {cf_policy_id}")
                        else:
                            
                            cf_policy = reusable_policies.create_reusable_policy(
                                name=cf_policy_name,
                                decision="bypass",
                                include_rules=[{"everyone": {}}]
                            )
                            if cf_policy and cf_policy.get("id"):
                                cf_policy_id = cf_policy["id"]
                                logging.info(f"Created default bypass policy in Cloudflare with ID: {cf_policy_id}")
                            else:
                                logging.warning(f"Failed to create default bypass policy in Cloudflare, will create local reference only")
                    except Exception as e:
                        logging.error(f"Error checking/creating default bypass policy in Cloudflare: {e}", exc_info=True)

            
            access_groups[default_bypass_id] = {
                "id": cf_policy_id if cf_policy_id else default_bypass_id,
                "display_name": display_name,
                "session_duration": "24h",
                "app_launcher_visible": False,
                "auto_redirect_to_identity": False,
                "public_mode": True,
                "policies": [
                    {
                        "name": cf_policy_name,
                        "decision": "bypass",
                        "include": [{"everyone": {}}]
                    }
                ],
                "system_policy": True,
                "deletable": False,
                "cf_policy_id": cf_policy_id,
                "cloudflare_policy_id": cf_policy_id
            }
            save_state()
            logging.info(f"Default bypass policy '{default_bypass_id}' created successfully in local state.")
        else:
            logging.debug(f"Default bypass policy '{default_bypass_id}' already exists in local state.")

            existing_policy = access_groups[default_bypass_id]

            
            if existing_policy.get("hide_from_ui"):
                logging.info(f"Migrating existing bypass policy to show in UI (removing hide_from_ui flag)")
                del existing_policy["hide_from_ui"]
                save_state()

            cf_policy_id = existing_policy.get("cf_policy_id") or existing_policy.get("id")

            if flask_app and cf_policy_id != default_bypass_id:  # Has a real CF ID
                with flask_app.app_context():
                    try:
                        cf_policy = reusable_policies.get_reusable_policy(cf_policy_id)
                        if cf_policy:
                            logging.debug(f"Verified default bypass policy exists in Cloudflare: {cf_policy_id}")
                        else:
                            logging.warning(f"Default bypass policy {cf_policy_id} not found in Cloudflare, searching by name")
                            existing_by_name = reusable_policies.find_policy_by_name(cf_policy_name)
                            if existing_by_name:
                                found_policy_id = existing_by_name.get("id")
                                logging.info(f"Found existing bypass policy by name with ID: {found_policy_id}")
                                existing_policy["cloudflare_policy_id"] = found_policy_id
                                existing_policy["cf_policy_id"] = found_policy_id
                                save_state()
                            else:
                                logging.info(f"No existing bypass policy found, creating new one")
                                new_policy = reusable_policies.create_reusable_policy(
                                    name=cf_policy_name,
                                    decision="bypass",
                                    include_rules=[{"everyone": {}}]
                                )
                                if new_policy and new_policy.get("id"):
                                    new_cf_policy_id = new_policy["id"]
                                    logging.info(f"Created bypass policy in Cloudflare with ID: {new_cf_policy_id}")
                                    existing_policy["cloudflare_policy_id"] = new_cf_policy_id
                                    existing_policy["cf_policy_id"] = new_cf_policy_id
                                    save_state()
                                else:
                                    logging.error(f"Failed to create bypass policy in Cloudflare")
                    except Exception as e:
                        logging.error(f"Error verifying/updating default bypass policy in Cloudflare: {e}")

def ensure_authenticated_default_policy(flask_app=None):

    from app.core import reusable_policies
    from app.core.cloudflare_api import get_cloudflare_account_email

    authenticated_default_id = "authenticated-default"
    cf_policy_name = "DockFlare-Default-Authenticated-Access"
    display_name = "Authenticated Access"

    account_email = None
    if flask_app:
        with flask_app.app_context():
            account_email = get_cloudflare_account_email()
    else:
        account_email = get_cloudflare_account_email()

    if not account_email:
        logging.warning("Cannot create authenticated-default policy: Cloudflare account email not available")
        return

    with state_lock:
        onetimepin_idp = identity_providers.get("onetimepin")
        if not onetimepin_idp or not onetimepin_idp.get("cloudflare_id"):
            logging.warning("Cannot create authenticated-default policy: One-time PIN IdP not found in state")
            logging.debug(f"Available IdPs in state: {list(identity_providers.keys())}")
            return

        onetimepin_cf_id = onetimepin_idp["cloudflare_id"]
        if authenticated_default_id not in access_groups:
            logging.info(f"Creating default authenticated access group in state: {authenticated_default_id}")

            cf_policy_id = None
            if flask_app:
                with flask_app.app_context():
                    try:
                        
                        existing_by_name = reusable_policies.find_policy_by_name(cf_policy_name)
                        if existing_by_name:
                            cf_policy_id = existing_by_name.get("id")
                            logging.info(f"Found existing authenticated policy in Cloudflare by name with ID: {cf_policy_id}")
                        else:
                            
                            cf_policy = reusable_policies.create_reusable_policy(
                                name=cf_policy_name,
                                decision="allow",
                                include_rules=[{"login_method": {"id": onetimepin_cf_id}}],
                                require_rules=[{"email": {"email": account_email}}]
                            )
                            if cf_policy and cf_policy.get("id"):
                                cf_policy_id = cf_policy["id"]
                                logging.info(f"Created default authenticated policy in Cloudflare with ID: {cf_policy_id}")
                            else:
                                logging.warning(f"Failed to create default authenticated policy in Cloudflare, will create local reference only")
                    except Exception as e:
                        logging.error(f"Error checking/creating default authenticated policy in Cloudflare: {e}", exc_info=True)

            access_groups[authenticated_default_id] = {
                "id": cf_policy_id if cf_policy_id else authenticated_default_id,
                "display_name": "Authenticated Access",
                "session_duration": "24h",
                "app_launcher_visible": False,
                "auto_redirect_to_identity": False,
                "public_mode": False,
                "allowed_idps": [onetimepin_cf_id],
                "policies": [
                    {
                        "name": cf_policy_name,
                        "decision": "allow",
                        "include": [{"login_method": {"id": onetimepin_cf_id}}],
                        "require": [{"email": {"email": account_email}}]
                    }
                ],
                "system_policy": True,
                "deletable": False,
                "cf_policy_id": cf_policy_id,
                "cloudflare_policy_id": cf_policy_id
            }
            save_state()
            logging.info(f"Default authenticated policy '{authenticated_default_id}' created successfully in local state.")
        else:
            logging.debug(f"Default authenticated policy '{authenticated_default_id}' already exists in local state.")

            existing_policy = access_groups[authenticated_default_id]

            needs_state_update = False
            needs_cf_update = False

            
            if existing_policy.get("hide_from_ui"):
                logging.info(f"Migrating existing authenticated-default policy to show in UI (removing hide_from_ui flag)")
                del existing_policy["hide_from_ui"]
                needs_state_update = True
            
            if not existing_policy.get("policies") or len(existing_policy.get("policies", [])) == 0:
                logging.warning(f"authenticated-default policy missing policies array - recreating it")
                existing_policy["policies"] = [
                    {
                        "name": cf_policy_name,
                        "decision": "allow",
                        "include": [{"login_method": {"id": onetimepin_cf_id}}],
                        "require": [{"email": {"email": account_email}}]
                    }
                ]
                needs_state_update = True
                needs_cf_update = True

            if existing_policy.get("display_name") != "Authenticated Access":
                logging.info(f"Updating authenticated-default display name to shorter version")
                existing_policy["display_name"] = "Authenticated Access"
                needs_state_update = True

            current_allowed_idps = existing_policy.get("allowed_idps", [])
            if not current_allowed_idps or current_allowed_idps == ["onetimepin"]:
                logging.info(f"Migrating existing authenticated-default policy to use correct one-time PIN IdP UUID in allowed_idps")
                existing_policy["allowed_idps"] = [onetimepin_cf_id]
                needs_state_update = True

            existing_include = existing_policy.get("policies", [{}])[0].get("include", [])
            has_correct_login_method = any(
                rule.get("login_method", {}).get("id") == onetimepin_cf_id
                for rule in existing_include
            )

            existing_require = existing_policy.get("policies", [{}])[0].get("require", [])
            has_email_in_require = any(
                rule.get("email", {}).get("email") == account_email
                for rule in existing_require
            )

            if not has_correct_login_method or not has_email_in_require:
                logging.info(f"Migrating authenticated-default policy to use include=login_method + require=email structure")
                if existing_policy.get("policies") and len(existing_policy["policies"]) > 0:
                    existing_policy["policies"][0]["include"] = [{"login_method": {"id": onetimepin_cf_id}}]
                    existing_policy["policies"][0]["require"] = [{"email": {"email": account_email}}]
                    needs_state_update = True
                    needs_cf_update = True

            if needs_state_update:
                save_state()

            cf_policy_id = existing_policy.get("cloudflare_policy_id") or existing_policy.get("cf_policy_id") or existing_policy.get("id")

            if flask_app and cf_policy_id != authenticated_default_id:
                with flask_app.app_context():
                    try:
                        cf_policy = reusable_policies.get_reusable_policy(cf_policy_id)
                        if cf_policy:
                            logging.debug(f"Verified default authenticated policy exists in Cloudflare: {cf_policy_id}")

                            if needs_cf_update:
                                logging.info(f"Updating Cloudflare reusable policy {cf_policy_id} with include=login_method + require=email")
                                updated_policy = reusable_policies.update_reusable_policy(
                                    cf_policy_id,
                                    cf_policy_name,
                                    "allow",
                                    include_rules=[{"login_method": {"id": onetimepin_cf_id}}],
                                    require_rules=[{"email": {"email": account_email}}]
                                )
                                if updated_policy:
                                    logging.info(f"Successfully updated Cloudflare policy {cf_policy_id} with correct structure")
                                else:
                                    logging.error(f"Failed to update Cloudflare policy {cf_policy_id}")
                        else:
                            logging.warning(f"Default authenticated policy {cf_policy_id} not found in Cloudflare, searching by name")
                            existing_by_name = reusable_policies.find_policy_by_name(cf_policy_name)
                            if existing_by_name:
                                found_policy_id = existing_by_name.get("id")
                                logging.info(f"Found existing authenticated-default policy by name with ID: {found_policy_id}")
                                existing_policy["cloudflare_policy_id"] = found_policy_id
                                existing_policy["cf_policy_id"] = found_policy_id
                                save_state()
                            else:
                                logging.info(f"No existing authenticated-default policy found, creating new one")
                                new_policy = reusable_policies.create_reusable_policy(
                                    name=cf_policy_name,
                                    decision="allow",
                                    include_rules=[{"login_method": {"id": onetimepin_cf_id}}],
                                    require_rules=[{"email": {"email": account_email}}]
                                )
                                if new_policy and new_policy.get("id"):
                                    new_cf_policy_id = new_policy["id"]
                                    logging.info(f"Created authenticated-default policy in Cloudflare with ID: {new_cf_policy_id}")
                                    existing_policy["cloudflare_policy_id"] = new_cf_policy_id
                                    existing_policy["cf_policy_id"] = new_cf_policy_id
                                    save_state()
                                else:
                                    logging.error(f"Failed to create authenticated-default policy in Cloudflare")
                    except Exception as e:
                        logging.error(f"Error verifying/updating default authenticated policy in Cloudflare: {e}")

def save_state():
    with state_lock:
        current_thread_name = threading.current_thread().name
        logging.info(f"SAVE_STATE: Start. THREAD: {current_thread_name}. Items to save: {len(managed_rules)} rules, {len(access_groups)} access groups.")

        serializable_rules = {}
        rules_to_iterate = list(managed_rules.items())
        groups_to_iterate = dict(access_groups)
        agents_to_iterate = dict(agents)
        idps_to_iterate = dict(identity_providers)

        for rule_key, rule in rules_to_iterate:
            try:
                data_to_serialize = {
                    "hostname": rule.get("hostname"),
                    "path": rule.get("path"),
                    "service": rule.get("service"),
                    "container_id": rule.get("container_id"),
                    "status": rule.get("status"),
                    "delete_at": None,
                    "zone_id": rule.get("zone_id"),
                    "no_tls_verify": rule.get("no_tls_verify", False),
                    "origin_server_name": rule.get("origin_server_name"),
                    "http_host_header": rule.get("http_host_header"),
                    "http2_origin": rule.get("http2_origin", False),
                    "disable_chunked_encoding": rule.get("disable_chunked_encoding", False),
                    "match_sni_to_host": rule.get("match_sni_to_host", False),
                    "access_app_id": rule.get("access_app_id"),
                    "access_policy_type": rule.get("access_policy_type"),
                    "access_app_config_hash": rule.get("access_app_config_hash"),
                    "access_policy_ui_override": rule.get("access_policy_ui_override", False),
                    "rule_ui_override": rule.get("rule_ui_override", False),
                    "source": rule.get("source", "docker"),
                    "access_group_id": rule.get("access_group_id"),
                    "tunnel_id": rule.get("tunnel_id"),
                    "tunnel_name": rule.get("tunnel_name"),
                    "zone_name": rule.get("zone_name")
                }
                delete_at_val = rule.get("delete_at")
                if isinstance(delete_at_val, datetime):
                    data_to_serialize["delete_at"] = delete_at_val.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
                serializable_rules[rule_key] = data_to_serialize
            except Exception as e_serialize_item:
                logging.error(f"SAVE_STATE_LOOP_ERROR: THREAD: {current_thread_name}. Error preparing rule for serialization '{rule_key}': {e_serialize_item}. Rule data: {rule}", exc_info=True)
                continue
        
        final_state_to_save = {
            "managed_rules": serializable_rules,
            "access_groups": groups_to_iterate,
            "agents": agents_to_iterate,
            "identity_providers": idps_to_iterate
        }

        try:
            state_dir = os.path.dirname(config.STATE_FILE_PATH)
            if not os.path.exists(state_dir):
                try:
                    os.makedirs(state_dir, exist_ok=True)
                except OSError as e_mkdir:
                    logging.error(f"SAVE_STATE: THREAD: {current_thread_name}. Mkdir error {e_mkdir}. Save failed.")
                    return
            temp_file_path = config.STATE_FILE_PATH + ".tmp"
            with open(temp_file_path, 'w') as f:
                json.dump(final_state_to_save, f, indent=2)
            os.replace(temp_file_path, config.STATE_FILE_PATH)
            logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Successfully saved state to {config.STATE_FILE_PATH}")
        except Exception as e_save_io:
            logging.error(f"SAVE_STATE: THREAD: {current_thread_name}. File I/O or other error: {e_save_io}", exc_info=True)
        
        logging.info(f"SAVE_STATE: End. THREAD: {current_thread_name}.")

def add_agent(agent_id, agent_data):
    """
    Add a new agent entry to state and persist.
    agent_id: string (unique)
    agent_data: dict (metadata/state for the agent)
    """
    with state_lock:
        agents[agent_id] = agent_data
        save_state()

def get_agent(agent_id):
    """Return agent data dict or None."""
    with state_lock:
        return agents.get(agent_id)

def update_agent(agent_id, updates):
    """
    Update agent data with provided dict of updates.
    Returns True if agent existed and was updated, False otherwise.
    """
    with state_lock:
        if agent_id not in agents:
            return False
        agents[agent_id].update(updates)
        save_state()
        return True

def list_agents():
    """Return a shallow copy of agents dict."""
    with state_lock:
        return dict(agents)

def remove_agent(agent_id):
    """
    Remove an agent by id. Returns True if removed, False if not present.
    """
    with state_lock:
        if agent_id in agents:
            del agents[agent_id]
            save_state()
            return True
        return False

def add_agent_key(key_id, key_meta=None):
    """Persist an agent API key to the encrypted key store."""
    metadata = key_meta or {}
    agent_key_store.upsert_key(key_id, metadata)

def revoke_agent_key(key_id):
    """
    Revoke (remove) an agent API key. Returns True if removed, False if not present.
    """
    key_meta = agent_key_store.get_key(key_id)
    if not key_meta:
        return False

    meta_update = dict(key_meta)
    meta_update["status"] = "revoked"
    meta_update["revoked_at"] = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    agent_key_store.upsert_key(key_id, meta_update)
    return True

def find_agent_id_by_key(key_id):
    """
    Attempt to find an agent_id associated with the provided key.
    This implementation looks for:
      - key metadata 'owner' pointing to an agent_id
      - otherwise returns None (caller may allow shared keys)
    """
    info = agent_key_store.get_key(key_id)
    if not info:
        return None
    owner = info.get('owner')
    return owner

def get_agent_key_info(key_id):
    """Return metadata for a given key or None."""
    return agent_key_store.get_key(key_id)

def list_agent_keys():
    """Return a shallow copy of the agent key metadata from the encrypted store."""
    return agent_key_store.list_keys()

def cleanup_expired_revoked_keys(retention_days=30):
    """
    Auto-cleanup revoked keys older than retention_days.
    Returns dict with cleanup results.
    """
    if retention_days <= 0:
        return {"status": "skipped", "message": "Auto-cleanup disabled"}

    all_keys = agent_key_store.list_keys()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    expired_keys = []
    cleaned_count = 0

    for key_id, key_info in all_keys.items():
        if key_info.get("status") != "revoked":
            continue

        revoked_at_str = key_info.get("revoked_at")
        if not revoked_at_str:
            continue

        try:
            # Parse revocation timestamp
            if revoked_at_str.endswith('Z'):
                revoked_at = datetime.fromisoformat(revoked_at_str.replace('Z', '+00:00'))
            else:
                revoked_at = datetime.fromisoformat(revoked_at_str)
            revoked_at = revoked_at.replace(tzinfo=timezone.utc) if revoked_at.tzinfo is None else revoked_at.astimezone(timezone.utc)

            # Check if key is expired
            days_since_revoked = (now - revoked_at).days
            if days_since_revoked >= retention_days:
                owner = key_info.get("owner", "unknown")
                expired_keys.append({
                    "key_id": key_id,
                    "owner": owner,
                    "revoked_at": revoked_at_str,
                    "days_old": days_since_revoked
                })

                # Remove the expired key
                agent_key_store.remove_key(key_id)
                cleaned_count += 1
                logging.info(f"AUTO_CLEANUP: Removed expired revoked key {key_id[:8]}... (owner: {owner}, revoked {days_since_revoked} days ago)")

        except Exception as e:
            logging.warning(f"AUTO_CLEANUP: Failed to process revoked key {key_id[:8]}: {e}")

    result = {
        "status": "completed",
        "cleaned_count": cleaned_count,
        "retention_days": retention_days,
        "expired_keys": expired_keys
    }

    if cleaned_count > 0:
        logging.info(f"AUTO_CLEANUP: Removed {cleaned_count} expired revoked keys (retention: {retention_days} days)")

    return result

def get_revoked_keys_summary():
    """
    Get summary information about revoked keys for display.
    Returns dict with revoked key counts and aging info.
    """
    all_keys = agent_key_store.list_keys()
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    revoked_keys = []
    for key_id, key_info in all_keys.items():
        if key_info.get("status") != "revoked":
            continue

        revoked_at_str = key_info.get("revoked_at")
        days_until_cleanup = None

        if revoked_at_str:
            try:
                if revoked_at_str.endswith('Z'):
                    revoked_at = datetime.fromisoformat(revoked_at_str.replace('Z', '+00:00'))
                else:
                    revoked_at = datetime.fromisoformat(revoked_at_str)
                revoked_at = revoked_at.replace(tzinfo=timezone.utc) if revoked_at.tzinfo is None else revoked_at.astimezone(timezone.utc)

                # Calculate days until auto-cleanup (assuming 30 day retention)
                days_since_revoked = (now - revoked_at).days
                days_until_cleanup = max(0, 30 - days_since_revoked)

            except Exception:
                pass

        revoked_keys.append({
            "key_id": key_id,
            "owner": key_info.get("owner", "unknown"),
            "revoked_at": revoked_at_str,
            "days_until_cleanup": days_until_cleanup
        })

    return {
        "revoked_count": len(revoked_keys),
        "revoked_keys": revoked_keys
    }

def get_agent_rules(agent_id):
    """Return all active rules for a specific agent."""
    with state_lock:
        return {
            key: rule for key, rule in managed_rules.items()
            if rule.get("agent_id") == agent_id and rule.get("status") == "active"
        }


def _serialize_datetime(value):
    if isinstance(value, datetime):
        value_utc = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return value_utc.isoformat().replace('+00:00', 'Z')
    return None


def serialize_managed_rule(rule_key: str, rule: Dict[str, Any]) -> Dict[str, Any]:
    if not rule:
        return {"id": rule_key}

    return {
        "id": rule_key,
        "hostname": rule.get("hostname"),
        "path": rule.get("path"),
        "service": rule.get("service"),
        "status": rule.get("status"),
        "delete_at": _serialize_datetime(rule.get("delete_at")),
        "zone_id": rule.get("zone_id"),
        "zone_name": rule.get("zone_name"),
        "source": rule.get("source"),
        "container_id": rule.get("container_id"),
        "tunnel_id": rule.get("tunnel_id"),
        "tunnel_name": rule.get("tunnel_name"),
        "access_policy_type": rule.get("access_policy_type"),
        "access_policy_ui_override": rule.get("access_policy_ui_override", False),
        "rule_ui_override": rule.get("rule_ui_override", False)
    }


def get_services_snapshot() -> List[Dict[str, Any]]:
    with state_lock:
        return [
            serialize_managed_rule(rule_key, rule.copy())
            for rule_key, rule in managed_rules.items()
        ]

def update_tunnel_names_after_initialization():
    """
    Update tunnel names for rules that have missing or default tunnel names.
    This is called after tunnel initialization to fix migration issues.
    """
    from app import tunnel_state
    from app.core.cloudflare_api import get_tunnel_name_by_id

    updated_count = 0

    with state_lock:
        master_tunnel_id = tunnel_state.get("id")
        master_tunnel_name = tunnel_state.get("name")

        if not master_tunnel_id:
            logging.debug("No master tunnel ID available, skipping tunnel name updates")
            return updated_count

        for rule_key, rule in managed_rules.items():
            rule_tunnel_id = rule.get("tunnel_id")
            current_tunnel_name = rule.get("tunnel_name")

            if not current_tunnel_name or current_tunnel_name == "dockflare-tunnel":
                new_tunnel_name = None

                if rule_tunnel_id == master_tunnel_id and master_tunnel_name:
                    new_tunnel_name = master_tunnel_name
                elif rule_tunnel_id:
                    api_tunnel_name = get_tunnel_name_by_id(rule_tunnel_id)
                    if api_tunnel_name:
                        new_tunnel_name = api_tunnel_name

                if new_tunnel_name and new_tunnel_name != current_tunnel_name:
                    rule["tunnel_name"] = new_tunnel_name
                    updated_count += 1
                    logging.debug(f"Updated tunnel name for rule '{rule_key}': '{current_tunnel_name}' -> '{new_tunnel_name}'")

        if updated_count > 0:
            logging.info(f"Updated tunnel names for {updated_count} rules after tunnel initialization")
            save_state()

    return updated_count

def save_identity_provider(friendly_name, idp_data):
    with state_lock:
        identity_providers[friendly_name] = idp_data
        logging.info(f"Saved identity provider '{friendly_name}' to state")
    save_state()

def get_identity_provider(friendly_name):
    with state_lock:
        return identity_providers.get(friendly_name)

def delete_identity_provider(friendly_name):
    with state_lock:
        if friendly_name in identity_providers:
            del identity_providers[friendly_name]
            logging.info(f"Deleted identity provider '{friendly_name}' from state")
            save_state()
            return True
        return False

def list_identity_providers():
    with state_lock:
        return dict(identity_providers)

def get_idp_by_cloudflare_id(cloudflare_id):
    with state_lock:
        for friendly_name, idp_data in identity_providers.items():
            if idp_data.get("cloudflare_id") == cloudflare_id:
                return friendly_name, idp_data
        return None, None

def get_idp_id_by_name(friendly_name):
    with state_lock:
        idp = identity_providers.get(friendly_name)
        if idp:
            return idp.get("cloudflare_id")
        return None

def queue_agent_command(agent_id: str, command: dict) -> bool:
    """
    Queue a command for an agent to execute on next poll.

    Args:
        agent_id: The agent ID
        command: Command dict with 'action' and other params

    Returns:
        True if queued successfully, False if agent not found
    """
    with state_lock:
        agent = agents.get(agent_id)
        if not agent:
            logging.warning(f"Cannot queue command for agent {agent_id}: agent not found")
            return False

        if "commands" not in agent:
            agent["commands"] = []

        agent["commands"].append(command)
        logging.info(f"Queued command '{command.get('action')}' for agent {agent_id}")
        save_state()
        return True
