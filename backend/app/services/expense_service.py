"""Service layer: business rules for expenses.

Spending Guard (category-limit warnings) will be added here, since it is a business rule
that runs when an expense is created or changed.
"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.months import month_bounds
from app.models.expense import Expense
from app.repositories.category_repository import CategoryRepository
from app.repositories.expense_repository import ExpenseRepository
from app.schemas.expense import ExpenseWrite


class ExpenseService:
    def __init__(self, db: Session):
        self.repo = ExpenseRepository(db)
        # Needed to validate that an expense points at a real category.
        self.categories = CategoryRepository(db)

    def list_expenses(self, month: str | None, category_id: int | None) -> list[Expense]:
        # No month means "all time": (None, None) applies no date filter.
        start, end = month_bounds(month) if month else (None, None)
        return self.repo.list(start, end, category_id)

    def get_expense(self, expense_id: int) -> Expense:
        expense = self.repo.get(expense_id)
        if expense is None:
            raise NotFoundError(f"Expense {expense_id} not found")
        return expense

    def create_expense(self, data: ExpenseWrite) -> Expense:
        self._ensure_category_exists(data.category_id)
        expense = Expense(**data.model_dump())
        return self.repo.create(expense)

    def update_expense(self, expense_id: int, data: ExpenseWrite) -> Expense:
        expense = self.get_expense(expense_id)
        # The category may have changed in this update, so it must be re-validated.
        self._ensure_category_exists(data.category_id)
        for field, value in data.model_dump().items():
            setattr(expense, field, value)
        return self.repo.save(expense)

    def delete_expense(self, expense_id: int) -> None:
        self.repo.delete(self.get_expense(expense_id))

    def _ensure_category_exists(self, category_id: int) -> None:
        # 404 with a clear message, instead of letting the FK violation surface as a 500.
        if self.categories.get(category_id) is None:
            raise NotFoundError(f"Category {category_id} not found")
