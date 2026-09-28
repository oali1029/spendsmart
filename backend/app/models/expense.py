from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Expense(Base):
    """A single spend. Belongs to exactly one category."""

    __tablename__ = "expenses"
    # Serves both "expenses in a month" and "expenses in a month for a category".
    # Date comes first because every query filters on a month; category narrows it further.
    __table_args__ = (Index("ix_expenses_date_category", "expense_date", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Numeric (exact decimal), never float, because floats can't represent money exactly.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(String(255))
    # The day the money was spent (user-chosen), distinct from created_at (when the row was inserted).
    expense_date: Mapped[date] = mapped_column(Date)
    # RESTRICT: the database itself refuses to delete a category that still has expenses.
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
