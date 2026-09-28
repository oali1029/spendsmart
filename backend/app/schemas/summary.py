from decimal import Decimal

from pydantic import BaseModel


class CategorySpending(BaseModel):
    category_id: int
    name: str
    spent: Decimal
    # The category's Spending Guard limit (None = no limit), included so the dashboard can show
    # spent-vs-limit from this one response.
    monthly_limit: Decimal | None


class MonthlySummary(BaseModel):
    month: str
    # None when no budget has been set for the month; the summary still works without one.
    budget: Decimal | None
    total_spent: Decimal
    # budget - total_spent. None if there is no budget. NEGATIVE if overspent (deliberately not
    # clamped to zero, so the client can show by how much the budget was exceeded).
    remaining: Decimal | None
    categories: list[CategorySpending]
