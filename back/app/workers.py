"""Background loop in the API process: deliver outbox events and expire unpaid checkouts.

One daemon thread per process. Safe with several workers: outbox events are claimed atomically and expiry uses
compare-and-set updates. Turn off with BACKGROUND_WORKERS=false (tests do).
"""

import logging
import threading
from datetime import UTC, datetime

from app.db.mongo import get_database
from app.db.outbox import dispatch
from app.modules import booking
from app.modules.payment.rails import configured_rail

logger = logging.getLogger(__name__)
OUTBOX_EVERY_SECONDS = 2
EXPIRY_EVERY_SECONDS = 30


def run_once(now: datetime | None = None, *, expire: bool = True) -> None:
    now = now or datetime.now(UTC)
    db = get_database()
    dispatch(db, booking.OUTBOX_HANDLERS, now=now)
    if expire:
        booking.expire_checkouts(db, configured_rail(), now=now)


def _loop(stop: threading.Event) -> None:
    ticks = 0
    while not stop.wait(OUTBOX_EVERY_SECONDS):
        ticks += 1
        try:
            run_once(expire=ticks % (EXPIRY_EVERY_SECONDS // OUTBOX_EVERY_SECONDS) == 0)
        except Exception:  # noqa: BLE001 - keep the loop alive; the next tick retries
            logger.exception("Background worker tick failed")


def start() -> threading.Event:
    stop = threading.Event()
    threading.Thread(target=_loop, args=(stop,), name="outbox-and-expiry", daemon=True).start()
    logger.info(
        "Background worker started (outbox every %ss, expiry every %ss)", OUTBOX_EVERY_SECONDS, EXPIRY_EVERY_SECONDS
    )
    return stop
