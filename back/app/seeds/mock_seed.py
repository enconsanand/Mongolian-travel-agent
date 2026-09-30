import json
import logging
from pathlib import Path

from pymongo.database import Database

from app import crud
from app.core.config import settings
from app.db.mongo import create_indexes_for
from app.db.validators import create_validated_collection, refresh_validator
from app.models.user import User
from app.schemas.commerce import COMMERCE_MODELS
from app.schemas.travel import DOC_MODELS, MockUserDoc

logger = logging.getLogger(__name__)

# Not collections: helper files that live next to the mock data
_SKIP = {"image_pool.json", "images.json", "translations.mn.json"}

# Collections that change while the app runs: what the agent writes (trips, payments, ...) and the
# inventory that bookings use up (free rooms, seats, cars). A normal re-seed never drops or overwrites
# them; it only inserts demo rows that are missing, so real bookings and the inventory they used stay
# consistent. Every other collection is reference data (stays, routes, events...) and is replaced.
STATEFUL_COLLECTIONS = {
    "trips",
    "itinerary_versions",
    "quotes",
    "bookings",
    "payments",
    "refunds",
    "audit_log",
    "conversations",
    "agent_state",
    "user_memory",
    "stay_availability",
    "transport_availability",
    "vehicle_availability",
    "shared_rides",
}


def _load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_all(folder: Path) -> dict[str, list[dict]]:
    """Read and strictly validate every mock file before touching the database."""
    collections: dict[str, list[dict]] = {}
    for path in sorted(folder.glob("*.json")):
        if path.name in _SKIP or path.stem == "users":
            continue
        model = DOC_MODELS.get(path.stem)
        if model is None:
            raise ValueError(f"No schema for mock collection `{path.stem}`; add one to app/schemas/travel.py")
        docs = _load(path)
        for doc in docs:
            # strict: no "3" -> 3 coercion, so what passes here also passes MongoDB's $jsonSchema
            model.model_validate(doc, strict=True)
        collections[path.stem] = docs
    return collections


def _replace_collection(db: Database, name: str, docs: list[dict], real_server: bool) -> None:
    """Build the new collection (validator, indexes, data) under a temp name, then swap it in.

    Readers never see a half-loaded or index-less collection, and a failed insert leaves the
    current collection untouched.
    """
    tmp = f"_seed_tmp_{name}"
    db[tmp].drop()
    if real_server:
        create_validated_collection(db, tmp, schema=name)
        create_indexes_for(db[tmp], name)
    if docs:
        db[tmp].insert_many(docs)
    db[tmp].rename(name, dropTarget=True)


def _add_missing(db: Database, name: str, docs: list[dict], real_server: bool) -> None:
    """Keep existing data; create the collection if needed and insert demo rows that are not there yet."""
    if real_server:
        if name not in db.list_collection_names():
            create_validated_collection(db, name)
        else:
            refresh_validator(db, name)
        create_indexes_for(db[name], name)
    for doc in docs:
        fields = {k: v for k, v in doc.items() if k != "_id"}
        db[name].update_one({"_id": doc["_id"]}, {"$setOnInsert": fields}, upsert=True)


def load_mock_collections(
    db: Database, data_dir: str | None = None, real_server: bool = True, reset: bool = False
) -> None:
    """Load ``data/mock`` into MongoDB.

    All files are validated against ``app.schemas.travel`` first, so a bad file changes nothing.
    Reference collections are replaced. Stateful collections keep their data and only get missing
    demo rows, unless ``reset`` is set: then they are replaced too (wipes real trips/payments; for
    local development only). With ``real_server`` each collection also gets its ``$jsonSchema``
    validator and indexes (mongomock in tests supports neither). The commerce collections are created
    (or, with ``reset``, emptied) as well. ``users`` is handled by ``upsert_mock_users``.
    """
    folder = Path(data_dir or settings.MOCK_DATA_DIR)
    if not folder.is_dir():
        raise FileNotFoundError(f"Mock data folder not found: {folder} (set MOCK_DATA_DIR)")

    for name, docs in _read_all(folder).items():
        if name in STATEFUL_COLLECTIONS and not reset:
            _add_missing(db, name, docs, real_server)
            logger.info("Kept %s, added missing demo docs (%d in file)", name, len(docs))
        else:
            _replace_collection(db, name, docs, real_server)
            logger.info("Loaded %4d docs into %s", len(docs), name)

    # Commerce collections have no mock files; make sure they exist with their validator and indexes. A reset
    # empties them too, since the trips, payments and inventory they point at were just replaced.
    for name in COMMERCE_MODELS:
        if reset:
            db[name].drop()
        _add_missing(db, name, [], real_server)
        logger.info("%s %s (commerce, no mock data)", "Emptied" if reset else "Ensured", name)


def upsert_mock_users(db: Database, password: str, data_dir: str | None = None) -> None:
    """Create the mock travellers as login users.

    Existing accounts keep their password, email, ``created_at`` and ``is_active``; only profile
    fields (phone, saved payment methods, ...) are refreshed.
    """
    path = Path(data_dir or settings.MOCK_DATA_DIR) / "users.json"
    for doc in _load(path):
        MockUserDoc.model_validate(doc, strict=True)
        existing = crud.user.get_by_email(db=db, email=doc["email"])
        if existing:
            if existing.id != doc["_id"]:
                logger.warning(
                    "User `%s` exists with id `%s`, not `%s`; the demo trips for this user will not show up.",
                    doc["email"],
                    existing.id,
                    doc["_id"],
                )
            profile = {k: v for k, v in doc.items() if k not in ("_id", "email", "created_at", "is_active")}
            db[User.collection].update_one({"_id": existing.id}, {"$set": profile})
            logger.info("Updated mock user `%s`.", doc["email"])
            continue
        # created_at comes from the model (a real datetime), like accounts created through the API
        crud.user.insert_with_password(db, {k: v for k, v in doc.items() if k != "created_at"}, password)
        logger.info("Created mock user `%s`.", doc["email"])
