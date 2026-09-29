from typing import Any

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    # Every model defines its own mapped ``id`` column; this non-mapped annotation
    # just lets generic code (e.g. CRUDBase) reference ``model.id`` for typing.
    id: Any

    # Generate __tablename__ automatically from the class name.
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
