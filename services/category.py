from sqlalchemy import select

from db import session_maker
from models.category import Category
from models.item import Item


class CategoryService:
    @staticmethod
    def get_or_create_one(category_name: str) -> Category:
        with session_maker() as session:
            stmt = select(Category).where(Category.name == category_name)
            category = session.execute(stmt)
            category = category.scalar()
            if category is None:
                new_category_obj = Category(name=category_name)
                session.add(new_category_obj)
                session.commit()
                session.refresh(new_category_obj)
                return new_category_obj
            else:
                return category

    @staticmethod
    def get_by_primary_key(primary_key: int) -> Category:
        with session_maker() as session:
            stmt = select(Category).where(Category.id == primary_key)
            category = session.execute(stmt)
            return category.scalar()

    @staticmethod
    def get_all_categories():
        with session_maker() as session:
            stmt = select(Category).distinct()
            categories = session.execute(stmt)
            return categories.scalars().all()

    @staticmethod
    def get_unsold() -> list[Category]:
        with session_maker() as session:
            stmt = select(Category).join(Item, Item.category_id == Category.id).where(Item.is_sold == 0).distinct()
            category_names = session.execute(stmt)
            return category_names.scalars().all()
