# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev
#
# Licensed under the GPL v3 or later.
"""Helpers for reading and applying encrypted DockFlare configuration."""

import json
import logging
import os
from typing import Dict, Optional

from cryptography.fernet import Fernet

from app import config


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
    flask_app.config['DOCKFLARE_USERNAME'] = config_data.get('username')
    flask_app.config['DOCKFLARE_PASSWORD_HASH'] = config_data.get('password')
    flask_app.config['DISABLE_PASSWORD_LOGIN'] = config_data.get('disable_password_login', False)
    flask_app.config['MASTER_API_KEY'] = effective_master_key

    config.CF_API_TOKEN = flask_app.config['CF_API_TOKEN']
    config.CF_ACCOUNT_ID = flask_app.config['CF_ACCOUNT_ID']
    config.CF_ZONE_ID = flask_app.config['CF_ZONE_ID']
    config.TUNNEL_NAME = flask_app.config['TUNNEL_NAME']
    config.TUNNEL_DNS_SCAN_ZONE_NAMES = flask_app.config['TUNNEL_DNS_SCAN_ZONE_NAMES']
    config.GRACE_PERIOD_SECONDS = flask_app.config['GRACE_PERIOD_SECONDS']
    config.MASTER_API_KEY = effective_master_key

    if flask_app.config['CF_API_TOKEN']:
        config.CF_HEADERS['Authorization'] = f"Bearer {flask_app.config['CF_API_TOKEN']}"
    else:
        config.CF_HEADERS.pop('Authorization', None)

    flask_app.is_configured = True
    container_name = f"cloudflared-agent-{tunnel_name}" if tunnel_name else None
    flask_app.config['CLOUDFLARED_CONTAINER_NAME'] = container_name
    config.CLOUDFLARED_CONTAINER_NAME = container_name
