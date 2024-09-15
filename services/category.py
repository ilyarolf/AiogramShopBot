import math

from sqlalchemy import select, func

import config
from db import async_session_maker
from models.category import Category
from models.item import Item


class CategoryService:
    items_per_page = config.PAGE_ENTRIES

    @staticmethod
    async def get_or_create_one(category_name: str) -> Category:
        async with async_session_maker() as session:
            stmt = select(Category).where(Category.name == category_name)
            category = await session.execute(stmt)
            category = category.scalar()
            if category is None:
                new_category_obj = Category(name=category_name)
                session.add(new_category_obj)
                await session.commit()
                await session.refresh(new_category_obj)
                return new_category_obj
            else:
                return category

    @staticmethod
    async def get_by_primary_key(primary_key: int) -> Category:
        async with async_session_maker() as session:
            stmt = select(Category).where(Category.id == primary_key)
            category = await session.execute(stmt)
            return category.scalar()

    @staticmethod
    async def get_all_categories(page: int = 0):
        async with async_session_maker() as session:
            stmt = select(Category).distinct().limit(CategoryService.items_per_page).offset(
                page * CategoryService.items_per_page).group_by(Category.name)
            categories = await session.execute(stmt)
            return categories.scalars().all()

    @staticmethod
    async def get_unsold(page) -> list[Category]:
        async with async_session_maker() as session:
            stmt = select(Category).join(Item, Item.category_id == Category.id).where(
                Item.is_sold == 0).distinct().limit(CategoryService.items_per_page).offset(
                page * CategoryService.items_per_page).group_by(Category.name)
            category_names = await session.execute(stmt)
            return category_names.scalars().all()

    @staticmethod
    async def get_maximum_page():
        async with async_session_maker() as session:
            unique_categories_subquery = (
                select(Category.id)
                .join(Item, Item.category_id == Category.id)
                .filter(Item.is_sold == 0)
                .distinct()
            ).alias('unique_categories')
            stmt = select(func.count()).select_from(unique_categories_subquery)
            max_page = await session.execute(stmt)
            max_page = max_page.scalar_one()
            if max_page % CategoryService.items_per_page == 0:
                return max_page / CategoryService.items_per_page - 1
            else:
                return math.trunc(max_page / CategoryService.items_per_page)

