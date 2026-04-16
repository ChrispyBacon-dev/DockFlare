import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger('mail-manager')


def bootstrap():
    master_url = os.environ.get('DOCKFLARE_MASTER_URL', '').rstrip('/')
    if not master_url:
        log.warning("DOCKFLARE_MASTER_URL not set, skipping config bootstrap")
        return None

    import requests

    bootstrap_secret = os.environ.get('INTERNAL_BOOTSTRAP_SECRET', '')
    headers = {'X-Bootstrap-Token': bootstrap_secret} if bootstrap_secret else {}

    for attempt in range(15):
        try:
            r = requests.get(
                f"{master_url}/email/internal/config",
                headers=headers,
                timeout=5,
                allow_redirects=False,
            )
            if r.status_code == 200 and r.content:
                data = r.json()
                if data.get('configured'):
                    os.environ['JWT_PUBLIC_KEY'] = data.get('jwt_public_key', '')
                    os.environ['JWT_ALGORITHM'] = data.get('jwt_algorithm', 'EdDSA')
                    os.environ['JWT_ISSUER'] = data.get('jwt_issuer', 'dockflare-master')
                    os.environ['JWT_AUDIENCE'] = data.get('jwt_audience', 'dockflare-mail')
                    os.environ['VAPID_PRIVATE_KEY'] = data.get('vapid_private_key', '')
                    os.environ['VAPID_PUBLIC_KEY'] = data.get('vapid_public_key', '')
                    domains = data.get('domains', {})
                    if not domains:
                        log.warning("No domains in bootstrap config")
                    log.info("Config bootstrapped from DockFlare Master")
                else:
                    log.info("DockFlare Master has no email config yet, starting unconfigured")
                return data
        except Exception as e:
            log.info("Bootstrap attempt %d/15 failed: %s", attempt + 1, e)
        time.sleep(2)

    log.warning("Could not reach DockFlare Master after 15 attempts, starting with env vars as-is")
    return None


def _sync_mailboxes(bootstrap_data):
    if not bootstrap_data or not bootstrap_data.get('configured'):
        return

    import sqlite3
    from datetime import datetime, timezone

    mail_data_path = os.environ.get('MAIL_DATA_PATH', '/data')
    db_path = os.path.join(mail_data_path, 'db', 'mail.db')
    if not os.path.exists(db_path):
        log.warning("DB not found during mailbox sync, skipping")
        return

    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        for zone_name, d in bootstrap_data.get('domains', {}).items():
            for address, mbox in d.get('mailboxes', {}).items():
                quota_bytes = mbox.get('quota_bytes', 10737418240)
                existed = conn.execute(
                    "SELECT 1 FROM mailboxes WHERE address=?", (address,)
                ).fetchone()
                conn.execute(
                    "INSERT INTO mailboxes (address, display_name, domain, created_at, is_active, quota_bytes) VALUES (?, ?, ?, ?, 1, ?) "
                    "ON CONFLICT(address) DO UPDATE SET display_name=excluded.display_name, quota_bytes=excluded.quota_bytes",
                    (address, mbox.get('display_name', ''), zone_name, now, quota_bytes),
                )
                if not existed:
                    for folder in ['Inbox', 'Sent', 'Drafts', 'Trash', 'Spam']:
                        conn.execute(
                            "INSERT OR IGNORE INTO folders (mailbox_address, name, system_folder, created_at) VALUES (?, ?, 1, ?)",
                            (address, folder, now),
                        )
        conn.commit()
        log.info("Mailbox sync complete")
    except Exception as e:
        log.error("Mailbox sync failed: %s", e)
    finally:
        conn.close()


