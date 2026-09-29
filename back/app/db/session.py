from typing import Any

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def _get_db_config() -> dict[str, Any]:
    """Database connection pool configuration."""
    return {
        "pool_size": 5,
        "max_overflow": 2,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }


def _create_tcp_url() -> URL:
    """Create TCP connection URL for local/dev environments."""
    return URL.create(
        drivername="postgresql+psycopg2",
        username=settings.DB_USER,
        password=settings.DB_PASS,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )


def _create_unix_url() -> URL:
    """Create Unix socket URL for production (Cloud SQL)."""
    return URL.create(
        drivername="postgresql+psycopg2",
        username=settings.DB_USER,
        password=settings.DB_PASS,
        database=settings.DB_NAME,
        query={"host": f"{settings.DB_SOCKET_DIR}/{settings.DB_INSTANCE_NAME}"},
    )


def create_db_engine():
    """Create SQLAlchemy engine based on environment."""
    url = _create_unix_url() if settings.ENV.is_production else _create_tcp_url()
    return create_engine(url, **_get_db_config())


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
