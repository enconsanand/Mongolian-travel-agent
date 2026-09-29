import uuid

from sqlalchemy import Boolean, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base_class import Base
from app.models.default import Default


class User(Base, Default):
    """User model for authentication and user management."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, server_default=func.uuid_generate_v4()
    )
    email: Mapped[str] = mapped_column(String, index=True, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="True")

    @validates("email")
    def convert_lower(self, key: str, value: str) -> str:
        """Normalize email to lowercase and strip whitespace."""
        return value.strip().lower()

    @property
    def full_name(self) -> str:
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"
