import math

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute, session_flush
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from models.category import Category, CategoryDTO
from models.item import Item
from utils.utils import get_bot_photo_id


class CategoryRepository:
    @staticmethod
    async def get(sort_property: SortProperty, sort_order: SortOrder,
                  page: int, session: AsyncSession) -> list[CategoryDTO]:
        sort_column = getattr(Category, sort_property.name.lower())
        sort_method = getattr(sort_column, sort_order.name.lower())
        stmt = (select(Category)
                .join(Item, Item.category_id == Category.id)
                .where(Item.is_sold == False)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(sort_method()))
        category_names = await session_execute(stmt, session)
        categories = category_names.scalars().all()
        return [CategoryDTO.model_validate(category, from_attributes=True) for category in categories]

    @staticmethod
    async def get_maximum_page(session: Session | AsyncSession) -> int:
        unique_categories_subquery = (
            select(Category.id)
            .join(Item, Item.category_id == Category.id)
            .filter(Item.is_sold == 0)
            .distinct()
        ).alias('unique_categories')
        stmt = select(func.count()).select_from(unique_categories_subquery)
        max_page = await session_execute(stmt, session)
        max_page = max_page.scalar_one()
        if max_page % config.PAGE_ENTRIES == 0:
            return max_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(category_id: int, session: Session | AsyncSession) -> CategoryDTO:
        stmt = select(Category).where(Category.id == category_id)
        category = await session_execute(stmt, session)
        return CategoryDTO.model_validate(category.scalar(), from_attributes=True)

    @staticmethod
    async def get_to_delete(page: int, session: Session | AsyncSession) -> list[CategoryDTO]:
        stmt = (select(Category)
                .join(Item, Item.category_id == Category.id)
                .where(Item.is_sold == False)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(Category.name))
        categories = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(category, from_attributes=True) for category in
                categories.scalars().all()]

    @staticmethod
    async def get_or_create(category_name: str, session: Session | AsyncSession):
        stmt = select(Category).where(Category.name == category_name)
        category = await session_execute(stmt, session)
        category = category.scalar()
        if category is None:
            bot_photo_id = get_bot_photo_id()
            new_category_obj = Category(name=category_name, media_id=f"0{bot_photo_id}")
            session.add(new_category_obj)
            await session_flush(session)
            return new_category_obj
        else:
            return category

    @staticmethod
    async def update(category_dto: CategoryDTO, session: AsyncSession):
        stmt = (update(Category)
                .where(Category.id == category_dto.id)
                .values(**category_dto.model_dump()))
        await session_execute(stmt, session)
