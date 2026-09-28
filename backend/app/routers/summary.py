"""Router layer for the monthly summary. HTTP only."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.summary import MonthlySummary
from app.services.summary_service import SummaryService

router = APIRouter(prefix="/summary", tags=["summary"])


def get_service(db: Session = Depends(get_db)) -> SummaryService:
    return SummaryService(db)


# month is required here (unlike the expense list): a summary is always "for a month".
@router.get("", response_model=MonthlySummary)
def get_summary(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", examples=["2026-09"]),
    service: SummaryService = Depends(get_service),
):
    return service.get_summary(month)
