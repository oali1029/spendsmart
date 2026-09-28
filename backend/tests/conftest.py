import os

# Settings requires DATABASE_URL at import time. Tests never use it (get_db is overridden below).
os.environ.setdefault("DATABASE_URL", "sqlite://")
# Real env vars beat .env, so a developer's TOOL_PROVIDER=mcp can never change what the tests exercise.
os.environ["TOOL_PROVIDER"] = "direct"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def session_factory():
    # One shared in-memory SQLite DB per test, so tests are isolated and need no Postgres.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # SQLite ignores FKs by default

    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db(session_factory):
    """A session on the same in-memory database the `client` fixture uses (for calling tools directly)."""
    session = session_factory()
    yield session
    session.close()
