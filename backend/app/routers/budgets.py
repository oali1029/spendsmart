"""Router layer for monthly budgets. HTTP only."""
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.budget import BudgetRead, BudgetWrite
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])

# Same YYYY-MM rule as the expense filter; guarantees a valid month before the service runs.
MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


def get_service(db: Session = Depends(get_db)) -> BudgetService:
    return BudgetService(db)


@router.get("/{month}", response_model=BudgetRead)
def get_budget(
    month: str = Path(pattern=MONTH_PATTERN, examples=["2026-09"]),
    service: BudgetService = Depends(get_service),
):
    return service.get_budget(month)


# PUT (not POST): the month in the URL identifies the resource, and repeating the same request
# has the same result (idempotent). It creates the budget or updates it, so it always returns 200.
@router.put("/{month}", response_model=BudgetRead)
def set_budget(
    data: BudgetWrite,
    month: str = Path(pattern=MONTH_PATTERN, examples=["2026-09"]),
    service: BudgetService = Depends(get_service),
):
    return service.set_budget(month, data)
