import math

from sqlalchemy import select, func

import config
from db import get_db_session, session_execute, session_commit, session_refresh
from models.category import Category, CategoryDTO
from models.item import Item


class CategoryRepository:
    @staticmethod
    async def get(page: int) -> list[CategoryDTO]:
        stmt = select(Category).join(Item, Item.category_id == Category.id).where(
            Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
            page * config.PAGE_ENTRIES).group_by(Category.name)
        async with get_db_session() as session:
            category_names = await session_execute(stmt, session)
            categories = category_names.scalars().all()
            return [CategoryDTO.model_validate(category, from_attributes=True) for category in categories]

    @staticmethod
    async def get_maximum_page() -> int:
        unique_categories_subquery = (
            select(Category.id)
            .join(Item, Item.category_id == Category.id)
            .filter(Item.is_sold == 0)
            .distinct()
        ).alias('unique_categories')
        stmt = select(func.count()).select_from(unique_categories_subquery)
        async with get_db_session() as session:
            max_page = await session_execute(stmt, session)
            max_page = max_page.scalar_one()
            if max_page % config.PAGE_ENTRIES == 0:
                return max_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(category_id: int):
        stmt = select(Category).where(Category.id == category_id)
        async with get_db_session() as session:
            category = await session_execute(stmt, session)
            return CategoryDTO.model_validate(category.scalar(), from_attributes=True)

    @staticmethod
    async def get_to_delete(page: int) -> list[CategoryDTO]:
        stmt = select(Category).join(Item, Item.category_id == Category.id
                                     ).where(Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
            page * config.PAGE_ENTRIES).group_by(Category.name)
        async with get_db_session() as session:
            categories = await session_execute(stmt, session)
            return [CategoryDTO.model_validate(category, from_attributes=True) for category in
                    categories.scalars().all()]

    @staticmethod
    async def get_or_create(category_name: str):
        stmt = select(Category).where(Category.name == category_name)
        async with get_db_session() as session:
            category = await session_execute(stmt, session)
            category = category.scalar()
            if category is None:
                new_category_obj = Category(name=category_name)
                session.add(new_category_obj)
                await session_commit(session)
                await session_refresh(session, new_category_obj)
                return new_category_obj
            else:
                return category
