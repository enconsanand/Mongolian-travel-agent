"""Transactional outbox: write the event in the same transaction as the change it announces, deliver it later.

``dispatch`` claims one undelivered event at a time with an atomic ``find_one_and_update`` (safe with several
workers), runs its handler, and on failure puts it back with ``last_error`` so a later pass retries. Handlers
must be idempotent: an event can be delivered again after a crash. Polling is enough at hackathon scale; a
change stream can wake the loop later without changing this contract.
"""

import logging
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any
from uuid import uuid4

from pymongo import ReturnDocument
from pymongo.client_session import ClientSession
from pymongo.database import Database

from app.schemas.commerce import OutboxEventDoc


def iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(
    db: Database,
    *,
    type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    now: datetime,
    session: ClientSession | None = None,
) -> str:
    event = OutboxEventDoc.model_validate(
        {
            "_id": f"evt_{uuid4().hex}",
            "type": type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "created_at": iso(now),
        }
    )
    db[OutboxEventDoc.collection].insert_one(event.model_dump(by_alias=True, exclude={"is_mock"}), session=session)
    return event.id


logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 10
Handler = Callable[[Database, dict[str, Any], datetime], None]


def dispatch(db: Database, handlers: Mapping[str, Handler], *, now: datetime, limit: int = 50) -> int:
    """Deliver up to ``limit`` undelivered events of the handled types; returns how many were delivered."""
    delivered = 0
    col = db[OutboxEventDoc.collection]
    for _ in range(limit):
        event = col.find_one_and_update(
            {"dispatched_at": None, "type": {"$in": list(handlers)}, "attempts": {"$lt": MAX_ATTEMPTS}},
            {"$set": {"dispatched_at": iso(now)}, "$inc": {"attempts": 1}},
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if event is None:
            break
        try:
            handlers[event["type"]](db, event, now)
            delivered += 1
        except Exception as exc:  # noqa: BLE001 - any handler failure: put the event back for a retry
            logger.exception("Outbox handler for %s failed (attempt %s)", event["_id"], event["attempts"])
            col.update_one({"_id": event["_id"]}, {"$set": {"dispatched_at": None, "last_error": str(exc)[:500]}})
    return delivered
