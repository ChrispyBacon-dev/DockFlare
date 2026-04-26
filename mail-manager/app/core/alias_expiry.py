import logging
import os
from datetime import datetime, timezone

import requests as http_requests

log = logging.getLogger(__name__)


def _sync_alias_kv_delete(alias_address):
    master_url = os.environ.get('DOCKFLARE_MASTER_URL', '').rstrip('/')
    if not master_url:
        return
    try:
        http_requests.post(
            f"{master_url}/email/internal/alias-kv-sync",
            json={
                "domain": alias_address.split('@')[1],
                "alias_address": alias_address,
                "action": "delete",
            },
            headers={"X-Bootstrap-Token": os.environ.get("INTERNAL_BOOTSTRAP_SECRET", "")},
            timeout=5,
        )
    except Exception:
        log.error("alias-kv-sync delete failed during expiry for %s", alias_address)


def _insert_expiry_message(db, mailbox_address, alias_address, now):
    inbox = db.execute(
        "SELECT id FROM folders WHERE mailbox_address=? AND name='Inbox'",
        (mailbox_address,)
    ).fetchone()
    if not inbox:
        return
    alias_row = db.execute(
        "SELECT use_count FROM aliases WHERE address=?", (alias_address,)
    ).fetchone()
    if not alias_row or alias_row['use_count'] == 0:
        return
    db.execute("""
        INSERT OR IGNORE INTO messages (
            message_id, mailbox_address, folder_id,
            from_address, from_name, to_addresses,
            cc_addresses, bcc_addresses, subject,
            text_body, html_body, received_at,
            is_read, is_starred, is_draft,
            in_reply_to, reference_ids, size_bytes,
            has_attachments, headers_json, created_at, is_system
        ) VALUES (?, ?, ?, 'noreply@dockflare', 'DockFlare System', ?,
            '[]', '[]',
            ?, ?, '', ?, 0, 0, 0,
            NULL, NULL, 0, 0, '{}', ?, 1)
    """, (
        f"alias-expired-{alias_address}-{now}",
        mailbox_address,
        inbox['id'],
        f'["{mailbox_address}"]',
        f"Alias expired: {alias_address}",
        f"The alias {alias_address} has reached its expiration date and is no longer active.\n\n"
        f"Emails sent to this address will no longer be delivered to your mailbox.",
        now,
        now,
    ))


def expire_aliases():
    from app.core.database import get_standalone_db

    db = get_standalone_db()
    try:
        now = datetime.now(timezone.utc).isoformat()
        expired = db.execute(
            "SELECT address, mailbox_address FROM aliases "
            "WHERE is_active=1 AND expires_at IS NOT NULL AND expires_at < ?",
            (now,)
        ).fetchall()

        if not expired:
            return

        for alias in expired:
            db.execute("UPDATE aliases SET is_active=0 WHERE address=?", (alias['address'],))
            _sync_alias_kv_delete(alias['address'])
            _insert_expiry_message(db, alias['mailbox_address'], alias['address'], now)
            log.info("Alias expired: %s -> %s", alias['address'], alias['mailbox_address'])

        db.commit()
    except Exception:
        log.exception("alias expiry: unhandled error")
    finally:
        db.close()
