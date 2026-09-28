"""Database engine and per-request session handling."""
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

# create_engine is lazy: it does not connect until the first query.
# pool_pre_ping tests a pooled connection before using it, so a restarted database
# doesn't cause a burst of "connection closed" errors.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

# autoflush=False: we decide when SQL is sent (at commit), which keeps behaviour predictable.
# expire_on_commit=False: objects stay readable after commit, so we can return them without a re-query.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # Runs even if the request raised, so connections always return to the pool.
        db.close()
