import logging
from typing import Any

from pydantic import ValidationError
from pymongo.database import Database

from app import schemas
from app.core.security import get_password_hash
from app.crud._base import CRUDBase
from app.models.user import User

logger = logging.getLogger(__name__)


class CRUDUser(CRUDBase[User, schemas.UserCreate, schemas.UserUpdate]):
    def get_by_email(self, db: Database, email: str) -> User | None:
        doc = self._col(db).find_one({"email": email.strip().lower()})
        try:
            return self._to_model(doc)
        except ValidationError:
            # e.g. a profile imported without login fields: treat as "no usable account", not a 500
            logger.warning("User document for `%s` is not a valid login account.", email)
            return None

    def insert_with_password(self, db: Database, fields: dict[str, Any], password: str) -> User:
        """Insert a user from ``fields`` (may include ``_id`` and profile extras) with a hashed password."""
        db_obj = User.model_validate({**fields, "hashed_password": get_password_hash(password)})
        self._col(db).insert_one(db_obj.to_mongo())
        return db_obj

    def create(self, db: Database, obj_in: schemas.UserCreate) -> User:
        """Create a new user with hashed password."""
        return self.insert_with_password(db, obj_in.model_dump(exclude={"password"}), obj_in.password)

    def update(
        self,
        db: Database,
        db_obj: User,
        obj_in: schemas.UserUpdate | dict[str, Any],
    ) -> User:
        """Update user fields, hashing password if provided."""
        update_data = dict(obj_in) if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)

        if password := update_data.pop("password", None):
            update_data["hashed_password"] = get_password_hash(password)

        return super().update(db=db, db_obj=db_obj, obj_in=update_data)


user = CRUDUser(User, User.collection)
