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
# app/core/utils.py

from app import config

def get_rule_key(hostname, path):
    # ... (this function remains the same)
    path_str = str(path or "").strip()
    return f"{hostname}|{path_str}"

def get_label(labels, key_suffix, default=None):
    """
    Gets a label value by checking prefixes in a specific order:
    1. User-defined custom prefix (from LABEL_PREFIX env var)
    2. The new 'dockflare.' prefix
    3. The legacy 'cloudflare.tunnel.' prefix
    
    Args:
        labels (dict): The dictionary of container labels.
        key_suffix (str): The part of the label after the prefix (e.g., 'enable', '0.hostname').
        default: The value to return if no label is found.

    Returns:
        The value of the found label or the default.
    """
    # 1. Check for a user-defined custom prefix first.
    if config.CUSTOM_LABEL_PREFIX:
        custom_key = f"{config.CUSTOM_LABEL_PREFIX.rstrip('.')}.{key_suffix}"
        if custom_key in labels:
            return labels[custom_key]

    # 2. Check for the new, primary prefix.
    primary_key = f"{config.PRIMARY_LABEL_PREFIX}{key_suffix}"
    if primary_key in labels:
        return labels[primary_key]

    # 3. Fall back to the legacy prefix.
    legacy_key = f"{config.LEGACY_LABEL_PREFIX}{key_suffix}"
    if legacy_key in labels:
        return labels[legacy_key]

    # 4. If nothing is found, return the default.
    return default