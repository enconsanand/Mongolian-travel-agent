"""Transactional outbox: write the event in the same transaction as the change it announces.

A dispatcher (change stream on ``outbox``) delivers undelivered events and sets ``dispatched_at``; until it
exists, readers can query ``outbox`` for ``dispatched_at: null``.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

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
