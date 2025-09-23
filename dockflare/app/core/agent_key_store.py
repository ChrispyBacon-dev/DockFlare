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
"""Encrypted persistence for agent API keys."""

import json
import logging
import os
import threading
from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken

from app import config

_store_lock = threading.RLock()
_cached_keys: Dict[str, Dict] = {}
_initialized = False


def _data_directory() -> str:
    return os.path.dirname(config.STATE_FILE_PATH)


def _store_path() -> str:
    custom_path = getattr(config, "AGENT_KEY_STORAGE_PATH", None)
    if custom_path:
        if os.path.isabs(custom_path):
            return custom_path
        return os.path.join(_data_directory(), custom_path)
    return os.path.join(_data_directory(), "agent_keys.dat")


def get_store_path() -> str:
    """Return the absolute path to the encrypted agent key store."""
    return _store_path()


def _fernet() -> Optional[Fernet]:
    key_file = os.path.join(_data_directory(), "dockflare.key")
    if not os.path.exists(key_file):
        logging.warning("AGENT_KEY_STORE: Encryption key file missing (%s).", key_file)
        return None
    try:
        with open(key_file, "rb") as fh:
            key_bytes = fh.read()
        return Fernet(key_bytes)
    except (OSError, ValueError) as err:
        logging.error("AGENT_KEY_STORE: Failed loading Fernet key: %s", err, exc_info=True)
        return None


def _persist_locked() -> None:
    fernet = _fernet()
    if fernet is None:
        logging.warning("AGENT_KEY_STORE: Persist skipped because Fernet key is unavailable.")
        return

    payload = {"keys": _cached_keys}
    try:
        serialized = json.dumps(payload).encode("utf-8")
        encrypted = fernet.encrypt(serialized)
        target_path = _store_path()
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        temp_path = f"{target_path}.tmp"
        with open(temp_path, "wb") as fh:
            fh.write(encrypted)
        os.replace(temp_path, target_path)
        logging.debug("AGENT_KEY_STORE: Persisted %d keys to encrypted store.", len(_cached_keys))
    except Exception as err:  # pylint: disable=broad-except
        logging.error("AGENT_KEY_STORE: Failed to persist key store: %s", err, exc_info=True)


def _load_locked() -> None:
    global _initialized
    fernet = _fernet()
    if fernet is None:
        _cached_keys.clear()
        _initialized = True
        return

    store_file = _store_path()
    if not os.path.exists(store_file):
        _cached_keys.clear()
        _initialized = True
        return

    try:
        with open(store_file, "rb") as fh:
            encrypted = fh.read()
        decrypted = fernet.decrypt(encrypted)
        payload = json.loads(decrypted.decode("utf-8"))
        keys = payload.get("keys", {}) if isinstance(payload, dict) else {}
        if not isinstance(keys, dict):
            raise ValueError("Invalid agent key store format: 'keys' is not a dict")
        _cached_keys.clear()
        _cached_keys.update(keys)
        logging.info("AGENT_KEY_STORE: Loaded %d keys from encrypted store.", len(_cached_keys))
    except (InvalidToken, ValueError) as err:
        logging.error("AGENT_KEY_STORE: Failed to decrypt key store: %s", err, exc_info=True)
        _cached_keys.clear()
    except Exception as err:  # pylint: disable=broad-except
        logging.error("AGENT_KEY_STORE: Unexpected error loading store: %s", err, exc_info=True)
        _cached_keys.clear()
    finally:
        _initialized = True


def _ensure_loaded() -> None:
    with _store_lock:
        if not _initialized:
            _load_locked()


def list_keys() -> Dict[str, Dict]:
    _ensure_loaded()
    with _store_lock:
        return {token: dict(meta) for token, meta in _cached_keys.items()}


def get_key(token: str) -> Optional[Dict]:
    if not token:
        return None
    _ensure_loaded()
    with _store_lock:
        entry = _cached_keys.get(token)
        return dict(entry) if isinstance(entry, dict) else None


def upsert_key(token: str, metadata: Optional[Dict] = None) -> None:
    if not token:
        raise ValueError("token is required")
    _ensure_loaded()
    with _store_lock:
        _cached_keys[token] = dict(metadata) if metadata else {}
        _persist_locked()


def remove_key(token: str) -> None:
    if not token:
        return
    _ensure_loaded()
    with _store_lock:
        if token in _cached_keys:
            del _cached_keys[token]
            _persist_locked()


def bulk_replace(keys: Dict[str, Dict]) -> None:
    if not isinstance(keys, dict):
        raise ValueError("keys must be a dict")
    _ensure_loaded()
    with _store_lock:
        _cached_keys.clear()
        for token, metadata in keys.items():
            if not isinstance(metadata, dict):
                logging.warning("AGENT_KEY_STORE: Skipping non-dict metadata for token %s", token)
                continue
            _cached_keys[token] = metadata
        _persist_locked()


def clear_store() -> None:
    _ensure_loaded()
    with _store_lock:
        _cached_keys.clear()
        _persist_locked()


def reload_store() -> None:
    """Force a reload from disk, discarding any cached state."""
    global _initialized
    with _store_lock:
        _initialized = False
    _ensure_loaded()
