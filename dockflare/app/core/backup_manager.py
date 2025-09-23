# DockFlare: Automates Cloudflare Tunnel ingress from Docker labels.
# Copyright (C) 2025 ChrispyBacon-Dev
#
# Licensed under the GPL v3 or later.
"""Utility helpers for creating and restoring DockFlare backup archives."""

import datetime as _dt
import hashlib
import io
import json
import logging
import os
import threading
import zipfile
from typing import BinaryIO, Dict, List, Tuple

from flask import current_app

from app import config
from app.core import agent_key_store

MANIFEST_NAME = "manifest.json"
MANIFEST_VERSION = 1
RESTART_FLAG_NAME = "restore-restart.flag"


def _data_directory() -> str:
    return os.path.dirname(config.STATE_FILE_PATH)


def _known_files() -> List[Tuple[str, str, bool]]:
    data_dir = _data_directory()
    return [
        ("dockflare.key", os.path.join(data_dir, "dockflare.key"), True),
        ("dockflare_config.dat", os.path.join(data_dir, "dockflare_config.dat"), True),
        ("state.json", config.STATE_FILE_PATH, False),
        ("agent_keys.dat", agent_key_store.get_store_path(), False),
    ]


def _hash_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def create_backup_archive() -> Tuple[io.BytesIO, str]:
    """
    Bundle DockFlare data files into an in-memory ZIP archive.

    Returns (buffer, suggested_filename).
    """
    buffer = io.BytesIO()
    manifest: Dict = {
        "schema": MANIFEST_VERSION,
        "generated_at": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "app_version": config.APP_VERSION,
        "files": []
    }

    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path, required in _known_files():
            if not os.path.exists(path):
                if required:
                    raise FileNotFoundError(f"Required file missing for backup: {path}")
                logging.info("BACKUP: Optional file '%s' not found; skipping.", name)
                continue

            with open(path, "rb") as fh:
                content = fh.read()
            archive.writestr(name, content)
            manifest["files"].append({
                "name": name,
                "sha256": _hash_bytes(content),
                "size": len(content),
                "required": required
            })

        archive.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2).encode("utf-8"))

    buffer.seek(0)
    timestamp = _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"dockflare_backup_{timestamp}.zip"
    return buffer, filename


class RestoreResult:
    """Simple container describing the outcome of a restore."""

    def __init__(self, *, mode: str, files_applied: List[str]):
        self.mode = mode
        self.files_applied = files_applied

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"RestoreResult(mode={self.mode!r}, files_applied={self.files_applied!r})"


def _write_file_atomic(target_path: str, payload: bytes) -> None:
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    temp_path = f"{target_path}.tmp"
    with open(temp_path, "wb") as fh:
        fh.write(payload)
    os.replace(temp_path, target_path)


def _apply_zip_backup(buffer: BinaryIO) -> RestoreResult:
    with zipfile.ZipFile(buffer, mode="r") as archive:
        if MANIFEST_NAME not in archive.namelist():
            raise ValueError("Backup archive missing manifest.json")
        manifest_data = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
        files_meta = manifest_data.get("files") or []
        applied: List[str] = []

        index = {name: path for name, path, _ in _known_files()}
        required_map = {name: required for name, _, required in _known_files()}

        for entry in files_meta:
            name = entry.get("name")
            if not name:
                continue
            required = entry.get("required", True)
            if required_map.get(name, required) and name not in archive.namelist():
                raise ValueError(f"Backup archive missing required file: {name}")

            if name not in archive.namelist():
                continue

            payload = archive.read(name)
            expected_hash = entry.get("sha256")
            if expected_hash and _hash_bytes(payload) != expected_hash:
                raise ValueError(f"Checksum mismatch for {name}")

            target = index.get(name)
            if not target:
                logging.warning("RESTORE: Unknown file '%s' in archive; skipping.", name)
                continue

            _write_file_atomic(target, payload)
            applied.append(name)

    return RestoreResult(mode="zip", files_applied=applied)


def _apply_legacy_state(payload: bytes) -> RestoreResult:
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as err:
        raise ValueError("Legacy state file is not valid JSON") from err

    if not isinstance(parsed, dict) or "managed_rules" not in parsed:
        raise ValueError("Legacy state file missing expected fields")

    _write_file_atomic(config.STATE_FILE_PATH, json.dumps(parsed, indent=2).encode("utf-8"))
    return RestoreResult(mode="legacy_state", files_applied=["state.json"])


def restore_backup(file_storage, *, allow_legacy_json: bool) -> RestoreResult:
    """
    Restore DockFlare data from an uploaded file-like object.
    """
    raw_bytes = file_storage.read()
    buffer = io.BytesIO(raw_bytes)
    buffer.seek(0)

    if zipfile.is_zipfile(buffer):
        buffer.seek(0)
        result = _apply_zip_backup(buffer)
        buffer.close()
        return result

    if allow_legacy_json:
        return _apply_legacy_state(raw_bytes)

    raise ValueError("Backup must be a DockFlare archive (.zip)")


def refresh_runtime_after_restore(result: RestoreResult) -> None:
    """Best-effort runtime refresh after files have been restored."""
    restart_required = False

    if "state.json" in result.files_applied:
        try:
            from app.core.state_manager import load_state

            load_state()
            logging.info("RESTORE: State file reloaded into memory.")
        except Exception as err:  # pylint: disable=broad-except
            logging.error("RESTORE: Failed to reload state: %s", err, exc_info=True)

    if "agent_keys.dat" in result.files_applied:
        try:
            agent_key_store.reload_store()
        except Exception as err:  # pylint: disable=broad-except
            logging.error("RESTORE: Failed to reload agent key store: %s", err, exc_info=True)

    if any(name in result.files_applied for name in ("dockflare_config.dat", "dockflare.key")):
        try:
            # When restoring config/key we need to ensure Flask config is refreshed if possible.
            from app.web import config_loader

            config_data = config_loader.load_encrypted_config()
            if config_data:
                config_loader.apply_config_to_app(current_app, config_data)
                restart_required = True
        except Exception as err:  # pylint: disable=broad-except
            logging.error("RESTORE: Failed to refresh application config: %s", err, exc_info=True)

    if restart_required:
        flag_path = os.path.join(_data_directory(), RESTART_FLAG_NAME)
        try:
            with open(flag_path, "w", encoding="utf-8") as fh:
                fh.write("restart_pending\n")
            logging.info("RESTORE: Created restart flag at %s", flag_path)
        except Exception as err:  # pylint: disable=broad-except
            logging.error("RESTORE: Failed to create restart flag: %s", err, exc_info=True)
        _schedule_process_exit()


def _schedule_process_exit(delay_seconds: float = 6.0) -> None:
    """Schedule a process exit to allow Docker to restart the container."""

    def _exit_process():
        try:
            logging.info("RESTORE: Exiting process to complete restore restart.")
        finally:
            os._exit(0)

    timer = threading.Timer(delay_seconds, _exit_process)
    timer.daemon = True
    timer.start()
