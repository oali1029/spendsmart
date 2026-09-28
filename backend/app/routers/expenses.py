"""Router layer for expenses: HTTP only, delegates everything else to ExpenseService."""
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.expense import ExpenseRead, ExpenseWrite
from app.services.expense_service import ExpenseService

router = APIRouter(prefix="/expenses", tags=["expenses"])


def get_service(db: Session = Depends(get_db)) -> ExpenseService:
    return ExpenseService(db)


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    # The regex guarantees YYYY-MM with a valid month 01-12, so the service can parse it safely.
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-09"]),
    category_id: int | None = None,
    service: ExpenseService = Depends(get_service),
):
    return service.list_expenses(month, category_id)


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(data: ExpenseWrite, service: ExpenseService = Depends(get_service)):
    return service.create_expense(data)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: int, service: ExpenseService = Depends(get_service)):
    return service.get_expense(expense_id)


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(
    expense_id: int, data: ExpenseWrite, service: ExpenseService = Depends(get_service)
):
    return service.update_expense(expense_id, data)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, service: ExpenseService = Depends(get_service)):
    service.delete_expense(expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
