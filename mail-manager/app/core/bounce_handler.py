import sqlite3
from datetime import datetime, timezone
from app.core.database import get_db

def log_bounce(original_message_id, bounce_type, recipient, reason):
    conn = get_db()
    conn.execute(
        "INSERT INTO bounce_log (original_message_id, bounce_type, recipient, reason, received_at) VALUES (?, ?, ?, ?, ?)",
        (original_message_id, bounce_type, recipient, reason, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
