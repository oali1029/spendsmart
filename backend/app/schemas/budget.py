from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class BudgetWrite(BaseModel):
    """Body for PUT /budgets/{month}. The month comes from the URL, not the body."""

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month: date  # stored as the 1st of the month...
    amount: Decimal

    @field_serializer("month")
    def _month_as_year_month(self, value: date) -> str:
        # ...but exposed as "2026-09", the same format the client used in the URL.
        # The "first of the month" storage detail never leaks out of the API.
        return value.strftime("%Y-%m")
