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
                .where(Item.category_id == category_id, Item.is_sold is False)
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES))
        async with get_db_session() as session:
            subcategories = await session_execute(stmt, session)
            subcategories = subcategories.scalars().all()
            return [SubcategoryDTO.model_validate(subcategory, from_attributes=True) for subcategory in subcategories]

    @staticmethod
    async def max_page(category_id: int) -> int:
        subquery = (select(Subcategory)
                    .join(Item.subcategory_id == Subcategory.id)
                    .where(Item.category_id == category_id,
                           Item.is_sold == False).distinct())
        stmt = select(func.count(subquery))
        async with get_db_session() as session:
            maximum_page = await session_execute(stmt, session)
            maximum_page = maximum_page.scalar_one()
            if maximum_page % config.PAGE_ENTRIES == 0:
                return maximum_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(maximum_page / config.PAGE_ENTRIES)
