import base64
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

import requests as http_requests
from flask import Blueprint, request, jsonify, send_file

from app.config import config
from app.core.database import get_db
from app.api.middleware import jwt_required, admin_required
from app.core.rate_limiter import limiter

log = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_MAX_BODY_LEN = 1_000_000


def _paginated(items, total, page, per_page):
    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    })


def _check_mailbox_access(address):
    if request.user.get('role') == 'admin':
        return True
    return address in request.user.get('mailboxes', [])


@api_bp.route('/stats', methods=['GET'])
@admin_required
def stats():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT COUNT(*) FROM messages")
    total_messages = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM messages WHERE is_read=0")
    unread_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM send_log")
    total_sent = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mailboxes")
    mailbox_count = cur.fetchone()[0]
    return jsonify({
        "total_messages": total_messages,
        "unread_count": unread_count,
        "total_sent": total_sent,
        "mailbox_count": mailbox_count,
    })


@api_bp.route('/mailboxes', methods=['GET'])
@admin_required
def get_mailboxes():
    db = get_db()
    cur = db.execute("SELECT * FROM mailboxes")
    return jsonify([dict(row) for row in cur.fetchall()])


@api_bp.route('/mailboxes', methods=['POST'])
@admin_required
def create_mailbox():
    data = request.json or {}
    address = data.get('address', '')
    domain = data.get('domain', '')
    if not address or not domain:
        return jsonify({"error": "address and domain are required"}), 400
    if not _EMAIL_RE.match(address):
        return jsonify({"error": "invalid email address format"}), 400

    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        db.execute(
            "INSERT INTO mailboxes (address, display_name, domain, created_at, is_active) VALUES (?, ?, ?, ?, ?)",
            (address, data.get('display_name', ''), domain, now, 1),
        )
        for folder in ['Inbox', 'Sent', 'Drafts', 'Trash', 'Spam']:
            db.execute(
                "INSERT INTO folders (mailbox_address, name, system_folder, created_at) VALUES (?, ?, 1, ?)",
                (address, folder, now),
            )
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    return jsonify({"status": "created"}), 201


@api_bp.route('/mailboxes/<address>', methods=['GET'])
@admin_required
def get_mailbox(address):
    db = get_db()
    cur = db.execute("SELECT * FROM mailboxes WHERE address=?", (address,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@api_bp.route('/mailboxes/<address>', methods=['DELETE'])
@admin_required
def delete_mailbox(address):
    db = get_db()
    db.execute("DELETE FROM mailboxes WHERE address=?", (address,))
    db.commit()
    return jsonify({"status": "deleted"})


@api_bp.route('/mailboxes/<address>', methods=['PATCH'])
@admin_required
def patch_mailbox(address):
    data = request.json or {}
    if 'display_name' in data:
        db = get_db()
        db.execute(
            "UPDATE mailboxes SET display_name=? WHERE address=?",
            (data['display_name'], address),
        )
        db.commit()
    return jsonify({"status": "updated"})


@api_bp.route('/mailboxes/<address>/messages', methods=['GET'])
@jwt_required
def get_messages(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    folder = request.args.get('folder', 'Inbox')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(1, int(request.args.get('per_page', 50))))
    offset = (page - 1) * per_page

    _SORT_COLS = {'received_at', 'sent_at', 'subject', 'from_address'}
    sort_col = request.args.get('sort', 'default')
    order = 'ASC' if request.args.get('order', 'desc').lower() == 'asc' else 'DESC'

    if sort_col not in _SORT_COLS:
        sort_expr = "COALESCE(sent_at, received_at, created_at)"
    else:
        sort_expr = sort_col

    db = get_db()
    cur = db.execute(
        "SELECT id FROM folders WHERE mailbox_address=? AND name=?",
        (address, folder),
    )
    folder_row = cur.fetchone()
    if not folder_row:
        return jsonify({"error": "folder not found"}), 404

    folder_id = folder_row['id']

    cur = db.execute(
        "SELECT COUNT(*) FROM messages WHERE folder_id=?", (folder_id,)
    )
    total = cur.fetchone()[0]

    cur = db.execute(
        f"SELECT * FROM messages WHERE folder_id=? ORDER BY {sort_expr} {order} LIMIT ? OFFSET ?",
        (folder_id, per_page, offset),
    )
    msgs = [dict(row) for row in cur.fetchall()]
    return _paginated(msgs, total, page, per_page)


@api_bp.route('/mailboxes/<address>/messages/<int:msg_id>', methods=['GET'])
@jwt_required
def get_message(address, msg_id):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT * FROM messages WHERE id=? AND mailbox_address=?",
        (msg_id, address),
    )
    msg = cur.fetchone()
    if not msg:
        return jsonify({"error": "not found"}), 404

    res = dict(msg)
    cur = db.execute("SELECT * FROM attachments WHERE message_id=?", (msg_id,))
    res['attachments'] = [dict(row) for row in cur.fetchall()]
    return jsonify(res)


@api_bp.route('/mailboxes/<address>/messages/<int:msg_id>', methods=['DELETE'])
@jwt_required
def delete_message(address, msg_id):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT folder_id FROM messages WHERE id=? AND mailbox_address=?",
        (msg_id, address),
    )
    msg = cur.fetchone()
    if not msg:
        return jsonify({"error": "not found"}), 404

    cur = db.execute(
        "SELECT id FROM folders WHERE mailbox_address=? AND name=?",
        (address, 'Trash'),
    )
    trash_row = cur.fetchone()
    if not trash_row:
        return jsonify({"error": "trash folder missing"}), 500
    trash_id = trash_row['id']

    if msg['folder_id'] == trash_id:
        db.execute("DELETE FROM messages WHERE id=?", (msg_id,))
    else:
        db.execute(
            "UPDATE messages SET folder_id=? WHERE id=?", (trash_id, msg_id)
        )

    db.commit()
    return jsonify({"status": "deleted"})


