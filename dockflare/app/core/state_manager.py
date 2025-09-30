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
state_lock = threading.RLock()
logging.info(
    "STATE_MANAGER_INIT: managed_rules ID: %s, access_groups ID: %s, agents ID: %s",
    id(managed_rules),
    id(access_groups),
    id(agents)
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
            else:
                logging.info("Loading state from old format (rules only). Will migrate on next save.")
                rules_to_load = loaded_data
                agents_to_load = {}

            access_groups.update(groups_to_load)
            agents.update(agents_to_load)
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

def save_state():
    global managed_rules, access_groups
    current_thread_name = threading.current_thread().name
    
    with state_lock:
        logging.info(f"SAVE_STATE: Start (RLock acquired). THREAD: {current_thread_name}. Items to save: {len(managed_rules)} rules, {len(access_groups)} access groups.")
        
    serializable_rules = {}
    rules_to_iterate = list(managed_rules.items())
    groups_to_iterate = dict(access_groups)
    agents_to_iterate = dict(agents)
    if not rules_to_iterate and not groups_to_iterate and not agents_to_iterate:
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. State is empty. Proceeding to write empty state file.")
    else:
        logging.info(
            "SAVE_STATE: THREAD: %s. Serializing %s rules, %s groups and %s agents.",
            current_thread_name,
            len(rules_to_iterate),
            len(groups_to_iterate),
            len(agents_to_iterate)
        )

    for rule_key, rule in rules_to_iterate:
        logging.debug(f"SAVE_STATE_LOOP: THREAD: {current_thread_name}. Preparing rule for key: {rule_key}")
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
                logging.debug(f"SAVE_STATE_LOOP: THREAD: {current_thread_name}. Serializing datetime for {rule_key} (value: {delete_at_val}).")
                data_to_serialize["delete_at"] = delete_at_val.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            serializable_rules[rule_key] = data_to_serialize
        except Exception as e_serialize_item:
            logging.error(f"SAVE_STATE_LOOP_ERROR: THREAD: {current_thread_name}. Error preparing rule for serialization '{rule_key}': {e_serialize_item}. Rule data: {rule}", exc_info=True)
            continue
    
    final_state_to_save = {
        "managed_rules": serializable_rules,
        "access_groups": groups_to_iterate,
        "agents": agents_to_iterate
    }

    logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Prepared final state with {len(serializable_rules)} rules and {len(groups_to_iterate)} groups.")

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
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Successfully saved state for {len(serializable_rules)} rules and {len(groups_to_iterate)} groups to {config.STATE_FILE_PATH}")
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
