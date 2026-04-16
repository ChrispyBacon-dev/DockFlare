import email as _email_lib
import hmac
import hashlib
import json
import os
import shutil
import sqlite3
import logging
import uuid
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
import requests as _http_requests
from app.config import config
from app.core.database import get_db
from app.core.push import send_push_notifications
from app.core.r2_client import fetch_email_from_r2, delete_from_r2
from app.core.mime_parser import parse_eml
from app.core.bounce_handler import log_bounce

log = logging.getLogger(__name__)
webhook_bp = Blueprint('webhook', __name__)


def _fmt_bytes(n):
    if n >= 1073741824:
        return f"{n / 1073741824:.1f} GB"
    if n >= 1048576:
        return f"{n / 1048576:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


def _detect_and_log_bounce(eml_bytes, parsed):
    from_addr = (parsed.get('from_address') or '').lower()
    headers = {}
    for h in parsed.get('headers_json', []):
        for k, v in h.items():
            headers[k.lower()] = v

    content_type = headers.get('content-type', '').lower()
    is_dsn = 'multipart/report' in content_type and 'delivery-status' in content_type
    is_mailer_daemon = 'mailer-daemon' in from_addr or (not from_addr and is_dsn)

    if not (is_dsn or is_mailer_daemon):
        return

    msg = _email_lib.message_from_bytes(eml_bytes)
    original_message_id = parsed.get('in_reply_to') or ''
    bounce_type = 'permanent'
    recipient = ''
    reason = ''

    for part in msg.walk():
        if part.get_content_type() == 'message/delivery-status':
            try:
                payload = part.get_payload(decode=False)
                if isinstance(payload, list):
                    dsn_text = '\n'.join(
                        p.as_string() if hasattr(p, 'as_string') else str(p)
                        for p in payload
                    )
                else:
                    dsn_text = str(payload or '')
                for line in dsn_text.splitlines():
                    if ':' not in line:
                        continue
                    key, _, val = line.partition(':')
                    key = key.strip().lower()
                    val = val.strip()
                    if key == 'final-recipient' and not recipient:
                        parts = val.split(';')
                        recipient = parts[-1].strip() if len(parts) > 1 else val
                    elif key == 'status':
                        bounce_type = 'temporary' if val.startswith('4.') else 'permanent'
                    elif key == 'diagnostic-code' and not reason:
                        reason = val.split(';', 1)[-1].strip() if ';' in val else val
                    elif key == 'original-message-id' and not original_message_id:
                        original_message_id = val.strip('<>')
            except Exception:
                pass

    if not recipient:
        recipient = ', '.join(parsed.get('to_addresses', []))
    if not reason:
        reason = (parsed.get('subject') or '').strip()

    try:
        log_bounce(original_message_id, bounce_type, recipient, reason)
    except Exception:
        log.warning("bounce_log write failed for message_id=%s", original_message_id)


