import math

from sqlalchemy import select, func, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute, session_flush
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from models.category import Category
from models.item import Item, ItemDTO
from models.subcategory import Subcategory, SubcategoryDTO
from utils.utils import get_bot_photo_id


class SubcategoryRepository:
    @staticmethod
    async def get_paginated_by_category_id(sort_pairs: dict[SortProperty, SortOrder],
                                           category_id: int | None, page: int,
                                           session: AsyncSession) -> list[ItemDTO]:
        sort_methods = []
        for sort_property, sort_order in sort_pairs.items():
            sort_property, sort_order = SortProperty(int(sort_property)), SortOrder(sort_order)
            if sort_order != SortOrder.DISABLE:
                table = Subcategory if sort_property == SortProperty.NAME else Item
                sort_column = sort_property.get_column(table)
                sort_method = (getattr(sort_column, sort_order.name.lower()))
                sort_methods.append(sort_method())
        conditions = [
            Item.is_sold == False
        ]
        if category_id:
            conditions.append(Item.category_id == category_id)
        stmt = (select(Item.category_id,
                       Item.subcategory_id,
                       Item.description,
                       Item.price,
                       Category.name.label("category_name"),
                       Subcategory.name.label("subcategory_name"))
                .join(Subcategory, Item.subcategory_id == Subcategory.id)
                .join(Category, Item.category_id == Category.id)
                .where(and_(*conditions))
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(*sort_methods))
        items = await session_execute(stmt, session)
        items = items.mappings().all()
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items]

    @staticmethod
    async def max_page(category_id: int | None, session: Session | AsyncSession) -> int:
        conditions = [
            Item.is_sold == False
        ]
        if category_id:
            conditions.append(Item.category_id == category_id)
        subquery = (select(Subcategory.id)
                    .join(Item, Item.subcategory_id == Subcategory.id)
                    .where(and_(*conditions))
                    .distinct())
        stmt = select(func.count()).select_from(subquery)
        maximum_page = await session_execute(stmt, session)
        maximum_page = maximum_page.scalar_one()
        if maximum_page % config.PAGE_ENTRIES == 0:
            return maximum_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(maximum_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(subcategory_id: int, session: Session | AsyncSession) -> SubcategoryDTO:
        stmt = select(Subcategory).where(Subcategory.id == subcategory_id)
        subcategory = await session_execute(stmt, session)
        return SubcategoryDTO.model_validate(subcategory.scalar(), from_attributes=True)

    @staticmethod
    async def get_to_delete(page: int, session: AsyncSession) -> list[SubcategoryDTO]:
        stmt = (select(Subcategory)
                .join(Item, Item.subcategory_id == Subcategory.id)
                .where(Item.is_sold == False)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(Subcategory.name))
        subcategories = await session_execute(stmt, session=session)
        return [SubcategoryDTO.model_validate(subcategory, from_attributes=True) for subcategory in
                subcategories.scalars().all()]

    @staticmethod
    async def get_maximum_page_to_delete(session: AsyncSession) -> int:
        unique_categories_subquery = (
            select(Subcategory.id)
            .join(Item, Item.subcategory_id == Subcategory.id)
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
    async def get_or_create(subcategory_name: str, session: AsyncSession) -> SubcategoryDTO:
        stmt = select(Subcategory).where(Subcategory.name == subcategory_name)
        subcategory = await session_execute(stmt, session)
        subcategory = subcategory.scalar()
        if subcategory is None:
            bot_photo_id = get_bot_photo_id()
            subcategory = Subcategory(name=subcategory_name, media_id=f"0{bot_photo_id}")
            session.add(subcategory)
            await session_flush(session)
        return SubcategoryDTO.model_validate(subcategory, from_attributes=True)

    @staticmethod
    async def update(subcategory_dto: SubcategoryDTO, session: AsyncSession):
        stmt = (update(Subcategory)
                .where(Subcategory.id == subcategory_dto.id)
                .values(**subcategory_dto.model_dump()))
        await session_execute(stmt, session)