@api_bp.route('/mailboxes/<address>/messages/<int:msg_id>', methods=['PATCH'])
@jwt_required
def patch_message(address, msg_id):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    db = get_db()
    if 'is_read' in data:
        db.execute(
            "UPDATE messages SET is_read=? WHERE id=? AND mailbox_address=?",
            (int(bool(data['is_read'])), msg_id, address),
        )
    if 'is_starred' in data:
        db.execute(
            "UPDATE messages SET is_starred=? WHERE id=? AND mailbox_address=?",
            (int(bool(data['is_starred'])), msg_id, address),
        )
    if 'folder_id' in data:
        db.execute(
            "UPDATE messages SET folder_id=? WHERE id=? AND mailbox_address=?",
            (data['folder_id'], msg_id, address),
        )
    db.commit()
    return jsonify({"status": "updated"})


@api_bp.route('/mailboxes/<address>/messages/move', methods=['POST'])
@jwt_required
def bulk_move(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    msg_ids = data.get('message_ids', [])
    folder_id = data.get('folder_id')
    if not msg_ids or folder_id is None:
        return jsonify({"error": "message_ids and folder_id are required"}), 400

    db = get_db()
    for mid in msg_ids:
        db.execute(
            "UPDATE messages SET folder_id=? WHERE id=? AND mailbox_address=?",
            (folder_id, mid, address),
        )
    db.commit()
    return jsonify({"status": "moved", "count": len(msg_ids)})


@api_bp.route('/mailboxes/<address>/messages/mark', methods=['POST'])
@jwt_required
def bulk_mark(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    msg_ids = data.get('message_ids', [])
    is_read = data.get('is_read')
    if not msg_ids or is_read is None:
        return jsonify({"error": "message_ids and is_read are required"}), 400

    db = get_db()
    for mid in msg_ids:
        db.execute(
            "UPDATE messages SET is_read=? WHERE id=? AND mailbox_address=?",
            (int(bool(is_read)), mid, address),
        )
    db.commit()
    return jsonify({"status": "marked", "count": len(msg_ids)})


@api_bp.route('/mailboxes/<address>/folders', methods=['GET'])
@jwt_required
def get_folders(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT id, name, system_folder, color FROM folders WHERE mailbox_address=?",
        (address,),
    )
    folders = [dict(row) for row in cur.fetchall()]
    for f in folders:
        cur = db.execute(
            "SELECT COUNT(*) FROM messages WHERE folder_id=? AND is_read=0",
            (f['id'],),
        )
        f['unread_count'] = cur.fetchone()[0]

        cur = db.execute(
            "SELECT COUNT(*) FROM messages WHERE folder_id=?",
            (f['id'],),
        )
        f['total_count'] = cur.fetchone()[0]

    return jsonify(folders)


@api_bp.route('/mailboxes/<address>/folders', methods=['POST'])
@jwt_required
def create_folder(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    color = (data.get('color') or '').strip() or None

    now = datetime.now(timezone.utc).isoformat()
    db = get_db()
    try:
        db.execute(
            "INSERT INTO folders (mailbox_address, name, system_folder, color, created_at) VALUES (?, ?, 0, ?, ?)",
            (address, name, color, now),
        )
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    return jsonify({"status": "created"}), 201


@api_bp.route('/mailboxes/<address>/folders/<int:fid>', methods=['PATCH'])
@jwt_required
def patch_folder(address, fid):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT system_folder FROM folders WHERE id=? AND mailbox_address=?",
        (fid, address),
    )
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    if row['system_folder'] == 1:
        return jsonify({"error": "cannot modify system folder"}), 400

    data = request.json or {}
    fields, values = [], []
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({"error": "name cannot be empty"}), 400
        fields.append("name=?")
        values.append(name)
    if 'color' in data:
        color = (data['color'] or '').strip() or None
        fields.append("color=?")
        values.append(color)
    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    values.extend([fid, address])
    try:
        db.execute(f"UPDATE folders SET {', '.join(fields)} WHERE id=? AND mailbox_address=?", values)
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    return jsonify({"status": "updated"})


@api_bp.route('/mailboxes/<address>/folders/<int:fid>', methods=['DELETE'])
@jwt_required
def delete_folder(address, fid):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT system_folder FROM folders WHERE id=? AND mailbox_address=?",
        (fid, address),
    )
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    if row['system_folder'] == 1:
        return jsonify({"error": "cannot delete system folder"}), 400

    db.execute(
        "DELETE FROM folders WHERE id=? AND mailbox_address=?", (fid, address)
    )
    db.commit()
    return jsonify({"status": "deleted"})


@api_bp.route('/mailboxes/<address>/folders/<int:fid>/empty', methods=['DELETE'])
@jwt_required
def empty_folder(address, fid):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT name FROM folders WHERE id=? AND mailbox_address=?",
        (fid, address),
    )
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404

    if row['name'] != 'Trash':
        return jsonify({"error": "can only empty Trash folder"}), 400

    db.execute("DELETE FROM messages WHERE folder_id=? AND mailbox_address=?", (fid, address))
    db.commit()
    return jsonify({"status": "emptied"})