def _check_and_send_auto_reply(db, mailbox_address, parsed, domain_cfg):
    from_addr = (parsed.get('from_address') or '').strip()
    if not from_addr or 'mailer-daemon' in from_addr.lower():
        return
    headers = {}
    for h in parsed.get('headers_json', []):
        for k, v in h.items():
            headers[k.lower()] = v
    auto_submitted = headers.get('auto-submitted', '').lower()
    if auto_submitted and auto_submitted != 'no':
        return
    precedence = headers.get('precedence', '').lower()
    if 'bulk' in precedence or 'list' in precedence or headers.get('list-id'):
        return
    row = db.execute(
        "SELECT * FROM auto_responders WHERE mailbox_address=? AND is_active=1",
        (mailbox_address,),
    ).fetchone()
    if not row:
        return
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    if row['start_date'] and now_iso < row['start_date']:
        return
    if row['end_date'] and now_iso > row['end_date'] + 'T23:59:59':
        return
    cutoff = (now - timedelta(hours=row['reply_interval_hours'])).isoformat()
    if db.execute(
        "SELECT 1 FROM auto_reply_log WHERE mailbox_address=? AND original_sender=? AND replied_at > ?",
        (mailbox_address, from_addr, cutoff),
    ).fetchone():
        return
    outbound_url = domain_cfg['outbound_worker_url'] if domain_cfg else None
    outbound_auth = domain_cfg['outbound_auth_secret'] if domain_cfg else None
    if not outbound_url:
        return
    msg_id = f"<auto-reply-{uuid.uuid4()}@dockflare>"
    original_subject = parsed.get('subject') or ''
    worker_payload = {
        "from": mailbox_address,
        "to": [from_addr],
        "subject": f"Auto Reply: {original_subject}",
        "text": f"{row['message_body']}\n\n---\nThis is an automated reply.",
        "messageId": msg_id,
        "inReplyTo": parsed.get('message_id') or '',
        "references": parsed.get('message_id') or '',
    }
    try:
        resp = _http_requests.post(
            outbound_url,
            json=worker_payload,
            headers={"Authorization": f"Bearer {outbound_auth}"},
            timeout=15,
        )
        if resp.ok:
            db.execute(
                "INSERT INTO auto_reply_log (mailbox_address, original_sender, original_message_id, replied_at) VALUES (?, ?, ?, ?)",
                (mailbox_address, from_addr, parsed.get('message_id') or '', now_iso),
            )
            db.commit()
    except Exception:
        log.warning("Auto-reply send failed for %s -> %s", mailbox_address, from_addr)


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

        if not to_address and domain_cfg and domain_cfg['catch_all_mailbox']:
            catch_all = domain_cfg['catch_all_mailbox']
            if db.execute("SELECT 1 FROM mailboxes WHERE address=?", (catch_all,)).fetchone():
                to_address = catch_all

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

        actual_size = sum(len(att['data']) for att in parsed['attachments'])
        if parsed.get('text_body'):
            actual_size += len(parsed['text_body'].encode('utf-8'))
        if parsed.get('html_body'):
            actual_size += len(parsed['html_body'].encode('utf-8'))

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
            parsed['references'], actual_size,
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

        _detect_and_log_bounce(eml_bytes, parsed)

        quota_row = db.execute(
            """SELECT m.quota_bytes, m.last_quota_warning_at, d.grace_buffer_bytes
               FROM mailboxes m
               LEFT JOIN domain_configs d ON d.domain_name = m.domain
               WHERE m.address = ?""",
            (to_address,)
        ).fetchone()

        if quota_row and quota_row['quota_bytes'] and quota_row['quota_bytes'] > 0:
            quota = quota_row['quota_bytes']
            raw_buffer = quota_row['grace_buffer_bytes']
            grace = raw_buffer if raw_buffer else max(int(quota * 0.15), 10 * 1024 * 1024)
            hard_limit = quota + grace

            used = db.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM messages WHERE mailbox_address=? AND is_system=0",
                (to_address,),
            ).fetchone()[0]

            if used > quota:
                db.execute(
                    "UPDATE mailboxes SET quota_exceeded_count = quota_exceeded_count + 1 WHERE address=?",
                    (to_address,),
                )
                log.warning("Quota exceeded for %s: %s used / %s limit", to_address, _fmt_bytes(used), _fmt_bytes(quota))

                if not quota_row['last_quota_warning_at']:
                    inbox = db.execute(
                        "SELECT id FROM folders WHERE mailbox_address=? AND name='Inbox'",
                        (to_address,)
                    ).fetchone()
                    if inbox:
                        db.execute("""
                            INSERT INTO messages (
                                message_id, mailbox_address, folder_id,
                                from_address, from_name, to_addresses,
                                cc_addresses, bcc_addresses, subject,
                                text_body, html_body, received_at,
                                is_read, is_starred, is_draft,
                                in_reply_to, reference_ids, size_bytes,
                                has_attachments, headers_json, created_at, is_system
                            ) VALUES (?, ?, ?, 'noreply@dockflare', 'DockFlare System', ?,
                                '[]', '[]',
                                'Action Required: Your mailbox is nearly full',
                                ?, '', ?, 0, 0, 0, NULL, NULL, 0, 0, '{}', ?, 1)
                        """, (
                            f"quota-warning-{to_address}-{now}",
                            to_address,
                            inbox['id'],
                            f'["{to_address}"]',
                            (
                                f"Your mailbox ({to_address}) has reached its storage quota "
                                f"({_fmt_bytes(quota)}). You have a grace buffer of "
                                f"{_fmt_bytes(grace)} before new emails are rejected.\n\n"
                                f"Current usage: {_fmt_bytes(used)}\n"
                                f"Soft limit:    {_fmt_bytes(quota)}\n"
                                f"Hard limit:    {_fmt_bytes(hard_limit)}\n\n"
                                f"Please delete old messages or contact your administrator "
                                f"to increase your quota."
                            ),
                            now, now,
                        ))
                    db.execute(
                        "UPDATE mailboxes SET last_quota_warning_at=? WHERE address=?",
                        (now, to_address)
                    )

            elif used < quota * 0.90 and quota_row['last_quota_warning_at']:
                db.execute(
                    "UPDATE mailboxes SET last_quota_warning_at=NULL WHERE address=?",
                    (to_address,)
                )

            db.commit()

            if used > hard_limit:
                att_dir = os.path.join(config.ATTACHMENTS_PATH, str(msg_id))
                if os.path.isdir(att_dir):
                    shutil.rmtree(att_dir, ignore_errors=True)
                db.execute("DELETE FROM messages WHERE id=?", (msg_id,))
                db.commit()
                log.warning(
                    "Hard quota exceeded for %s: %s used / %s hard limit — message %d rejected",
                    to_address, _fmt_bytes(used), _fmt_bytes(hard_limit), msg_id
                )
                try:
                    delete_from_r2(r2_key, domain_cfg)
                except Exception:
                    pass
                master_url = os.environ.get('DOCKFLARE_MASTER_URL', '').rstrip('/')
                if master_url:
                    try:
                        _http_requests.post(
                            f"{master_url}/email/internal/quota-kv-sync",
                            json={'domain': to_address.split('@')[1], 'address': to_address, 'action': 'block'},
                            headers={'X-Bootstrap-Token': os.environ.get('INTERNAL_BOOTSTRAP_SECRET', '')},
                            timeout=3,
                        )
                    except Exception:
                        pass
                return jsonify({"status": "rejected", "reason": "over_hard_quota"}), 200

        send_push_notifications(to_address, {
            'message_id': msg_id,
            'subject': parsed['subject'],
            'from_name': parsed['from_name'] or parsed['from_address'],
            'mailbox': to_address,
        })
        _check_and_send_auto_reply(db, to_address, parsed, domain_cfg)

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
