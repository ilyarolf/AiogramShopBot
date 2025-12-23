import math

from sqlalchemy import select, func, update, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute, session_flush
from enums.item_type import ItemType
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from models.category import Category, CategoryDTO
from models.item import Item
from utils.utils import get_bot_photo_id, calculate_max_page


class CategoryRepository:
    @staticmethod
    async def get(sort_pairs: dict[str, int],
                  filters: list[str] | None,
                  item_type: ItemType | None,
                  page: int,
                  session: AsyncSession) -> list[CategoryDTO]:
        sort_methods = []
        conditions = [
            Item.is_sold == False
        ]
        if item_type:
            conditions.append(
                Item.item_type == item_type
            )
        if filters is not None:
            filter_conditions = [Category.name.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        for sort_property, sort_order in sort_pairs.items():
            sort_property, sort_order = SortProperty(int(sort_property)), SortOrder(sort_order)
            if sort_order != SortOrder.DISABLE:
                table = Category if sort_property == SortProperty.NAME else Item
                sort_column = sort_property.get_column(table)
                sort_method = (getattr(sort_column, sort_order.name.lower()))
                sort_methods.append(sort_method())
        stmt = (select(Category)
                .join(Item, Item.category_id == Category.id)
                .where(and_(*conditions))
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(*sort_methods))
        category_names = await session_execute(stmt, session)
        categories = category_names.scalars().all()
        return [CategoryDTO.model_validate(category, from_attributes=True) for category in categories]

    @staticmethod
    async def get_maximum_page(filters: list[str] | None, session: AsyncSession) -> int:
        conditions = [Item.is_sold == False]
        if filters is not None:
            filter_conditions = [Category.name.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        sub_stmt = (
            select(Category.id)
            .join(Item, Item.category_id == Category.id)
            .where(and_(*conditions))
            .distinct()
        ).alias('unique_categories')
        stmt = select(func.count()).select_from(sub_stmt)
        max_page = await session_execute(stmt, session)
        max_page = max_page.scalar_one()
        return calculate_max_page(max_page)

    @staticmethod
    async def get_by_id(category_id: int, session: Session | AsyncSession) -> CategoryDTO:
        stmt = select(Category).where(Category.id == category_id)
        category = await session_execute(stmt, session)
        return CategoryDTO.model_validate(category.scalar(), from_attributes=True)

    @staticmethod
    async def get_to_delete(sort_pairs: dict[str, int],
                            filters: list[str],
                            page: int, session: AsyncSession) -> list[CategoryDTO]:
        sort_methods = []
        for sort_property, sort_order in sort_pairs.items():
            sort_property, sort_order = SortProperty(int(sort_property)), SortOrder(sort_order)
            if sort_order != SortOrder.DISABLE:
                sort_column = sort_property.get_column(Category)
                sort_method = (getattr(sort_column, sort_order.name.lower()))
                sort_methods.append(sort_method())
        conditions = [
            Item.is_sold == False
        ]
        if filters is not None:
            filter_conditions = [Category.name.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        stmt = (select(Category)
                .join(Item, Item.category_id == Category.id)
                .where(*conditions)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(*sort_methods))
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
