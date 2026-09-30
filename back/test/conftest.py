"""Shared pytest fixtures.

Pure-unit tests (models, schemas, security, JWT, deps) need no database. The
``db`` and ``client`` fixtures provide a fresh in-memory MongoDB (mongomock)
per test for CRUD and API tests, so no running MongoDB server is required.
"""

import os

# Tests use mongomock; don't try to reach a real MongoDB when the app starts
os.environ.setdefault("MONGO_INIT_ON_STARTUP", "false")

import mongomock  # noqa: E402
import pytest  # noqa: E402

from app.api.v1.deps import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.middlewares.rate_limit import InMemoryRateLimiter  # noqa: E402


@pytest.fixture
def db():
    """Function-scoped in-memory database with the app's indexes."""
    database = mongomock.MongoClient(tz_aware=True)["test_travel_mn"]
    # mongomock can't build 2dsphere indexes; only the ones tests rely on matter here
    database["users"].create_index("email", unique=True)
    yield database


@pytest.fixture
def client(db, monkeypatch):
    """TestClient whose endpoints use the isolated ``db``.

    Rate limiting is disabled so repeated auth calls don't trip the 5/min limit.
    """
    from fastapi.testclient import TestClient

    async def _always_allowed(*args, **kwargs):
        return True

    monkeypatch.setattr(InMemoryRateLimiter, "is_allowed", _always_allowed)

    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
