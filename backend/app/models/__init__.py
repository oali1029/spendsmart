# Import every model here so Base.metadata knows about it (Alembic relies on this).
from app.models.budget import MonthlyBudget  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.expense import Expense  # noqa: F401
