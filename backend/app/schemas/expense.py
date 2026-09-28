from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseWrite(BaseModel):
    """Body for both create (POST) and full update (PUT)."""

    # Must be positive with at most 2 decimals, matching the Numeric(12, 2) column.
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)
    expense_date: date
    # Existence of this category is checked in the service, since it needs a database lookup.
    category_id: int


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    description: str | None
    expense_date: date
    category_id: int
    created_at: datetime
    updated_at: datetime
