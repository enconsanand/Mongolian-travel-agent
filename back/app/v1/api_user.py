from fastapi import APIRouter

from app.v1.common import auth

user_router = APIRouter()

# common
user_router.include_router(auth.router, prefix="/auth", tags=["Common - Auth"])
