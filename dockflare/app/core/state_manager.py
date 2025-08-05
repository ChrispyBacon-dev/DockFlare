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
# app/core/state_manager.py
import json
import logging
import os
import threading
from datetime import datetime, timezone

from app import config
from app.core.utils import get_rule_key

managed_rules = {}
access_groups = {}
state_lock = threading.RLock()
logging.info(f"STATE_MANAGER_INIT: managed_rules ID: {id(managed_rules)}, access_groups ID: {id(access_groups)}")

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
        logging.info(f"LOAD_STATE: After .clear(), managed_rules ID: {id(managed_rules)}, len: {len(managed_rules)}")

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
                logging.info("Loading state from new format (with access_groups).")
                rules_to_load = loaded_data.get("managed_rules", {})
                groups_to_load = loaded_data.get("access_groups", {})
            else:
                logging.info("Loading state from old format (rules only). Will migrate on next save.")
                rules_to_load = loaded_data

            access_groups.update(groups_to_load)
            logging.info(f"LOAD_STATE: Loaded {len(access_groups)} access groups.")

            migrated_count = 0
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
                rule_copy.setdefault("source", "docker")
                rule_copy.setdefault("path", None)
                rule_copy.setdefault("http_host_header", None)
                rule_copy.setdefault("access_group_id", None)
                
                managed_rules[final_key] = rule_copy

            if migrated_count > 0:
                logging.info(f"LOAD_STATE: Migrated {migrated_count} rules to the new key format.")
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
    
    if not rules_to_iterate and not groups_to_iterate:
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. State is empty. Proceeding to write empty state file.")
    else:
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Serializing {len(rules_to_iterate)} rules and {len(groups_to_iterate)} groups.")

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
                "source": rule.get("source", "docker"),
                "access_group_id": rule.get("access_group_id")
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
        "access_groups": groups_to_iterate
    }

    logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Prepared final state with {len(serializable_rules)} rules and {len(groups_to_iterate)} groups.")

    try:
        state_dir = os.path.dirname(config.STATE_FILE_PATH)
        if not os.path.exists(state_dir):
            try: os.makedirs(state_dir, exist_ok=True)
            except OSError as e_mkdir: logging.error(f"SAVE_STATE: THREAD: {current_thread_name}. Mkdir error {e_mkdir}. Save failed."); return
        temp_file_path = config.STATE_FILE_PATH + ".tmp"
        with open(temp_file_path, 'w') as f: json.dump(final_state_to_save, f, indent=2)
        os.replace(temp_file_path, config.STATE_FILE_PATH)
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Successfully saved state for {len(serializable_rules)} rules and {len(groups_to_iterate)} groups to {config.STATE_FILE_PATH}")
    except Exception as e_save_io:
        logging.error(f"SAVE_STATE: THREAD: {current_thread_name}. File I/O or other error: {e_save_io}", exc_info=True)
    
    logging.info(f"SAVE_STATE: End. THREAD: {current_thread_name}.")