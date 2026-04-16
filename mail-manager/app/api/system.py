import os
import sqlite3
import zipfile
import json
import threading
import shutil
from datetime import datetime, timezone
from flask import Blueprint, jsonify, send_file, request, after_this_request
from app.config import config
from app.api.middleware import admin_required

system_bp = Blueprint('system', __name__)

@system_bp.route('/backup', methods=['GET'])
@admin_required
def backup_system():
    tmp_db_path = '/tmp/backup.db'
    tmp_zip_path = f'/tmp/email_backup_{datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")}.zip'
    
    if os.path.exists(tmp_db_path):
        os.remove(tmp_db_path)
        
    db_path = config.DB_PATH
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(f"VACUUM INTO '{tmp_db_path}'")
        conn.close()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
    manifest = {
        "schema": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": []
    }
    
    try:
        with zipfile.ZipFile(tmp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db_path, arcname='db/mail.db')
            
            att_path = config.ATTACHMENTS_PATH
            if os.path.exists(att_path):
                for root, dirs, files in os.walk(att_path):
                    for f in files:
                        file_path = os.path.join(root, f)
                        arc_name = os.path.relpath(file_path, config.MAIL_DATA_PATH)
                        zf.write(file_path, arcname=arc_name)
                        
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))
            
        @after_this_request
        def cleanup(response):
            if os.path.exists(tmp_db_path):
                os.remove(tmp_db_path)
            if os.path.exists(tmp_zip_path):
                os.remove(tmp_zip_path)
            return response
            
        return send_file(tmp_zip_path, as_attachment=True, download_name=os.path.basename(tmp_zip_path))
    except Exception as e:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)
        if os.path.exists(tmp_zip_path):
            os.remove(tmp_zip_path)
        return jsonify({"error": str(e)}), 500

@system_bp.route('/local-domains', methods=['GET'])
@admin_required
def local_domains():
    db_path = config.DB_PATH
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT m.domain,
                   COUNT(DISTINCT m.address) AS mailbox_count,
                   COUNT(msg.id) AS message_count
            FROM mailboxes m
            LEFT JOIN messages msg ON msg.mailbox_address = m.address
            GROUP BY m.domain
        """).fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@system_bp.route('/wipe-domain', methods=['POST'])
@admin_required
def wipe_domain():
    data = request.get_json(force=True, silent=True) or {}
    domain = data.get('domain', '').strip()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    config.IN_MAINTENANCE = True
    db_path = config.DB_PATH
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        rows = conn.execute(
            "SELECT id FROM messages WHERE mailbox_address LIKE ? AND has_attachments=1",
            (f'%@{domain}',)
        ).fetchall()
        for row in rows:
            shutil.rmtree(os.path.join(config.ATTACHMENTS_PATH, str(row['id'])), ignore_errors=True)
        conn.execute("DELETE FROM mailboxes WHERE address LIKE ?", (f'%@{domain}',))
        conn.commit()
        conn.close()
        def _vacuum():
            c = sqlite3.connect(db_path)
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            c.execute("VACUUM")
            c.close()
        threading.Thread(target=_vacuum, daemon=True).start()
        config.IN_MAINTENANCE = False
        return jsonify({"status": "wiped", "domain": domain})
    except Exception as e:
        config.IN_MAINTENANCE = False
        return jsonify({"error": str(e)}), 500

@system_bp.route('/wipe-all', methods=['POST'])
@admin_required
def wipe_all():
    config.IN_MAINTENANCE = True
    db_path = config.DB_PATH
    try:
        att_path = config.ATTACHMENTS_PATH
        if os.path.exists(att_path):
            shutil.rmtree(att_path)
        os.makedirs(att_path, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("DELETE FROM mailboxes")
        conn.commit()
        conn.close()
        def _vacuum():
            c = sqlite3.connect(db_path)
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            c.execute("VACUUM")
            c.close()
        threading.Thread(target=_vacuum, daemon=True).start()
        config.IN_MAINTENANCE = False
        return jsonify({"status": "wiped"})
    except Exception as e:
        config.IN_MAINTENANCE = False
        return jsonify({"error": str(e)}), 500

def _schedule_restart():
    def restart():
        import time
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=restart).start()

@system_bp.route('/restore', methods=['POST'])
@admin_required
def restore_system():
    config.IN_MAINTENANCE = True
    
    if 'file' not in request.files:
        config.IN_MAINTENANCE = False
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    tmp_upload_path = '/tmp/restore_upload.zip'
    staging_path = '/data/restore_staging'
    old_data_path = '/data/old_data'
    
    file.save(tmp_upload_path)
    
    try:
        with zipfile.ZipFile(tmp_upload_path, 'r') as zf:
            if 'manifest.json' not in zf.namelist():
                raise ValueError("Invalid backup archive: missing manifest.json")
            if os.path.exists(staging_path):
                shutil.rmtree(staging_path)
            os.makedirs(staging_path)
            zf.extractall(staging_path)
            
        if os.path.exists(old_data_path):
            shutil.rmtree(old_data_path)
        os.makedirs(old_data_path)
        
        db_dir = os.path.dirname(config.DB_PATH)
        att_dir = config.ATTACHMENTS_PATH
        
        if os.path.exists(db_dir):
            shutil.move(db_dir, os.path.join(old_data_path, 'db'))
        if os.path.exists(att_dir):
            shutil.move(att_dir, os.path.join(old_data_path, 'attachments'))
            
        staged_db = os.path.join(staging_path, 'db')
        staged_att = os.path.join(staging_path, 'attachments')
        
        if os.path.exists(staged_db):
            shutil.move(staged_db, db_dir)
        if os.path.exists(staged_att):
            shutil.move(staged_att, att_dir)
            
        shutil.rmtree(staging_path)
        os.remove(tmp_upload_path)
        
        _schedule_restart()
        return jsonify({"status": "success"})
        
    except Exception as e:
        config.IN_MAINTENANCE = False
        if os.path.exists(tmp_upload_path):
            os.remove(tmp_upload_path)
        if os.path.exists(staging_path):
            shutil.rmtree(staging_path)
        if os.path.exists(os.path.join(old_data_path, 'db')):
            if os.path.exists(db_dir):
                shutil.rmtree(db_dir)
            shutil.move(os.path.join(old_data_path, 'db'), db_dir)
        if os.path.exists(os.path.join(old_data_path, 'attachments')):
            if os.path.exists(att_dir):
                shutil.rmtree(att_dir)
            shutil.move(os.path.join(old_data_path, 'attachments'), att_dir)
            
        return jsonify({"error": str(e)}), 500
