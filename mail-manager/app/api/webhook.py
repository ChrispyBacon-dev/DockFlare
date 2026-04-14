import hmac
import hashlib
import json
import os
import sqlite3
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from app.config import config
from app.core.database import get_db
from app.core.push import send_push_notifications
from app.core.r2_client import fetch_email_from_r2, delete_from_r2
from app.core.mime_parser import parse_eml

log = logging.getLogger(__name__)
webhook_bp = Blueprint('webhook', __name__)


def _get_domain_config(domain):
    db = get_db()
    cur = db.execute("SELECT * FROM domain_configs WHERE domain_name=?", (domain,))
    return cur.fetchone()


def _verify_signature(req, secret):
    signature = req.headers.get('X-DockFlare-Signature')
    if not signature or not secret:
        return False
    body = req.get_data()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


@webhook_bp.route('/inbound', methods=['POST'])
def inbound():
    if getattr(config, 'IN_MAINTENANCE', False):
        return jsonify({"error": "Service unavailable during maintenance"}), 503

    domain = request.headers.get('X-DockFlare-Domain', '').strip()

    if domain and domain != 'undefined':
        domain_cfg = _get_domain_config(domain)
        if domain_cfg is None:
            log.warning("Inbound webhook: unknown domain '%s'", domain)
            return jsonify({"error": "unknown domain"}), 401
        secret = domain_cfg['webhook_secret']
    else:
        cur = get_db().execute("SELECT webhook_secret FROM domain_configs LIMIT 1")
        row = cur.fetchone()
        secret = row['webhook_secret'] if row else config.WEBHOOK_SECRET
        domain_cfg = None

    if not _verify_signature(request, secret):
        return jsonify({"error": "invalid signature"}), 401

    data = request.json
    if not data:
        return jsonify({"error": "missing json body"}), 400

    r2_key = data.get('r2_key')
    if not r2_key:
        return jsonify({"error": "missing r2_key"}), 400

    msg_uuid = request.headers.get('X-DockFlare-Message-Id', '')
    log.info("Inbound webhook: message=%s domain=%s from=%s to=%s",
             msg_uuid, domain or 'legacy', data.get('from', ''), data.get('to', ''))

    try:
        eml_bytes = fetch_email_from_r2(r2_key, domain_cfg)
        parsed = parse_eml(eml_bytes)

        db = get_db()

        to_address = ''
        for addr in parsed['to_addresses']:
            cur = db.execute(
                "SELECT address FROM mailboxes WHERE address=?", (addr,)
            )
            if cur.fetchone():
                to_address = addr
                break

        if not to_address:
            log.info("Inbound ignored: no matching mailbox for %s",
                     parsed['to_addresses'])
            return jsonify({
                "status": "ignored",
                "reason": "unknown recipient",
            }), 200

        cur = db.execute(
            "SELECT id FROM folders WHERE mailbox_address=? AND name='Inbox'",
            (to_address,),
        )
        folder_row = cur.fetchone()
        folder_id = folder_row['id'] if folder_row else None

        now = datetime.now(timezone.utc).isoformat()

        cur = db.execute("""
            INSERT INTO messages (
                message_id, mailbox_address, folder_id, from_address, from_name,
                to_addresses, cc_addresses, bcc_addresses, subject, text_body,
                html_body, received_at, is_read, is_starred, is_draft,
                in_reply_to, reference_ids, size_bytes, has_attachments,
                headers_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?, ?, ?, ?)
        """, (
            parsed['message_id'], to_address, folder_id,
            parsed['from_address'], parsed['from_name'],
            json.dumps(parsed['to_addresses']),
            json.dumps(parsed['cc_addresses']),
            json.dumps(parsed['bcc_addresses']),
            parsed['subject'], parsed['text_body'], parsed['html_body'],
            parsed['received_at'], parsed['in_reply_to'],
            parsed['references'], data.get('size_bytes', 0),
            1 if parsed['attachments'] else 0,
            json.dumps(parsed['headers_json']), now,
        ))
        msg_id = cur.lastrowid

        for att in parsed['attachments']:
            att_dir = os.path.join(config.ATTACHMENTS_PATH, str(msg_id))
            os.makedirs(att_dir, exist_ok=True)
            safe_filename = att['filename'].replace('/', '_').replace('\\', '_')
            att_path = os.path.join(att_dir, safe_filename)
            with open(att_path, 'wb') as f:
                f.write(att['data'])

            db.execute("""
                INSERT INTO attachments (
                    message_id, filename, content_type, size_bytes,
                    storage_path, content_id, is_inline, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg_id, att['filename'], att['content_type'],
                att['size_bytes'], att_path, att['content_id'],
                att['is_inline'], now,
            ))

        db.commit()

        quota_row = db.execute(
            "SELECT quota_bytes FROM mailboxes WHERE address=?", (to_address,)
        ).fetchone()
        if quota_row and quota_row['quota_bytes'] and quota_row['quota_bytes'] > 0:
            used = db.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM messages WHERE mailbox_address=?",
                (to_address,),
            ).fetchone()[0]
            if used > quota_row['quota_bytes']:
                db.execute(
                    "UPDATE mailboxes SET quota_exceeded_count = quota_exceeded_count + 1 WHERE address=?",
                    (to_address,),
                )
                db.commit()
                log.warning("Quota exceeded for %s: %d bytes used / %d bytes limit", to_address, used, quota_row['quota_bytes'])

        send_push_notifications(to_address, {
            'message_id': msg_id,
            'subject': parsed['subject'],
            'from_name': parsed['from_name'] or parsed['from_address'],
            'mailbox': to_address,
        })
        delete_from_r2(r2_key, domain_cfg)

        log.info("Inbound delivered: message=%s to=%s db_id=%s",
                 msg_uuid, to_address, msg_id)
        return jsonify({"status": "success"})

    except sqlite3.IntegrityError:
        log.info("Inbound duplicate (already delivered): message=%s — cleaning R2", msg_uuid)
        try:
            delete_from_r2(r2_key, domain_cfg)
        except Exception:
            pass
        return jsonify({"status": "already_delivered"}), 200

    except Exception as e:
        log.exception("Inbound webhook failed: message=%s", msg_uuid)
        return jsonify({"error": str(e)}), 500
