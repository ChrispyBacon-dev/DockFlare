import json
import logging
import os
import threading
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urlparse

log = logging.getLogger(__name__)


def _address_is_blocked(ip_text):
    try:
        addr = ipaddress.ip_address(ip_text)
    except ValueError:
        return True
    return (
        addr.is_private or addr.is_loopback or addr.is_link_local
        or addr.is_reserved or addr.is_multicast or addr.is_unspecified
    )


def validate_push_endpoint(endpoint):
    if not isinstance(endpoint, str) or not endpoint or len(endpoint) > 2048:
        raise ValueError("invalid push endpoint")
    parsed = urlparse(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname:
        raise ValueError("push endpoint must be a valid https URL")
    if parsed.username or parsed.password:
        raise ValueError("push endpoint must not contain credentials")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError("push endpoint host could not be resolved") from e
    if not infos:
        raise ValueError("push endpoint host could not be resolved")
    for info in infos:
        if _address_is_blocked(info[4][0]):
            raise ValueError("push endpoint resolves to a non-public address")
    return True


def send_push_notifications(mailbox_address: str, payload: dict):
    threading.Thread(
        target=_dispatch,
        args=(mailbox_address, payload),
        daemon=True,
    ).start()


def _get_private_key() -> str:
    private_key = os.environ.get('VAPID_PRIVATE_KEY', '')
    if not private_key:
        return ''
    if private_key.strip().startswith('-----'):
        from cryptography.hazmat.primitives.serialization import (
            load_pem_private_key, Encoding, PrivateFormat, NoEncryption
        )
        import base64
        key_obj = load_pem_private_key(private_key.encode(), password=None)
        der = key_obj.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
        return base64.urlsafe_b64encode(der).rstrip(b'=').decode()
    return private_key


def _send_one(sub: dict, private_key: str, push_payload: dict, mailbox_address: str):
    from pywebpush import webpush, WebPushException
    from app.core.database import get_standalone_db

    now_iso = datetime.now(timezone.utc).isoformat()
    db = get_standalone_db()
    try:
        validate_push_endpoint(sub['endpoint'])
    except ValueError as endpoint_error:
        try:
            db.execute("DELETE FROM push_subscriptions WHERE id=?", (sub['id'],))
            db.commit()
        except Exception:
            log.exception("Failed to delete invalid subscription %s", sub['id'])
        log.warning("Removed invalid push subscription %s: %s", sub['id'], endpoint_error)
        return
    try:
        webpush(
            subscription_info={
                "endpoint": sub['endpoint'],
                "keys": {"p256dh": sub['p256dh'], "auth": sub['auth']},
            },
            data=json.dumps(push_payload),
            vapid_private_key=private_key,
            vapid_claims={"sub": "mailto:push@dockflare.local"},
        )
        try:
            db.execute(
                "UPDATE push_subscriptions SET last_attempted_at=?, last_success_at=?, fail_count=0 WHERE id=?",
                (now_iso, now_iso, sub['id']),
            )
            db.commit()
        except Exception:
            log.exception("Failed to update tracking for subscription %s", sub['id'])
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            try:
                db.execute("DELETE FROM push_subscriptions WHERE id=?", (sub['id'],))
                db.commit()
                log.info("Removed stale push subscription for %s", mailbox_address)
            except Exception:
                log.exception("Failed to delete stale subscription %s", sub['id'])
        else:
            try:
                db.execute(
                    "UPDATE push_subscriptions SET last_attempted_at=?, fail_count=fail_count+1 WHERE id=?",
                    (now_iso, sub['id']),
                )
                db.commit()
            except Exception:
                log.exception("Failed to update fail_count for subscription %s", sub['id'])
            log.warning("Push failed for %s: %s", mailbox_address, e)
    except Exception:
        try:
            db.execute(
                "UPDATE push_subscriptions SET last_attempted_at=?, fail_count=fail_count+1 WHERE id=?",
                (now_iso, sub['id']),
            )
            db.commit()
        except Exception:
            log.exception("Failed to update fail_count for subscription %s", sub['id'])
        log.exception("Push network error for %s", mailbox_address)
    finally:
        db.close()


def _dispatch(mailbox_address: str, payload: dict):
    private_key = _get_private_key()
    if not private_key:
        return

    from app.core.database import get_standalone_db

    db = get_standalone_db()
    try:
        row = db.execute("""
            SELECT m.notification_preview,
                   (SELECT COUNT(*) FROM messages msg
                    JOIN folders f ON msg.folder_id = f.id
                    WHERE msg.mailbox_address = m.address AND f.name='Inbox'
                    AND msg.is_read=0 AND msg.is_draft=0) AS unread_count
            FROM mailboxes m WHERE m.address=?
        """, (mailbox_address,)).fetchone()

        unread_count = row['unread_count'] if row else 0
        preview = row['notification_preview'] if row and row['notification_preview'] is not None else 1

        push_payload = {
            'message_id': payload.get('message_id'),
            'mailbox': payload.get('mailbox'),
            'unread_count': unread_count,
        }
        if preview:
            push_payload['subject'] = payload.get('subject', '')
            push_payload['from_name'] = payload.get('from_name', '')

        subscriptions = list(db.execute(
            "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE mailbox_address=?",
            (mailbox_address,),
        ).fetchall())
    except Exception:
        log.exception("Push dispatch error for %s", mailbox_address)
        return
    finally:
        db.close()

    if not subscriptions:
        return

    max_workers = min(len(subscriptions), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for sub in subscriptions:
            executor.submit(_send_one, dict(sub), private_key, push_payload, mailbox_address)
