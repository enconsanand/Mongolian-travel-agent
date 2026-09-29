import logging

from app.db.session import SessionLocal
from app.seeds.user_seed import create_users

logger = logging.getLogger(__name__)


def init() -> None:
    with SessionLocal() as db:
        logger.info("Seeding data...")
        create_users(db=db)
        db.commit()
        logger.info("Finished seeding process.")


if __name__ == "__main__":
    print("*" * 10, "Creating initial data", "*" * 10, "\n")
    init()
    print("*" * 10, "Initial data created", "*" * 10, "\n")