@api_bp.route('/mailboxes/<address>/search', methods=['GET'])
@jwt_required
def search_messages(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({"error": "q parameter is required"}), 400

    folder = request.args.get('folder')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(1, int(request.args.get('per_page', 50))))
    offset = (page - 1) * per_page

    safe_q = re.sub(r'[^\w\s@.\-]', '', q).strip()
    if not safe_q:
        return jsonify({"error": "invalid search query"}), 400

    db = get_db()

    count_query = """
        SELECT COUNT(*) FROM messages m
        JOIN messages_fts fts ON m.id = fts.rowid
        WHERE m.mailbox_address = ? AND messages_fts MATCH ?
    """
    select_query = """
        SELECT m.* FROM messages m
        JOIN messages_fts fts ON m.id = fts.rowid
        WHERE m.mailbox_address = ? AND messages_fts MATCH ?
    """
    params = [address, safe_q]

    if folder:
        cur = db.execute(
            "SELECT id FROM folders WHERE mailbox_address=? AND name=?",
            (address, folder),
        )
        row = cur.fetchone()
        if row:
            count_query += " AND m.folder_id = ?"
            select_query += " AND m.folder_id = ?"
            params.append(row['id'])

    try:
        cur = db.execute(count_query, params)
        total = cur.fetchone()[0]

        select_query += " ORDER BY m.received_at DESC LIMIT ? OFFSET ?"
        cur = db.execute(select_query, params + [per_page, offset])
        msgs = [dict(row) for row in cur.fetchall()]
    except Exception:
        log.exception("FTS search failed for query: %s", safe_q)
        return jsonify({"error": "search query syntax error"}), 400

    return _paginated(msgs, total, page, per_page)


def _parse_email_address(raw):
    m = re.search(r'<([^>]+)>', raw)
    return m.group(1).strip() if m else raw.strip()


def _local_deliver(db, recipient_addr, from_address, to_field, data, subject, text, html, msg_id, now):
    cur = db.execute(
        "SELECT id FROM folders WHERE mailbox_address=? AND name='Inbox'",
        (recipient_addr,),
    )
    inbox = cur.fetchone()
    if not inbox:
        return
    local_msg_id = f"<local-{uuid.uuid4()}@{msg_id.split('@')[-1].rstrip('>')}>"
    db.execute("""
        INSERT INTO messages (
            message_id, mailbox_address, folder_id, from_address,
            to_addresses, cc_addresses, subject, text_body, html_body,
            received_at, is_read, is_starred, is_draft, in_reply_to,
            reference_ids, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, ?, ?)
    """, (
        local_msg_id, recipient_addr, inbox['id'], from_address,
        json.dumps(to_field), json.dumps(data.get('cc') or []),
        subject, text, html, now,
        data.get('in_reply_to') or data.get('inReplyTo', ''),
        data.get('references', ''), now,
    ))
    log.info("Local delivery: msg_id=%s to=%s", local_msg_id, recipient_addr)


