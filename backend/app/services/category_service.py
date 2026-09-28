"""Service layer: business rules for categories.

Sits between the router (HTTP) and the repository (database). It decides *what is allowed*
and raises domain exceptions; it neither builds HTTP responses nor writes SQL.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryWrite


class CategoryService:
    def __init__(self, db: Session):
        self.repo = CategoryRepository(db)

    def list_categories(self) -> list[Category]:
        return self.repo.list_all()

    def get_category(self, category_id: int) -> Category:
        category = self.repo.get(category_id)
        if category is None:
            raise NotFoundError(f"Category {category_id} not found")
        return category

    def create_category(self, data: CategoryWrite) -> Category:
        name = data.name.strip()
        # Check first so the common case gets a clear 409 message...
        self._ensure_name_free(name)
        try:
            return self.repo.create(name, data.monthly_limit)
        except IntegrityError:
            # ...but two requests can race past that check, so the database's unique constraint
            # is the real guard. Roll back so the session is usable again, then report a conflict.
            self.repo.db.rollback()
            raise ConflictError(f"Category '{name}' already exists")

    def update_category(self, category_id: int, data: CategoryWrite) -> Category:
        category = self.get_category(category_id)
        name = data.name.strip()
        # Only check for duplicates if the name actually changed; keeping the same name is fine.
        if name != category.name:
            self._ensure_name_free(name)
        try:
            return self.repo.update(category, name, data.monthly_limit)
        except IntegrityError:
            self.repo.db.rollback()
            raise ConflictError(f"Category '{name}' already exists")

    def delete_category(self, category_id: int) -> None:
        category = self.get_category(category_id)
        # Deleting would orphan (or destroy) the category's expenses, so refuse rather than cascade.
        if self.repo.has_expenses(category_id):
            raise ConflictError("Category still has expenses; delete or reassign them first")
        try:
            self.repo.delete(category)
        except IntegrityError:
            # An expense was added after the check above; the FK (ON DELETE RESTRICT) caught it.
            self.repo.db.rollback()
            raise ConflictError("Category still has expenses; delete or reassign them first")

    def _ensure_name_free(self, name: str) -> None:
        if self.repo.get_by_name(name) is not None:
            raise ConflictError(f"Category '{name}' already exists")
