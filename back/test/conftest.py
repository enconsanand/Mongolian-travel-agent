"""Shared pytest fixtures.

Pure-unit tests (models, schemas, security, JWT, deps) need no database. The
``db`` and ``client`` fixtures provide a Postgres-backed, transactionally
isolated session for CRUD and API tests; if no database is reachable those
tests are skipped rather than failing.
"""

import pytest
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.base import Base  # noqa: F401  (imports models so metadata is populated)
from app.db.session import engine
from app.main import app
from app.middlewares.rate_limit import InMemoryRateLimiter
from app.v1.deps import get_db


@pytest.fixture(scope="session")
def _schema():
    """Ensure the schema exists; skip DB-backed tests if Postgres is unreachable."""
    from sqlalchemy import text

    try:
        connection = engine.connect()
    except OperationalError as exc:  # pragma: no cover - depends on environment
        pytest.skip(f"Database not available: {exc}")

    try:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        connection.commit()
        Base.metadata.create_all(bind=connection)
        connection.commit()
    finally:
        connection.close()

    yield


@pytest.fixture
def db(_schema):
    """Function-scoped session wrapped in a transaction that is always rolled back."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db, monkeypatch):
    """TestClient whose endpoints use the isolated ``db`` session.

    Rate limiting is disabled so repeated auth calls don't trip the 5/min limit.
    """
    from fastapi.testclient import TestClient

    async def _always_allowed(*args, **kwargs):
        return True

    monkeypatch.setattr(InMemoryRateLimiter, "is_allowed", _always_allowed)

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
