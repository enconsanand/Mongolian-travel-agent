from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base class with default CRUD operations using SQLAlchemy 2.0 style."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    def get(self, db: Session, id: UUID) -> ModelType | None:
        """Retrieve a single record by ID."""
        return db.get(self.model, id)

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Retrieve multiple records with pagination."""
        stmt = select(self.model).order_by(desc(self.model.id)).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    def get_multi_with_count(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[int, list[ModelType]]:
        """Retrieve multiple records with total count for pagination."""
        total = self.count(db)
        items = self.get_multi(db, skip=skip, limit=limit)
        return total, items

    def count(self, db: Session) -> int:
        """Return total count of records."""
        stmt = select(func.count()).select_from(self.model)
        return db.scalar(stmt) or 0

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record. Flushes only; the caller owns the transaction."""
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update an existing record. Flushes only; the caller owns the transaction."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: UUID) -> ModelType:
        """Delete a record by ID. Flushes only; the caller owns the transaction."""
        obj = db.get(self.model, id)
        if obj is None:
            raise ValueError(f"{self.model.__name__}({id}) not found")
        db.delete(obj)
        db.flush()
        return obj
