import logging
import os
import threading
import time

log = logging.getLogger(__name__)

_CLEANUP_INTERVAL = 7 * 24 * 3600
_ALIAS_EXPIRY_INTERVAL = 3600


def _run_cleanup():
    from app.core.database import get_standalone_db

    db = get_standalone_db()
    try:
        cur = db.execute("""
            DELETE FROM push_subscriptions
            WHERE last_success_at IS NULL AND created_at < datetime('now', '-60 days')
        """)
        if cur.rowcount:
            log.info("Cleanup: removed %d never-fired subscriptions", cur.rowcount)

        cur = db.execute("""
            DELETE FROM push_subscriptions
            WHERE last_success_at IS NOT NULL AND last_success_at < datetime('now', '-60 days')
        """)
        if cur.rowcount:
            log.info("Cleanup: removed %d inactive subscriptions", cur.rowcount)

        cur = db.execute("""
            DELETE FROM push_subscriptions WHERE fail_count >= 5
        """)
        if cur.rowcount:
            log.info("Cleanup: removed %d high-failure subscriptions", cur.rowcount)

        db.commit()
    except Exception:
        log.exception("Cleanup: error during subscription purge")
    finally:
        try:
            db.execute("PRAGMA wal_checkpoint(PASSIVE)")
            db.execute("PRAGMA optimize")
        except Exception:
            log.exception("Cleanup: error during WAL maintenance")
        db.close()


def _scheduler_loop():
    while True:
        time.sleep(_CLEANUP_INTERVAL)
        log.info("Scheduler: running push subscription cleanup")
        try:
            _run_cleanup()
        except Exception:
            log.exception("Scheduler: unhandled error in cleanup run")


def _alias_expiry_loop():
    time.sleep(300)
    while True:
        try:
            from app.core.alias_expiry import expire_aliases
            expire_aliases()
        except Exception:
            log.exception("Scheduler: unhandled error in alias expiry run")
        time.sleep(_ALIAS_EXPIRY_INTERVAL)


def start_scheduler():
    if os.environ.get('DISABLE_SCHEDULER'):
        return
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="push-cleanup-scheduler")
    t.start()
    log.info("Scheduler: push subscription cleanup scheduled every 7 days")
    a = threading.Thread(target=_alias_expiry_loop, daemon=True, name="alias-expiry-scheduler")
    a.start()
    log.info("Scheduler: alias expiry scheduled every hour")
