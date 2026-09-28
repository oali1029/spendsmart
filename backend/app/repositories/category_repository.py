"""Repository layer: the only place that talks to the database for categories.

It knows SQL/SQLAlchemy but nothing about business rules or HTTP.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.expense import Expense


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Category]:
        return list(self.db.scalars(select(Category).order_by(Category.name)))

    def get(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self.db.scalar(select(Category).where(Category.name == name))

    def has_expenses(self, category_id: int) -> bool:
        # LIMIT 1: we only need to know whether one exists, not count them all.
        query = select(Expense.id).where(Expense.category_id == category_id).limit(1)
        return self.db.scalar(query) is not None

    # Write methods commit immediately: each request performs a single write, so this is the
    # simplest correct choice. If we later need several writes to succeed or fail together,
    # the commit would move up into the service.
    def create(self, name: str, monthly_limit: Decimal | None) -> Category:
        category = Category(name=name, monthly_limit=monthly_limit)
        self.db.add(category)
        self.db.commit()
        # refresh loads database-generated values (id, created_at) onto the object.
        self.db.refresh(category)
        return category

    def update(self, category: Category, name: str, monthly_limit: Decimal | None) -> Category:
        category.name = name
        category.monthly_limit = monthly_limit
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category: Category) -> None:
        self.db.delete(category)
        self.db.commit()
