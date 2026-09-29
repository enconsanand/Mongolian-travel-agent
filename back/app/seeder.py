import logging
import sys

from app.db.mongo import ensure_indexes, get_database
from app.seeds.mock_seed import load_mock_collections, upsert_mock_users
from app.seeds.user_seed import create_users, seed_password

logger = logging.getLogger(__name__)


def init(reset: bool = False) -> None:
    db = get_database()
    logger.info(
        "Seeding data%s...", " (--reset: trips, bookings, payments and inventory are replaced)" if reset else ""
    )
    load_mock_collections(db, reset=reset)
    password = seed_password()
    upsert_mock_users(db, password)
    create_users(db=db, password=password)
    failed = ensure_indexes(db)
    if failed:
        raise RuntimeError(f"Could not create indexes on: {', '.join(failed)}")
    logger.info("Finished seeding process.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("*" * 10, "Creating initial data", "*" * 10, "\n")
    init(reset="--reset" in sys.argv)
    print("*" * 10, "Initial data created", "*" * 10, "\n")
