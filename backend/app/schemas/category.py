"""Pydantic schemas: the shape of request and response bodies.

Kept separate from the SQLAlchemy models so the API contract can differ from the table layout.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryWrite(BaseModel):
    """Body for both create (POST) and full update (PUT)."""

    name: str = Field(min_length=1, max_length=100)
    # gt=0 rejects zero and negatives; max_digits/decimal_places match the Numeric(12, 2) column,
    # so bad input fails with a clear 422 instead of a database error.
    monthly_limit: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)


class CategoryRead(BaseModel):
    # from_attributes lets Pydantic read fields straight off a SQLAlchemy object.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    monthly_limit: Decimal | None
    created_at: datetime
