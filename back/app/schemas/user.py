from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str | None = None
    exp: int | None = None
    jti: str | None = None


class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=8, max_length=72)
    is_active: bool | None = None


class UserResponse(UserBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
