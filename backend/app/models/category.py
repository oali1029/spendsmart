from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    """An expense category, e.g. "Food". Also carries its Spending Guard limit."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True: enforced by the database, so duplicates are impossible even under concurrent requests.
    name: Mapped[str] = mapped_column(String(100), unique=True)
    # Spending Guard: NULL means "no limit for this category".
    # Numeric (exact decimal), never float, because floats can't represent money exactly.
    monthly_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # server_default: the database fills this in, so it's correct however the row is inserted.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
