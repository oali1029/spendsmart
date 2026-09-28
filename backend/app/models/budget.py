from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MonthlyBudget(Base):
    """The overall spending budget for one calendar month."""

    __tablename__ = "monthly_budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored as the FIRST day of the month (2026-09-01 means "September 2026").
    # A real DATE (not a "2026-09" string) keeps it comparable with expense_date.
    # unique=True: at most one budget per month, enforced by the database.
    # The service always normalises to day 1, so the API can never store another day.
    month: Mapped[date] = mapped_column(Date, unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
