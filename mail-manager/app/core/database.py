import sqlite3
import os
from flask import g
from app.config import config

_SCHEMA = """
    CREATE TABLE IF NOT EXISTS mailboxes (
        address TEXT PRIMARY KEY,
        display_name TEXT,
        domain TEXT,
        created_at TEXT,
        is_active INTEGER
    );
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mailbox_address TEXT,
        name TEXT,
        system_folder INTEGER,
        color TEXT,
        created_at TEXT,
        UNIQUE(mailbox_address, name),
        FOREIGN KEY(mailbox_address) REFERENCES mailboxes(address) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE,
        mailbox_address TEXT,
        folder_id INTEGER,
        from_address TEXT,
        from_name TEXT,
        to_addresses TEXT,
        cc_addresses TEXT,
        bcc_addresses TEXT,
        subject TEXT,
        text_body TEXT,
        html_body TEXT,
        received_at TEXT,
        sent_at TEXT,
        is_read INTEGER,
        is_starred INTEGER,
        is_draft INTEGER,
        in_reply_to TEXT,
        reference_ids TEXT,
        size_bytes INTEGER,
        has_attachments INTEGER,
        headers_json TEXT,
        created_at TEXT,
        FOREIGN KEY(mailbox_address) REFERENCES mailboxes(address) ON DELETE CASCADE,
        FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
        subject, from_address, from_name, to_addresses, text_body,
        tokenize='porter unicode61'
    );
    CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        filename TEXT,
        content_type TEXT,
        size_bytes INTEGER,
        storage_path TEXT,
        content_id TEXT,
        is_inline INTEGER,
        created_at TEXT,
        FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS send_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT,
        from_address TEXT,
        to_addresses TEXT,
        subject TEXT,
        sent_at TEXT,
        status TEXT,
        error_message TEXT,
        worker_response TEXT
    );
    CREATE TABLE IF NOT EXISTS bounce_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_message_id TEXT,
        bounce_type TEXT,
        recipient TEXT,
        reason TEXT,
        received_at TEXT
    );
    CREATE TABLE IF NOT EXISTS domain_configs (
        domain_name TEXT PRIMARY KEY,
        webhook_secret TEXT NOT NULL,
        r2_bucket TEXT NOT NULL,
        r2_access_key_id TEXT NOT NULL,
        r2_secret_access_key TEXT NOT NULL,
        r2_endpoint_url TEXT NOT NULL,
        outbound_worker_url TEXT NOT NULL,
        outbound_auth_secret TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_domain_configs_name ON domain_configs(domain_name);
    CREATE INDEX IF NOT EXISTS idx_messages_mailbox ON messages(mailbox_address);
    CREATE INDEX IF NOT EXISTS idx_messages_folder ON messages(folder_id);
    CREATE INDEX IF NOT EXISTS idx_messages_received ON messages(received_at DESC);
    CREATE INDEX IF NOT EXISTS idx_messages_read ON messages(is_read);
    CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
    CREATE INDEX IF NOT EXISTS idx_send_log_from ON send_log(from_address);
    CREATE TABLE IF NOT EXISTS push_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mailbox_address TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        p256dh TEXT NOT NULL,
        auth TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_attempted_at TEXT,
        last_success_at TEXT,
        fail_count INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (mailbox_address) REFERENCES mailboxes(address) ON DELETE CASCADE,
        UNIQUE(mailbox_address, endpoint)
    );
    CREATE INDEX IF NOT EXISTS idx_push_subscriptions_mailbox ON push_subscriptions(mailbox_address);

    DROP TRIGGER IF EXISTS messages_ai;
    CREATE TRIGGER messages_ai AFTER INSERT ON messages BEGIN
        INSERT INTO messages_fts(rowid, subject, from_address, from_name, to_addresses, text_body)
        VALUES (new.id, new.subject, new.from_address, new.from_name, new.to_addresses, new.text_body);
    END;
    DROP TRIGGER IF EXISTS messages_ad;
    CREATE TRIGGER messages_ad AFTER DELETE ON messages BEGIN
        DELETE FROM messages_fts WHERE rowid = old.id;
    END;
    DROP TRIGGER IF EXISTS messages_au;
    CREATE TRIGGER messages_au AFTER UPDATE ON messages BEGIN
        DELETE FROM messages_fts WHERE rowid = old.id;
        INSERT INTO messages_fts(rowid, subject, from_address, from_name, to_addresses, text_body)
        VALUES (new.id, new.subject, new.from_address, new.from_name, new.to_addresses, new.text_body);
    END;
"""


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=5000')
    return conn


