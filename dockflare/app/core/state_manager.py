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

# app/core/state_manager.py
import json
import logging
import os
import threading
import copy # For deepcopy in save_state logging if used
from datetime import datetime, timezone

from app import config

managed_rules = {}
state_lock = threading.Lock()
# Log the initial ID of managed_rules when the module is first loaded
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
                managed_rules[hostname] = rule_copy 
            
            logging.info(f"LOAD_STATE: Loaded {len(managed_rules)} rules. managed_rules ID after populating: {id(managed_rules)}")
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"LOAD_STATE: Error loading state from {config.STATE_FILE_PATH}: {e}. Starting fresh (already cleared).", exc_info=True)
        except Exception as e_load_unexp:
            logging.error(f"LOAD_STATE: Unexpected error loading state: {e_load_unexp}. Starting fresh (already cleared).", exc_info=True)


def save_state():
    global managed_rules # Ensures we are working with the module-level global
    logging.info(f"SAVE_STATE: Start. managed_rules object ID: {id(managed_rules)}, Current item count: {len(managed_rules)}")
    serializable_state = {}
    
    with state_lock: 
        rules_to_iterate = list(managed_rules.items()) 

    if not rules_to_iterate:
        logging.info("SAVE_STATE: managed_rules is empty. Nothing to serialize for state file.")
    else:
        logging.info(f"SAVE_STATE: Serializing {len(rules_to_iterate)} rules.")

    for hostname, rule in rules_to_iterate: 
        rule_copy_for_serialization = copy.deepcopy(rule) 
        delete_at_val = rule_copy_for_serialization.get("delete_at")
        if isinstance(delete_at_val, datetime):
            rule_copy_for_serialization["delete_at"] = delete_at_val.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        if "zone_id" not in rule_copy_for_serialization:
            rule_copy_for_serialization["zone_id"] = None
        
        rule_copy_for_serialization.setdefault("access_app_id", None)
        rule_copy_for_serialization.setdefault("access_policy_type", None)
        rule_copy_for_serialization.setdefault("access_app_config_hash", None)
        rule_copy_for_serialization.setdefault("access_policy_ui_override", False)
        rule_copy_for_serialization.setdefault("source", "docker")
            
        serializable_state[hostname] = rule_copy_for_serialization
    
    logging.info(f"SAVE_STATE: Prepared serializable_state with {len(serializable_state)} items. Sample: {str(dict(list(serializable_state.items())[:1]))}")

    try:
        # ... (rest of your file writing logic with .tmp and os.replace) ...
        state_dir = os.path.dirname(config.STATE_FILE_PATH)
        if not os.path.exists(state_dir):
            try: os.makedirs(state_dir, exist_ok=True); logging.info(f"SAVE_STATE: Created dir {state_dir}.")
            except OSError as e_mkdir: logging.error(f"SAVE_STATE: Could not create dir {state_dir}: {e_mkdir}. Save failed."); return

        temp_file_path = config.STATE_FILE_PATH + ".tmp"
        logging.info(f"SAVE_STATE: Writing to temp file: {temp_file_path}")
        with open(temp_file_path, 'w') as f:
            json.dump(serializable_state, f, indent=2)
        
        logging.info(f"SAVE_STATE: Replacing original state file. Original: {config.STATE_FILE_PATH}")
        os.replace(temp_file_path, config.STATE_FILE_PATH)
        logging.info(f"SAVE_STATE: Successfully saved state for {len(serializable_state)} rules to {config.STATE_FILE_PATH}")

    except (IOError, OSError) as e_io:
        logging.error(f"SAVE_STATE: IO/OS Error: {e_io}", exc_info=True)
    except TypeError as e_type: 
        logging.error(f"SAVE_STATE: TypeError during JSON serialization: {e_type}. Data sample: {str(serializable_state)[:500]}", exc_info=True)
    except Exception as e_save:
        logging.error(f"SAVE_STATE: Unexpected error: {e_save}", exc_info=True)