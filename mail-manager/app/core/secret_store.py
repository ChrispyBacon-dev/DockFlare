import base64
import hashlib
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import config

_PREFIX = "enc:v1:"
SECRET_COLUMNS = ("webhook_secret", "r2_secret_access_key", "outbound_auth_secret")


def _encryption_key():
    raw = (config.MAIL_SECRET_KEY or '').strip()
    if not raw:
        return None
    try:
        candidate = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        if len(candidate) == 32:
            return candidate
    except Exception:
        pass
    return hashlib.sha256(raw.encode('utf-8')).digest()


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt_value(value):
    if not value or not isinstance(value, str) or is_encrypted(value):
        return value
    key = _encryption_key()
    if key is None:
        logging.warning("MAIL_SECRET_KEY is not configured; a mail secret is being stored unencrypted")
        return value
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, value.encode('utf-8'), None)
    return _PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii')


def decrypt_value(value):
    if not is_encrypted(value):
        return value
    key = _encryption_key()
    if key is None:
        raise ValueError("Cannot decrypt a stored mail secret because MAIL_SECRET_KEY is not configured")
    try:
        blob = base64.urlsafe_b64decode(value[len(_PREFIX):])
        return AESGCM(key).decrypt(blob[:12], blob[12:], None).decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to decrypt a stored mail secret: {e}")
        raise ValueError("Stored mail secret could not be decrypted; check MAIL_SECRET_KEY") from e


def decrypt_domain_config(row):
    if row is None:
        return None
    data = dict(row)
    for column in SECRET_COLUMNS:
        if column in data:
            data[column] = decrypt_value(data[column])
    return data
