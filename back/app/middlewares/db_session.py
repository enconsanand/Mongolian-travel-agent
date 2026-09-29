import logging

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        db_session = None
        try:
            db_session = SessionLocal()
            request.state.db = db_session
            response = await call_next(request)
            # HTTPExceptions are converted to responses by Starlette before they
            # reach this middleware, so inspect the status code to decide outcome.
            if response.status_code < 400:
                db_session.commit()
            else:
                db_session.rollback()
            return response
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            if db_session:
                db_session.rollback()
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in middleware: {e}")
            if db_session:
                db_session.rollback()
            raise e
        finally:
            if db_session:
                try:
                    db_session.close()
                except SQLAlchemyError as e:
                    logger.error(f"Error closing database session: {e}")