def _sync_domains(bootstrap_data):
    if not bootstrap_data or not bootstrap_data.get('configured'):
        return

    import sqlite3
    from datetime import datetime, timezone

    mail_data_path = os.environ.get('MAIL_DATA_PATH', '/data')
    db_path = os.path.join(mail_data_path, 'db', 'mail.db')
    if not os.path.exists(db_path):
        log.warning("DB not found during domain sync, skipping")
        return

    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    try:
        for zone_name, d in bootstrap_data.get('domains', {}).items():
            conn.execute("""
                INSERT INTO domain_configs (
                    domain_name, webhook_secret, r2_bucket, r2_access_key_id,
                    r2_secret_access_key, r2_endpoint_url, outbound_worker_url,
                    outbound_auth_secret, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain_name) DO UPDATE SET
                    webhook_secret=excluded.webhook_secret,
                    r2_bucket=excluded.r2_bucket,
                    r2_access_key_id=excluded.r2_access_key_id,
                    r2_secret_access_key=excluded.r2_secret_access_key,
                    r2_endpoint_url=excluded.r2_endpoint_url,
                    outbound_worker_url=excluded.outbound_worker_url,
                    outbound_auth_secret=excluded.outbound_auth_secret,
                    updated_at=excluded.updated_at
            """, (
                zone_name,
                d.get('webhook_secret', ''),
                d.get('r2_bucket', ''),
                d.get('r2_access_key_id', ''),
                d.get('r2_secret_access_key', ''),
                d.get('r2_endpoint_url', ''),
                d.get('outbound_worker_url', ''),
                d.get('outbound_auth_secret', ''),
                now,
            ))
        conn.commit()
        log.info("Domain config sync complete (%d domains)", len(bootstrap_data.get('domains', {})))
    except Exception as e:
        log.error("Domain config sync failed: %s", e)
    finally:
        conn.close()


def _cleanup_stale_mailboxes(bootstrap_data):
    if not bootstrap_data or not bootstrap_data.get('configured'):
        return
    domains = bootstrap_data.get('domains', {})
    total_expected = sum(len(d.get('mailboxes', {})) for d in domains.values())
    if total_expected < 1:
        return

    import sqlite3, shutil

    mail_data_path = os.environ.get('MAIL_DATA_PATH', '/data')
    db_path = os.path.join(mail_data_path, 'db', 'mail.db')
    att_path = os.path.join(mail_data_path, 'attachments')
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        for zone_name, d in domains.items():
            expected = set(d.get('mailboxes', {}).keys())
            db_rows = conn.execute(
                "SELECT address FROM mailboxes WHERE domain=?", (zone_name,)
            ).fetchall()
            for row in db_rows:
                if row['address'] not in expected:
                    msg_rows = conn.execute(
                        "SELECT id FROM messages WHERE mailbox_address=? AND has_attachments=1",
                        (row['address'],),
                    ).fetchall()
                    for m in msg_rows:
                        shutil.rmtree(os.path.join(att_path, str(m['id'])), ignore_errors=True)
                    conn.execute("DELETE FROM mailboxes WHERE address=?", (row['address'],))
                    log.info("Removed stale mailbox: %s", row['address'])
            conn.commit()
    except Exception as e:
        log.error("Stale mailbox cleanup failed: %s", e)
    finally:
        conn.close()


def _heal_filesystem():
    import sqlite3, shutil

    mail_data_path = os.environ.get('MAIL_DATA_PATH', '/data')
    db_path = os.path.join(mail_data_path, 'db', 'mail.db')
    att_path = os.path.join(mail_data_path, 'attachments')

    if not os.path.exists(att_path) or not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        for name in os.listdir(att_path):
            dir_path = os.path.join(att_path, name)
            if not os.path.isdir(dir_path):
                continue
            try:
                msg_id = int(name)
            except ValueError:
                shutil.rmtree(dir_path, ignore_errors=True)
                log.info("Purged non-integer attachment dir: %s", name)
                continue
            if not conn.execute("SELECT 1 FROM messages WHERE id=?", (msg_id,)).fetchone():
                shutil.rmtree(dir_path, ignore_errors=True)
                log.info("Purged orphan attachment dir: %s", name)

        rows = conn.execute("SELECT id FROM messages WHERE has_attachments=1").fetchall()
        for row in rows:
            if not os.path.isdir(os.path.join(att_path, str(row['id']))):
                conn.execute("UPDATE messages SET has_attachments=0 WHERE id=?", (row['id'],))
        conn.commit()
    except Exception as e:
        log.error("Filesystem self-healing failed: %s", e)
    finally:
        conn.close()


bootstrap_data = bootstrap()

from waitress import serve
from app import create_app

app = create_app()
_sync_mailboxes(bootstrap_data)
_sync_domains(bootstrap_data)
_cleanup_stale_mailboxes(bootstrap_data)
_heal_filesystem()
log.info("Starting mail-manager on port 8025")
serve(app, host='0.0.0.0', port=8025, threads=16, connection_limit=100, channel_timeout=30)
