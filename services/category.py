import math

from sqlalchemy import select, func
from db import session_maker
from models.category import Category
from models.item import Item


class CategoryService:
    items_per_page = 20

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
    def get_all_categories(page: int = 0):
        with session_maker() as session:
            stmt = select(Category).distinct().limit(CategoryService.items_per_page).offset(
                page * CategoryService.items_per_page).group_by(Category.name)
            categories = session.execute(stmt)
            return categories.scalars().all()

    @staticmethod
    def get_unsold(page) -> list[Category]:
        with session_maker() as session:
            stmt = select(Category).join(Item, Item.category_id == Category.id).where(
                Item.is_sold == 0).distinct().limit(CategoryService.items_per_page).offset(
                page * CategoryService.items_per_page).group_by(Category.name)
            category_names = session.execute(stmt)
            return category_names.scalars().all()

    @staticmethod
    def get_maximum_page():
        with session_maker() as session:
            stmt = select(func.count(Category.id)).distinct()
            subcategories = session.execute(stmt)
            categories_count = subcategories.scalar_one()
            if categories_count % CategoryService.items_per_page == 0:
                return categories_count / CategoryService.items_per_page - 1
            else:
                return math.trunc(categories_count / CategoryService.items_per_page) - 1