def _dispatch_send(address, data):
    allowed, reason = limiter.check_rate(address)
    if not allowed:
        return jsonify({"error": reason}), 429

    to_field = data.get('to', [])
    if isinstance(to_field, str):
        to_field = [to_field]
    if not to_field:
        return jsonify({"error": "to is required"}), 400

    subject = data.get('subject', '')
    text = data.get('text') or data.get('text_body', '')
    html = data.get('html') or data.get('html_body', '')

    if len(text) > _MAX_BODY_LEN or len(html) > _MAX_BODY_LEN:
        return jsonify({"error": "message body too large"}), 413

    attachments = data.get('attachments') or []
    _MAX_ATTACH_BYTES = 10 * 1024 * 1024
    total_attach = sum(a.get('size_bytes', 0) for a in attachments)
    if total_attach > _MAX_ATTACH_BYTES:
        return jsonify({"error": "attachments exceed 10 MB limit"}), 413

    now = datetime.now(timezone.utc).isoformat()
    msg_id = f"<{uuid.uuid4()}@{address.split('@')[1]}>"

    db = get_db()

    # Split recipients: local mailboxes get direct delivery, external go via CF worker
    local_recipients = []
    external_recipients = []
    for recipient in to_field:
        addr = _parse_email_address(recipient)
        cur = db.execute("SELECT address FROM mailboxes WHERE address=? AND is_active=1", (addr,))
        if cur.fetchone():
            local_recipients.append(addr)
        else:
            external_recipients.append(recipient)

    status = 'sent'
    error_msg = None
    worker_resp = None

    outbound_url = config.OUTBOUND_WORKER_URL
    if external_recipients:
        worker_payload = {
            "from": address,
            "to": external_recipients,
            "cc": data.get('cc'),
            "bcc": data.get('bcc'),
            "subject": subject,
            "text": text,
            "html": html,
            "replyTo": data.get('reply_to') or data.get('replyTo'),
            "inReplyTo": data.get('in_reply_to') or data.get('inReplyTo'),
            "references": data.get('references'),
            "messageId": msg_id,
            "attachments": attachments,
        }
        if outbound_url:
            try:
                resp = http_requests.post(
                    outbound_url,
                    json=worker_payload,
                    headers={"Authorization": f"Bearer {config.OUTBOUND_AUTH_SECRET}"},
                    timeout=30,
                )
                worker_resp = resp.text
                if not resp.ok:
                    status = 'failed'
                    error_msg = resp.text
            except Exception as e:
                status = 'failed'
                error_msg = str(e)
        else:
            status = 'failed'
            error_msg = 'Outbound worker not configured'

    db.execute(
        "INSERT INTO send_log (message_id, from_address, to_addresses, subject, sent_at, status, error_message, worker_response) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (msg_id, address, json.dumps(to_field), subject, now, status, error_msg, worker_resp),
    )

    if status == 'sent':
        limiter.record_send(address)
        cur = db.execute(
            "SELECT id FROM folders WHERE mailbox_address=? AND name='Sent'",
            (address,),
        )
        sent_folder = cur.fetchone()
        if sent_folder:
            cur2 = db.execute("""
                INSERT INTO messages (
                    message_id, mailbox_address, folder_id, from_address,
                    to_addresses, cc_addresses, subject, text_body, html_body,
                    sent_at, is_read, is_starred, is_draft, in_reply_to,
                    reference_ids, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, ?, ?, ?)
            """, (
                msg_id, address, sent_folder['id'], address,
                json.dumps(to_field), json.dumps(data.get('cc') or []),
                subject, text, html, now,
                data.get('in_reply_to') or data.get('inReplyTo', ''),
                data.get('references', ''), now,
            ))
            sent_msg_id = cur2.lastrowid
            for att in attachments:
                db.execute(
                    "INSERT INTO attachments (message_id, filename, content_type, size_bytes, storage_path, is_inline, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
                    (sent_msg_id, att['filename'], att['content_type'], att.get('size_bytes', 0), None, now),
                )

        for recipient_addr in local_recipients:
            _local_deliver(db, recipient_addr, address, to_field, data, subject, text, html, msg_id, now)

    db.commit()

    if status == 'failed':
        log.warning("Send failed: from=%s error=%s", address, error_msg)
        return jsonify({"error": error_msg or "Send failed"}), 502
    log.info("Send success: from=%s to=%s msg_id=%s", address, to_field, msg_id)
    return jsonify({"status": "sent", "message_id": msg_id})


