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
                    domains = data.get('domains', {})
                    if domains:
                        d = next(iter(domains.values()))
                        os.environ['WEBHOOK_SECRET'] = d.get('webhook_secret', '')
                        os.environ['R2_ACCESS_KEY_ID'] = d.get('r2_access_key_id', '')
                        os.environ['R2_SECRET_ACCESS_KEY'] = d.get('r2_secret_access_key', '')
                        os.environ['R2_ENDPOINT_URL'] = d.get('r2_endpoint_url', '')
                        os.environ['R2_BUCKET_NAME'] = d.get('r2_bucket', '')
                        os.environ['OUTBOUND_WORKER_URL'] = d.get('outbound_worker_url', '')
                        os.environ['OUTBOUND_AUTH_SECRET'] = d.get('outbound_auth_secret', '')
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
                if not conn.execute(
                    "SELECT 1 FROM mailboxes WHERE address=?", (address,)
                ).fetchone():
                    conn.execute(
                        "INSERT INTO mailboxes (address, display_name, domain, created_at, is_active) VALUES (?, ?, ?, ?, 1)",
                        (address, mbox.get('display_name', ''), zone_name, now),
                    )
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


bootstrap_data = bootstrap()

from waitress import serve
from app import create_app

_sync_mailboxes(bootstrap_data)

app = create_app()
log.info("Starting mail-manager on port 8025")
serve(app, host='0.0.0.0', port=8025)