def get_db():
    if 'db' not in g:
        g.db = _connect()
    return g.db


def close_db(exc=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def get_standalone_db():
    return _connect()


def _migrate(conn):
    for sql in [
        "ALTER TABLE folders ADD COLUMN color TEXT",
        "ALTER TABLE mailboxes ADD COLUMN notification_preview INTEGER DEFAULT 1",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass

    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='push_subscriptions'"
        ).fetchone()
        if row and 'UNIQUE(mailbox_address, endpoint)' not in (row[0] or ''):
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS push_subscriptions_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mailbox_address TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    p256dh TEXT NOT NULL,
                    auth TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (mailbox_address) REFERENCES mailboxes(address) ON DELETE CASCADE,
                    UNIQUE(mailbox_address, endpoint)
                );
                INSERT OR IGNORE INTO push_subscriptions_new
                    SELECT id, mailbox_address, endpoint, p256dh, auth, created_at
                    FROM push_subscriptions;
                DROP TABLE push_subscriptions;
                ALTER TABLE push_subscriptions_new RENAME TO push_subscriptions;
                CREATE INDEX IF NOT EXISTS idx_push_subscriptions_mailbox ON push_subscriptions(mailbox_address);
            """)
    except Exception:
        pass

    for sql in [
        "ALTER TABLE push_subscriptions ADD COLUMN last_attempted_at TEXT",
        "ALTER TABLE push_subscriptions ADD COLUMN last_success_at TEXT",
        "ALTER TABLE push_subscriptions ADD COLUMN fail_count INTEGER NOT NULL DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint ON push_subscriptions(endpoint)",
        "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_last_success ON push_subscriptions(last_success_at)",
        "ALTER TABLE mailboxes ADD COLUMN quota_bytes INTEGER NOT NULL DEFAULT 10737418240",
        "ALTER TABLE mailboxes ADD COLUMN quota_exceeded_count INTEGER NOT NULL DEFAULT 0",
        "CREATE INDEX IF NOT EXISTS idx_send_log_sent_at ON send_log(sent_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_bounce_log_received_at ON bounce_log(received_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_bounce_log_message_id ON bounce_log(original_message_id)",
        "ALTER TABLE domain_configs ADD COLUMN catch_all_mailbox TEXT DEFAULT NULL",
        "ALTER TABLE mailboxes ADD COLUMN last_quota_warning_at TEXT DEFAULT NULL",
        "ALTER TABLE domain_configs ADD COLUMN grace_buffer_bytes INTEGER DEFAULT NULL",
        "ALTER TABLE messages ADD COLUMN is_system INTEGER NOT NULL DEFAULT 0",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass


    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS auto_responders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mailbox_address TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT 'Auto Reply',
                message_body TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                reply_interval_hours INTEGER NOT NULL DEFAULT 24,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (mailbox_address) REFERENCES mailboxes(address) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS auto_reply_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mailbox_address TEXT NOT NULL,
                original_sender TEXT NOT NULL,
                original_message_id TEXT,
                replied_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_auto_responders_mailbox ON auto_responders(mailbox_address);
            CREATE INDEX IF NOT EXISTS idx_auto_reply_log_lookup ON auto_reply_log(mailbox_address, original_sender, replied_at);
        """)
    except Exception:
        pass


def init_db():
    import logging
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = _connect()
    conn.executescript(_SCHEMA)
    _migrate(conn)
    result = conn.execute("PRAGMA quick_check").fetchone()
    if result and result[0] != 'ok':
        logging.getLogger('mail-manager').critical("SQLite integrity check failed: %s", result[0])
    conn.commit()
    conn.close()


def register_db(app):
    app.teardown_appcontext(close_db)