@api_bp.route('/mailboxes/<address>/send', methods=['POST'])
@jwt_required
def send_email(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = dict(request.form)
        # Flatten single-value lists produced by request.form
        data = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in data.items()}
        files = request.files.getlist('attachments')
        log.debug("send_email multipart: form_keys=%s file_count=%d", list(data.keys()), len(files))
        attachments = []
        for f in files:
            raw = f.read()
            log.debug("send_email attachment: filename=%s content_type=%s size=%d", f.filename, f.content_type, len(raw))
            attachments.append({
                'filename': f.filename,
                'content_type': f.content_type or 'application/octet-stream',
                'data_b64': base64.b64encode(raw).decode('ascii'),
                'size_bytes': len(raw),
            })
        data['attachments'] = attachments
    else:
        data = request.json or {}
    return _dispatch_send(address, data)


@api_bp.route('/mailboxes/<address>/drafts', methods=['POST'])
@jwt_required
def create_draft(address):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    db = get_db()
    cur = db.execute(
        "SELECT id FROM folders WHERE mailbox_address=? AND name='Drafts'",
        (address,),
    )
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "drafts folder missing"}), 500
    folder_id = row['id']
    now = datetime.now(timezone.utc).isoformat()

    cur = db.execute("""
        INSERT INTO messages (
            message_id, mailbox_address, folder_id, to_addresses, subject,
            text_body, html_body, is_draft, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (
        str(uuid.uuid4()), address, folder_id,
        json.dumps(data.get('to', [])), data.get('subject', ''),
        data.get('text_body', ''), data.get('html_body', ''), now,
    ))
    db.commit()
    return jsonify({"status": "created", "id": cur.lastrowid}), 201


@api_bp.route('/mailboxes/<address>/drafts/<int:did>', methods=['PUT'])
@jwt_required
def update_draft(address, did):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    data = request.json or {}
    db = get_db()
    db.execute("""
        UPDATE messages SET to_addresses=?, subject=?, text_body=?, html_body=?
        WHERE id=? AND mailbox_address=? AND is_draft=1
    """, (
        json.dumps(data.get('to', [])), data.get('subject', ''),
        data.get('text_body', ''), data.get('html_body', ''),
        did, address,
    ))
    db.commit()
    return jsonify({"status": "updated"})


@api_bp.route('/mailboxes/<address>/drafts/<int:did>/send', methods=['POST'])
@jwt_required
def send_draft(address, did):
    if not _check_mailbox_access(address):
        return jsonify({"error": "forbidden"}), 403

    db = get_db()
    cur = db.execute(
        "SELECT * FROM messages WHERE id=? AND mailbox_address=? AND is_draft=1",
        (did, address),
    )
    draft = cur.fetchone()
    if not draft:
        return jsonify({"error": "draft not found"}), 404

    draft = dict(draft)
    send_data = {
        "to": json.loads(draft.get('to_addresses') or '[]'),
        "subject": draft.get('subject', ''),
        "text_body": draft.get('text_body', ''),
        "html_body": draft.get('html_body', ''),
        "in_reply_to": draft.get('in_reply_to', ''),
        "references": draft.get('reference_ids', ''),
    }

    result = _dispatch_send(address, send_data)
    response = result[0] if isinstance(result, tuple) else result
    status_code = result[1] if isinstance(result, tuple) else response.status_code

    if status_code < 400:
        db.execute(
            "DELETE FROM messages WHERE id=? AND mailbox_address=? AND is_draft=1",
            (did, address),
        )
        db.commit()

    return result


@api_bp.route('/attachments/<int:aid>/download', methods=['GET'])
@jwt_required
def download_attachment(aid):
    db = get_db()
    cur = db.execute("SELECT * FROM attachments WHERE id=?", (aid,))
    att = cur.fetchone()
    if not att:
        return jsonify({"error": "not found"}), 404

    cur = db.execute(
        "SELECT mailbox_address FROM messages WHERE id=?", (att['message_id'],)
    )
    msg = cur.fetchone()
    if not msg or not _check_mailbox_access(msg['mailbox_address']):
        return jsonify({"error": "forbidden"}), 403

    att_path = os.path.abspath(att['storage_path'])
    safe_root = os.path.abspath(config.ATTACHMENTS_PATH) + os.sep
    if not att_path.startswith(safe_root):
        return jsonify({"error": "invalid path"}), 400

    if not os.path.isfile(att_path):
        return jsonify({"error": "file not found"}), 404

    return send_file(
        att_path,
        as_attachment=True,
        download_name=att['filename'],
        mimetype=att['content_type'],
    )
