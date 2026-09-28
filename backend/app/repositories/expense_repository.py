"""Repository layer: the only place that talks to the database for expenses."""
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.expense import Expense


class ExpenseRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        start: date | None = None,
        end: date | None = None,
        category_id: int | None = None,
    ) -> list[Expense]:
        """Expenses with start <= expense_date < end, optionally for one category. Newest first."""
        # Build the query up from whichever filters were supplied; unused filters add no SQL.
        query = select(Expense)
        if start is not None:
            query = query.where(Expense.expense_date >= start)
        if end is not None:
            query = query.where(Expense.expense_date < end)  # exclusive, so no overlap between months
        if category_id is not None:
            query = query.where(Expense.category_id == category_id)
        # id as a tiebreaker keeps the order stable for expenses on the same day.
        query = query.order_by(Expense.expense_date.desc(), Expense.id.desc())
        return list(self.db.scalars(query))

    def total_by_category(self, start: date, end: date) -> dict[int, Decimal]:
        """Total spent per category for start <= expense_date < end.

        The database does the summing (GROUP BY) instead of loading every expense into Python.
        Categories with no expenses in the range are simply absent from the result.
        """
        query = (
            select(Expense.category_id, func.sum(Expense.amount))
            .where(Expense.expense_date >= start, Expense.expense_date < end)
            .group_by(Expense.category_id)
        )
        return {category_id: total for category_id, total in self.db.execute(query)}

    def get(self, expense_id: int) -> Expense | None:
        return self.db.get(Expense, expense_id)

    def create(self, expense: Expense) -> Expense:
        self.db.add(expense)
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def save(self, expense: Expense) -> Expense:
        """Persist changes already applied to a loaded expense."""
        # The object is tracked by the session, so setting its fields is enough; commit sends the UPDATE.
        self.db.commit()
        self.db.refresh(expense)
        return expense

    def delete(self, expense: Expense) -> None:
        self.db.delete(expense)
        self.db.commit()
