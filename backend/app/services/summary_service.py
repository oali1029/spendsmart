"""Service layer: the monthly summary (budget vs. spending).

Read-only: it combines data from three repositories but changes nothing.
Spending Guard will later reuse the same per-category totals.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.months import month_bounds
from app.repositories.budget_repository import BudgetRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.summary import CategorySpending, MonthlySummary


class SummaryService:
    def __init__(self, db: Session):
        self.budgets = BudgetRepository(db)
        self.categories = CategoryRepository(db)
        self.expenses = ExpenseRepository(db)

    def get_summary(self, month: str) -> MonthlySummary:
        start, end = month_bounds(month)

        # One grouped SQL query for all spending; the numbers below are derived from it in Python.
        spent_by_category = self.expenses.total_by_category(start, end)

        # Build the breakdown from ALL categories (not just ones with spending), so the dashboard
        # can show untouched categories and their limits. Missing from the totals means 0 spent.
        breakdown = [
            CategorySpending(
                category_id=category.id,
                name=category.name,
                spent=spent_by_category.get(category.id, Decimal("0")),
                monthly_limit=category.monthly_limit,
            )
            for category in self.categories.list_all()
        ]

        # Total is the sum of the same per-category figures, so the total and the breakdown
        # can never disagree with each other.
        total_spent = sum((item.spent for item in breakdown), Decimal("0"))

        budget = self.budgets.get_by_month(start)
        budget_amount = budget.amount if budget else None
        # No budget -> no "remaining" (None), rather than a misleading number.
        remaining = budget_amount - total_spent if budget_amount is not None else None

        return MonthlySummary(
            month=month,
            budget=budget_amount,
            total_spent=total_spent,
            remaining=remaining,
            categories=breakdown,
        )
