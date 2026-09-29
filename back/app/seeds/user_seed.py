import logging
import os
import secrets

from pymongo.database import Database

from app import crud, schemas
from app.utils.functions import load_data

logger = logging.getLogger(__name__)


def seed_password() -> str:
    """Never store seed passwords in version control; take from env or generate."""
    password = os.environ.get("SEED_DEV_PASSWORD")
    if password:
        return password
    password = secrets.token_urlsafe(24)
    logger.warning("SEED_DEV_PASSWORD not set; generated seed password: %s", password)
    return password


def create_users(db: Database, password: str):
    for row in load_data("users.json"):
        email = row.get("email")
        if crud.user.get_by_email(db=db, email=email):
            logger.info("User with email `%s` already exists.", email)
            continue

        obj_in = schemas.UserCreate(
            email=email,
            password=password,
            is_active=True,
            first_name=row.get("first_name"),
            last_name=row.get("last_name"),
        )
        crud.user.create(db=db, obj_in=obj_in)
