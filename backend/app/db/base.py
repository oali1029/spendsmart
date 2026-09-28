from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Parent class for all SQLAlchemy models.

    It collects their table definitions in Base.metadata, which Alembic reads to compare
    the models against the real database.
    """
