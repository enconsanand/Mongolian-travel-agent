from fastapi import APIRouter

from app.api.v1.common import auth, contact_auth

user_router = APIRouter()

# common
user_router.include_router(auth.router, prefix="/auth", tags=["Common - Auth"])

user_router.include_router(contact_auth.router, prefix="/auth", tags=["Common - Auth"])
