import math

from sqlalchemy import select, func

import config
from db import get_db_session, session_execute
from models.item import Item
from models.subcategory import Subcategory, SubcategoryDTO


class SubcategoryRepository:
    @staticmethod
    async def get_paginated_by_category_id(category_id: int, page: int) -> list[SubcategoryDTO]:
        stmt = (select(Subcategory)
                .join(Item, Item.subcategory_id == Subcategory.id)
                .where(Item.category_id == category_id, Item.is_sold == False)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES))
        async with get_db_session() as session:
            subcategories = await session_execute(stmt, session)
            subcategories = subcategories.scalars().all()
            return [SubcategoryDTO.model_validate(subcategory, from_attributes=True) for subcategory in subcategories]

    @staticmethod
    async def max_page(category_id: int) -> int:
        subquery = (select(Subcategory.id)
                    .join(Item, Item.subcategory_id == Subcategory.id)
                    .where(Item.category_id == category_id,
                           Item.is_sold == False)
                    .distinct())
        stmt = select(func.count(subquery))
        async with get_db_session() as session:
            maximum_page = await session_execute(stmt, session)
            maximum_page = maximum_page.scalar_one()
            if maximum_page % config.PAGE_ENTRIES == 0:
                return maximum_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(maximum_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(subcategory_id: int) -> SubcategoryDTO:
        stmt = select(Subcategory).where(Subcategory.id == subcategory_id)
        async with get_db_session() as session:
            subcategory = await session_execute(stmt, session)
            return SubcategoryDTO.model_validate(subcategory.scalar(), from_attributes=True)

    @staticmethod
    async def get_to_delete(page: int) -> list[SubcategoryDTO]:
        stmt = select(Subcategory).join(Item,
                                        Item.subcategory_id == Subcategory.id).where(
            Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
            page * config.PAGE_ENTRIES).group_by(Subcategory.name)
        async with get_db_session() as session:
            subcategories = await session_execute(stmt, session=session)
            return [SubcategoryDTO.model_validate(subcategory, from_attributes=True) for subcategory in
                    subcategories.scalars().all()]

    @staticmethod
    async def get_maximum_page_to_delete() -> int:
        unique_categories_subquery = (
            select(Subcategory.id)
            .join(Item, Item.subcategory_id == Subcategory.id)
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
