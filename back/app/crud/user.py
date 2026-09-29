from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.core.security import get_password_hash
from app.crud._base import CRUDBase
from app.models.user import User


class CRUDUser(CRUDBase[User, schemas.UserCreate, schemas.UserUpdate]):
    def get_by_email(self, db: Session, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return db.scalar(stmt)

    def create(self, db: Session, obj_in: schemas.UserCreate) -> User:
        """Create a new user with hashed password. Flushes only; the caller owns the transaction."""
        db_obj = User(
            **obj_in.model_dump(exclude={"password"}),
            hashed_password=get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        db_obj: User,
        obj_in: schemas.UserUpdate | dict[str, Any],
    ) -> User:
        """Update user fields, hashing password if provided."""
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        if password := update_data.pop("password", None):
            update_data["hashed_password"] = get_password_hash(password)

        return super().update(db=db, db_obj=db_obj, obj_in=update_data)


user = CRUDUser(User)
