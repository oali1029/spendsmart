"""Health endpoints, used by humans now and by a load balancer later."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services import health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def liveness() -> dict[str, str]:
    """Is the process up? Does not touch the database."""
    return {"status": "ok"}


@router.get("/db")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Can the app reach PostgreSQL? Returns 503 if not."""
    if not health_service.database_is_reachable(db):
        # 503 (temporarily unavailable) rather than 500: the app is fine, a dependency is down.
        raise HTTPException(status_code=503, detail="database unreachable")
    return {"status": "ok", "database": "ok"}
