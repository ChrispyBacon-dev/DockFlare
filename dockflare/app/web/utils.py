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
# /app/web/utils.py
from app import config

def get_rule_key(hostname, path):
    path_str = str(path or "").strip()
    return f"{hostname}|{path_str}"

def get_label(labels, key_suffix, default=None):
    if config.CUSTOM_LABEL_PREFIX:
        custom_key = f"{config.CUSTOM_LABEL_PREFIX.rstrip('.')}.{key_suffix}"
        if custom_key in labels:
            return labels[custom_key]

    primary_key = f"{config.PRIMARY_LABEL_PREFIX}{key_suffix}"
    if primary_key in labels:
        return labels[primary_key]

    legacy_key = f"{config.LEGACY_LABEL_PREFIX}{key_suffix}"
    if legacy_key in labels:
        return labels[legacy_key]

    return default