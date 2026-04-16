# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev <https://github.com/ChrispyBacon-dev/DockFlare>
#
# This program is free software: you can redistribute and/or modify
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
# dockflare/app/core/migration_service.py
"""Helpers for reading and applying encrypted DockFlare configuration."""

import json
import logging
import os
from typing import Dict, Optional

from cryptography.fernet import Fernet

from app import config
from app.core.container_name import build_cloudflared_container_name


def _data_directory() -> str:
    return os.path.dirname(config.STATE_FILE_PATH)


def config_file_path() -> str:
    return os.path.join(_data_directory(), "dockflare_config.dat")


def key_file_path() -> str:
    return os.path.join(_data_directory(), "dockflare.key")


def load_encrypted_config_with_cipher():
    """Return (config_data, Fernet instance) tuple or (None, None) if unavailable."""
    key_path = key_file_path()
    cfg_path = config_file_path()
    if not os.path.exists(key_path) or not os.path.exists(cfg_path):
        return None, None

    try:
        with open(key_path, "rb") as fh:
            key_material = fh.read()
        fernet = Fernet(key_material)
        with open(cfg_path, "rb") as fh:
            decrypted = fernet.decrypt(fh.read())
        payload = json.loads(decrypted.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Configuration payload is not a JSON object")
        return payload, fernet
    except Exception as err:  # pylint: disable=broad-except
        logging.error("CONFIG_LOADER: Failed to load encrypted config: %s", err, exc_info=True)
        return None, None


def load_encrypted_config() -> Optional[Dict]:
    data, _ = load_encrypted_config_with_cipher()
    return data


def apply_config_to_app(flask_app, config_data: Dict) -> None:
    """Populate Flask app and module-level config values from decrypted data."""
    if not isinstance(config_data, dict):
        raise ValueError("config_data must be a dict")

    master_key_env = os.getenv('DOCKFLARE_API_KEY')
    master_key_existing = config_data.get('master_api_key')
    effective_master_key = master_key_env or master_key_existing

    flask_app.config['CF_API_TOKEN'] = config_data.get('cf_api_token')
    flask_app.config['CF_ACCOUNT_ID'] = config_data.get('cf_account_id')
    tunnel_name = config_data.get('tunnel_name')
    flask_app.config['TUNNEL_NAME'] = tunnel_name
    flask_app.config['CF_ZONE_ID'] = config_data.get('cf_zone_id')

    tunnel_dns_scan_zone_names_str = config_data.get('tunnel_dns_scan_zone_names', '') or ''
    flask_app.config['TUNNEL_DNS_SCAN_ZONE_NAMES'] = [
        name.strip() for name in tunnel_dns_scan_zone_names_str.split(',') if name and name.strip()
    ]

    flask_app.config['GRACE_PERIOD_SECONDS'] = int(config_data.get('grace_period_seconds', 28800))
    flask_app.config['PRESERVE_UNMANAGED_CF_INGRESS_FIELDS'] = bool(config_data.get('preserve_unmanaged_cf_ingress_fields', False))
    flask_app.config['DOCKFLARE_USERNAME'] = config_data.get('username')
    flask_app.config['DOCKFLARE_PASSWORD_HASH'] = config_data.get('password')
    disable_password_login_legacy = config_data.get('disable_password_login')
    flask_app.config['MASTER_API_KEY'] = effective_master_key

    auth_settings = config_data.get('auth_settings', {})
    password_login_enabled = auth_settings.get('password_login_enabled')
    if password_login_enabled is not None:
        flask_app.config['DISABLE_PASSWORD_LOGIN'] = not bool(password_login_enabled)
    elif disable_password_login_legacy is not None:
        flask_app.config['DISABLE_PASSWORD_LOGIN'] = bool(disable_password_login_legacy)
    else:
        flask_app.config['DISABLE_PASSWORD_LOGIN'] = False

    flask_app.config['OAUTH_PROVIDERS'] = config_data.get('auth_providers', [])
    flask_app.config['OAUTH_AUTHORIZED_USERS'] = [
        user['email'] for user in config_data.get('authorized_users', [])
    ]

    flask_app.config['OAUTH_AUDIT_ENABLED'] = config_data.get('oauth_audit_enabled', True)
    oauth_settings = config_data.get('oauth_settings', {})
    flask_app.config['OAUTH_SESSION_TIMEOUT'] = oauth_settings.get('session_timeout', 86400)
    flask_app.config['OAUTH_MAX_LOGIN_ATTEMPTS'] = oauth_settings.get('max_login_attempts', 5)

    public_url_stored = config_data.get('dockflare_public_url', '')
    public_url_env = os.getenv('DOCKFLARE_PUBLIC_URL', '')
    effective_public_url = public_url_env or public_url_stored
    flask_app.config['DOCKFLARE_PUBLIC_URL'] = effective_public_url

    config.CF_API_TOKEN = flask_app.config['CF_API_TOKEN']
    config.CF_ACCOUNT_ID = flask_app.config['CF_ACCOUNT_ID']
    config.CF_ZONE_ID = flask_app.config['CF_ZONE_ID']
    config.TUNNEL_NAME = flask_app.config['TUNNEL_NAME']
    config.TUNNEL_DNS_SCAN_ZONE_NAMES = flask_app.config['TUNNEL_DNS_SCAN_ZONE_NAMES']
    config.GRACE_PERIOD_SECONDS = flask_app.config['GRACE_PERIOD_SECONDS']
    config.PRESERVE_UNMANAGED_CF_INGRESS_FIELDS = flask_app.config['PRESERVE_UNMANAGED_CF_INGRESS_FIELDS']
    config.MASTER_API_KEY = effective_master_key
    config.DOCKFLARE_PUBLIC_URL = effective_public_url

    email_config = config_data.get('email_config', {})
    flask_app.config['EMAIL_ENABLED'] = email_config.get('enabled', False)
    flask_app.config['EMAIL_CONFIG'] = email_config
    config.EMAIL_ENABLED = flask_app.config['EMAIL_ENABLED']
    config.EMAIL_CONFIG = flask_app.config['EMAIL_CONFIG']

    if flask_app.config['CF_API_TOKEN']:
        config.CF_HEADERS['Authorization'] = f"Bearer {flask_app.config['CF_API_TOKEN']}"
    else:
        config.CF_HEADERS.pop('Authorization', None)

    flask_app.is_configured = True
    container_name = build_cloudflared_container_name(tunnel_name)
    flask_app.config['CLOUDFLARED_CONTAINER_NAME'] = container_name
    config.CLOUDFLARED_CONTAINER_NAME = container_name
