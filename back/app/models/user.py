from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _now() -> datetime:
    return datetime.now(UTC)


class User(BaseModel):
    """User document in the ``users`` collection, used for authentication.

    Extra fields (phone, payment_methods, ... from the mock data) are kept as-is.
    """

    collection: ClassVar[str] = "users"

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")

    id: str = Field(default_factory=lambda: uuid4().hex, alias="_id")
    email: str
    hashed_password: str
    first_name: str
    last_name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @field_validator("email")
    @classmethod
    def convert_lower(cls, value: str) -> str:
        """Normalize email to lowercase and strip whitespace."""
        return value.strip().lower()

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"

    def to_mongo(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True)
