"""Router layer: HTTP only. Parse the request, call the service, return the response.

No business rules or queries here.
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryRead, CategoryWrite
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


def get_service(db: Session = Depends(get_db)) -> CategoryService:
    # Dependency injection: the service gets this request's DB session. Tests can swap get_db out.
    return CategoryService(db)


# response_model filters the output through CategoryRead, so only the declared fields are returned.
@router.get("", response_model=list[CategoryRead])
def list_categories(service: CategoryService = Depends(get_service)):
    return service.list_categories()


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryWrite, service: CategoryService = Depends(get_service)):
    return service.create_category(data)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, service: CategoryService = Depends(get_service)):
    return service.get_category(category_id)


# PUT replaces the whole resource: sending monthly_limit as null clears the limit.
@router.put("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, data: CategoryWrite, service: CategoryService = Depends(get_service)
):
    return service.update_category(category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, service: CategoryService = Depends(get_service)):
    service.delete_category(category_id)
    # 204 means "no content", so we return an empty response explicitly.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
