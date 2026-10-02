from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.database import Database

ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class with default CRUD operations on one MongoDB collection.

    Models are Pydantic models whose ``id`` field is aliased to Mongo's ``_id``.
    """

    def __init__(self, model: type[ModelType], collection: str) -> None:
        self.model = model
        self.collection_name = collection

    def _col(self, db: Database) -> Collection:
        return db[self.collection_name]

    @staticmethod
    def _key(id: str | UUID) -> str:
        # Ids are stored as uuid4().hex (no hyphens), not str(UUID)
        return id.hex if isinstance(id, UUID) else id

    def _to_model(self, doc: dict[str, Any] | None) -> ModelType | None:
        return None if doc is None else self.model.model_validate(doc)

    def get(self, db: Database, id: str | UUID) -> ModelType | None:
        """Retrieve a single record by ID."""
        return self._to_model(self._col(db).find_one({"_id": self._key(id)}))

    def create(self, db: Database, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in.model_dump())
        self._col(db).insert_one(db_obj.model_dump(by_alias=True))
        return db_obj

    def update(self, db: Database, db_obj: ModelType, obj_in: UpdateSchemaType | dict[str, Any]) -> ModelType:
        """Update an existing record with the given fields."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        fields = {k: v for k, v in update_data.items() if k in type(db_obj).model_fields}
        if "updated_at" in type(db_obj).model_fields:
            fields["updated_at"] = datetime.now(UTC)

        db_obj = db_obj.model_copy(update=fields)
        # Re-validate so normalizers (e.g. lower-case email) run on updated values
        db_obj = self.model.model_validate(db_obj.model_dump(by_alias=True))
        self._col(db).update_one({"_id": getattr(db_obj, "id")}, {"$set": db_obj.model_dump(include=set(fields))})
        return db_obj
