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
from datetime import datetime, timezone

from app import config

managed_rules = {}
state_lock = threading.Lock()

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
    global managed_rules
    state_dir = os.path.dirname(config.STATE_FILE_PATH)
    if not os.path.exists(state_dir):
        try:
            os.makedirs(state_dir, exist_ok=True)
            logging.info(f"Created directory for state file: {state_dir}")
        except OSError as e:
            logging.error(f"FATAL: Could not create directory for state file {state_dir}: {e}. State persistence will fail.")
            managed_rules = {}
            return

    if not os.path.exists(config.STATE_FILE_PATH):
        logging.info(f"State file '{config.STATE_FILE_PATH}' not found, starting fresh.")
        managed_rules = {}
        return

    with state_lock:
        try:
            with open(config.STATE_FILE_PATH, 'r') as f:
                loaded_data = json.load(f)
            
            processed_rules = {}
            for hostname, rule in loaded_data.items():
                rule_copy = rule.copy()
                delete_at_val = rule_copy.get("delete_at")
                if isinstance(delete_at_val, str):
                    rule_copy["delete_at"] = _deserialize_datetime(delete_at_val)
                elif not isinstance(delete_at_val, (datetime, type(None))):
                    logging.warning(f"Invalid type for delete_at for {hostname}: {type(delete_at_val)}. Setting to None.")
                    rule_copy["delete_at"] = None
                
                if "zone_id" not in rule_copy:
                    logging.warning(f"Rule for {hostname} loaded from state is missing 'zone_id'. Will attempt to re-determine on reconcile.")
                    rule_copy["zone_id"] = None
                
                rule_copy.setdefault("access_app_id", None)
                rule_copy.setdefault("access_policy_type", None)
                rule_copy.setdefault("access_app_config_hash", None)
                rule_copy.setdefault("access_policy_ui_override", False)
                rule_copy.setdefault("source", "docker")
                processed_rules[hostname] = rule_copy
            
            managed_rules = processed_rules
            logging.info(f"Loaded state for {len(managed_rules)} rules from {config.STATE_FILE_PATH}")
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.error(f"Error loading state from {config.STATE_FILE_PATH}: {e}. Starting fresh.", exc_info=True)
            managed_rules = {}
        except Exception as e:
            logging.error(f"Unexpected error during state loading from {config.STATE_FILE_PATH}: {e}. Starting fresh.", exc_info=True)
            managed_rules = {}


def save_state():
    global managed_rules
    serializable_state = {}
    
    with state_lock:
        for hostname, rule in managed_rules.items():
            rule_copy = rule.copy()
            delete_at_val = rule_copy.get("delete_at")
            if isinstance(delete_at_val, datetime):
                rule_copy["delete_at"] = delete_at_val.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            
            if "zone_id" not in rule_copy:
                logging.warning(f"Attempting to save rule for {hostname} without zone_id!")
                rule_copy["zone_id"] = None
            
            rule_copy.setdefault("access_app_id", None)
            rule_copy.setdefault("access_policy_type", None)
            rule_copy.setdefault("access_app_config_hash", None)
            rule_copy.setdefault("access_policy_ui_override", False)
            rule_copy.setdefault("source", "docker")
            
            serializable_state[hostname] = rule_copy

    try:
        state_dir = os.path.dirname(config.STATE_FILE_PATH)
        if not os.path.exists(state_dir):
            try:
                os.makedirs(state_dir, exist_ok=True)
                logging.info(f"Created directory {state_dir} before saving state.")
            except OSError as e:
                logging.error(f"Could not create directory {state_dir} for state file: {e}. Save failed.")
                return

        temp_file_path = config.STATE_FILE_PATH + ".tmp"
        with open(temp_file_path, 'w') as f:
            json.dump(serializable_state, f, indent=2)
        os.replace(temp_file_path, config.STATE_FILE_PATH)
        logging.debug(f"Saved state for {len(managed_rules)} rules to {config.STATE_FILE_PATH}")
    except (IOError, OSError) as e:
        logging.error(f"Error saving state to {config.STATE_FILE_PATH}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error during state saving to {config.STATE_FILE_PATH}: {e}", exc_info=True)