from enum import IntEnum as PyIntEnum
from typing import TypeVar

from sqlalchemy import Integer, TypeDecorator
from sqlalchemy.engine import Dialect

E = TypeVar("E", bound=PyIntEnum)


class IntEnum(TypeDecorator[E]):
    """
    SQLAlchemy type that stores Python IntEnum values as integers in the database.

    Usage:
        class Status(enum.IntEnum):
            ACTIVE = 1
            INACTIVE = 2

        class MyModel(Base):
            status = Column(IntEnum(Status), nullable=False)
    """

    impl = Integer
    cache_ok = True

    def __init__(self, enumtype: type[E]) -> None:
        super().__init__()
        self._enumtype = enumtype

    def process_bind_param(self, value: E | int | None, dialect: Dialect) -> int | None:
        """Convert enum to integer for database storage."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        return value.value

    def process_result_value(self, value: int | None, dialect: Dialect) -> E | None:
        """Convert integer from database to enum."""
        if value is None:
            return None
        return self._enumtype(value)
