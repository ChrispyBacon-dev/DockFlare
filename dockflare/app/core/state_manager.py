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

managed_rules = {}
state_lock = threading.RLock() 
logging.info(f"STATE_MANAGER_INIT: managed_rules object ID at module load: {id(managed_rules)}")

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
            
            for hostname, rule_data in loaded_data.items():
                rule_copy = rule_data.copy() 
                delete_at_val = rule_copy.get("delete_at")
                if isinstance(delete_at_val, str):
                    rule_copy["delete_at"] = _deserialize_datetime(delete_at_val)
                elif not isinstance(delete_at_val, (datetime, type(None))):
                    rule_copy["delete_at"] = None
                
                if "zone_id" not in rule_copy:
                    rule_copy["zone_id"] = None
                
                rule_copy.setdefault("access_app_id", None)
                rule_copy.setdefault("access_policy_type", None)
                rule_copy.setdefault("access_app_config_hash", None)
                rule_copy.setdefault("access_policy_ui_override", False)
                rule_copy.setdefault("source", "docker")
                rule_copy.setdefault("path", None)
                managed_rules[hostname] = rule_copy 
            
            logging.info(f"LOAD_STATE: Loaded {len(managed_rules)} rules. managed_rules ID after populating: {id(managed_rules)}")
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"LOAD_STATE: Error loading state from {config.STATE_FILE_PATH}: {e}. Starting fresh (already cleared).", exc_info=True)
        except Exception as e_load_unexp:
            logging.error(f"LOAD_STATE: Unexpected error loading state: {e_load_unexp}. Starting fresh (already cleared).", exc_info=True)

def save_state():
    global managed_rules
    current_thread_name = threading.current_thread().name
    
    with state_lock: 
        logging.info(f"SAVE_STATE: Start (RLock acquired). THREAD: {current_thread_name}. managed_rules item count: {len(managed_rules)}")
        
        serializable_state = {}
        rules_to_iterate_items = list(managed_rules.items()) 
    
    if not rules_to_iterate_items:
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. managed_rules is empty. Proceeding to write empty state file.")
    else:
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Serializing {len(rules_to_iterate_items)} rules.")

    for hostname, rule in rules_to_iterate_items:
        logging.debug(f"SAVE_STATE_LOOP: THREAD: {current_thread_name}. Preparing rule for hostname: {hostname}")
        try:
            data_to_serialize = {
                "service": rule.get("service"), "container_id": rule.get("container_id"),
                "status": rule.get("status"), "delete_at": None, 
                "zone_id": rule.get("zone_id"), "no_tls_verify": rule.get("no_tls_verify", False),
                "access_app_id": rule.get("access_app_id"), "access_policy_type": rule.get("access_policy_type"),
                "access_app_config_hash": rule.get("access_app_config_hash"),
                "access_policy_ui_override": rule.get("access_policy_ui_override", False),
                "source": rule.get("source", "docker"),
                "path": rule.get("path")
            }
            delete_at_val = rule.get("delete_at")
            if isinstance(delete_at_val, datetime): 
                logging.debug(f"SAVE_STATE_LOOP: THREAD: {current_thread_name}. Serializing datetime for {hostname} (value: {delete_at_val}).")
                data_to_serialize["delete_at"] = delete_at_val.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            serializable_state[hostname] = data_to_serialize
        except Exception as e_serialize_item:
            logging.error(f"SAVE_STATE_LOOP_ERROR: THREAD: {current_thread_name}. Error preparing rule for serialization '{hostname}': {e_serialize_item}. Rule data: {rule}", exc_info=True)
            continue
    
    logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Prepared serializable_state with {len(serializable_state)} items.")

    try:
        state_dir = os.path.dirname(config.STATE_FILE_PATH)
        if not os.path.exists(state_dir):
            try: os.makedirs(state_dir, exist_ok=True)
            except OSError as e_mkdir: logging.error(f"SAVE_STATE: THREAD: {current_thread_name}. Mkdir error {e_mkdir}. Save failed."); return
        temp_file_path = config.STATE_FILE_PATH + ".tmp"
        with open(temp_file_path, 'w') as f: json.dump(serializable_state, f, indent=2)
        os.replace(temp_file_path, config.STATE_FILE_PATH)
        logging.info(f"SAVE_STATE: THREAD: {current_thread_name}. Successfully saved state for {len(serializable_state)} rules to {config.STATE_FILE_PATH}")
    except Exception as e_save_io: 
        logging.error(f"SAVE_STATE: THREAD: {current_thread_name}. File I/O or other error: {e_save_io}", exc_info=True)
    
    logging.info(f"SAVE_STATE: End. THREAD: {current_thread_name}.")