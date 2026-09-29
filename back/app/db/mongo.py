import logging
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, GEOSPHERE, IndexModel, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> MongoClient:
    """Shared MongoClient; it pools connections and is safe to reuse across threads."""
    return MongoClient(settings.MONGO_URI, tz_aware=True, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    return get_client()[settings.MONGO_DB_NAME]


_region_key: list[tuple[str, int | str]] = [("region", ASCENDING)]

# (collection, keys, options). The only list of indexes: the app creates them at startup and the seeder
# creates them on every collection it loads.
INDEXES: list[tuple[str, list[tuple[str, int | str]], dict]] = [
    ("users", [("email", ASCENDING)], {"unique": True}),
    ("regions", [("boundary", GEOSPHERE)], {}),
    ("places", [("location", GEOSPHERE)], {}),
    ("stays", [("location", GEOSPHERE)], {}),
    ("events", [("location", GEOSPHERE)], {}),
    ("events", [("start_date", ASCENDING)], {}),
    ("vehicles", [("current_location", GEOSPHERE)], {}),
    ("routes", [("geometry", GEOSPHERE)], {}),
    *[(c, _region_key, {}) for c in ("places", "events", "routes", "transport_schedules", "shared_rides", "drivers")],
    ("stays", [("region", ASCENDING), ("type", ASCENDING)], {}),
    ("vehicles", [("region", ASCENDING), ("rental.mode", ASCENDING)], {}),
    ("stay_availability", [("stay_id", ASCENDING), ("date", ASCENDING), ("unit_type", ASCENDING)], {"unique": True}),
    (
        "transport_availability",
        [("schedule_id", ASCENDING), ("date", ASCENDING), ("departure_time", ASCENDING), ("seat_class", ASCENDING)],
        {"unique": True},
    ),
    ("vehicle_availability", [("vehicle_id", ASCENDING), ("date", ASCENDING)], {"unique": True}),
    ("shared_rides", [("from_place_id", ASCENDING), ("to_place_id", ASCENDING), ("date", ASCENDING)], {}),
    ("bookings", [("trip_id", ASCENDING)], {}),
    ("bookings", [("user_id", ASCENDING)], {}),
    ("quotes", [("trip_id", ASCENDING)], {}),
    ("payments", [("idempotency_key", ASCENDING)], {"unique": True}),
    ("payments", [("user_id", ASCENDING), ("status", ASCENDING)], {}),
    ("refunds", [("payment_id", ASCENDING)], {}),
    ("itinerary_versions", [("trip_id", ASCENDING), ("version", ASCENDING)], {"unique": True}),
    ("trips", [("user_id", ASCENDING)], {}),
    ("audit_log", [("trip_id", ASCENDING), ("ts", ASCENDING)], {}),
    ("audit_log", [("user_id", ASCENDING), ("ts", ASCENDING)], {}),
    ("conversations", [("user_id", ASCENDING), ("updated_at", DESCENDING)], {}),
    ("agent_state", [("trip_id", ASCENDING)], {"unique": True}),
    ("user_memory", [("user_id", ASCENDING)], {}),
]


def create_indexes_for(collection: Collection, name: str) -> None:
    """Create the indexes of collection ``name`` on ``collection`` (can be a temporary collection)."""
    models = [IndexModel(keys, **options) for col, keys, options in INDEXES if col == name]
    if models:
        collection.create_indexes(models)


def ensure_indexes(db: Database) -> list[str]:
    """Create all indexes (no-op for existing ones). Keeps going past failures; returns them."""
    failures = []
    for name in dict.fromkeys(col for col, _, _ in INDEXES):
        try:
            create_indexes_for(db[name], name)
        except PyMongoError as exc:
            logger.error("Could not create indexes on `%s`: %s", name, exc)
            failures.append(name)
    return failures
