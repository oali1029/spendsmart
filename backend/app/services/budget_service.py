"""Service layer: business rules for monthly budgets."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.months import month_bounds
from app.models.budget import MonthlyBudget
from app.repositories.budget_repository import BudgetRepository
from app.schemas.budget import BudgetWrite


class BudgetService:
    def __init__(self, db: Session):
        self.repo = BudgetRepository(db)

    def get_budget(self, month: str) -> MonthlyBudget:
        # Normalise "2026-09" to its first day; this is the only key the table ever uses.
        month_start, _ = month_bounds(month)
        budget = self.repo.get_by_month(month_start)
        if budget is None:
            raise NotFoundError(f"No budget set for {month}")
        return budget

    def set_budget(self, month: str, data: BudgetWrite) -> MonthlyBudget:
        month_start, _ = month_bounds(month)
        try:
            return self.repo.upsert(month_start, data.amount)
        except IntegrityError:
            # Two first-time PUTs for the same month raced; the unique constraint rejected one.
            # The client can simply retry (the second attempt becomes an update).
            self.repo.db.rollback()
            raise ConflictError(f"Budget for {month} was set concurrently; please retry")
