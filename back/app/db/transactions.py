"""Run a unit of work in a MongoDB transaction when the server supports it.

On a replica set (compose ``rs0``, Atlas) the callback runs inside ``with_transaction``, which retries on
transient errors and commits atomically. mongomock (unit tests) has no sessions, so the callback runs with
``session=None``; the integration tests (``MONGO_TEST_URI``) cover the transactional path.
"""

from collections.abc import Callable
from typing import TypeVar

from pymongo.client_session import ClientSession
from pymongo.database import Database

T = TypeVar("T")


def run_in_transaction(db: Database, work: Callable[[ClientSession | None], T]) -> T:
    try:
        session = db.client.start_session()
    except NotImplementedError:
        return work(None)
    with session:
        return session.with_transaction(lambda s: work(s))
