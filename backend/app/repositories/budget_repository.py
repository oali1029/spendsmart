"""Repository layer: database access for monthly budgets."""
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget import MonthlyBudget


class BudgetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_month(self, month_start: date) -> MonthlyBudget | None:
        return self.db.scalar(select(MonthlyBudget).where(MonthlyBudget.month == month_start))

    def upsert(self, month_start: date, amount: Decimal) -> MonthlyBudget:
        """Create the month's budget, or change its amount if one already exists."""
        budget = self.get_by_month(month_start)
        if budget is None:
            budget = MonthlyBudget(month=month_start, amount=amount)
            self.db.add(budget)
        else:
            budget.amount = amount
        self.db.commit()
        self.db.refresh(budget)
        return budget
