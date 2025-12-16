import math

from sqlalchemy import select, or_, func, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from models.buyItem import BuyItem, BuyItemDTO
from models.item import Item
from models.subcategory import Subcategory


class BuyItemRepository:
    @staticmethod
    async def get_single_by_buy_id(buy_id: int, session: Session | AsyncSession) -> BuyItemDTO:
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
        buy_item = await session_execute(stmt, session)
        return BuyItemDTO.model_validate(buy_item.scalar(), from_attributes=True)

    @staticmethod
    async def create_many(buy_item_dto_list: list[BuyItemDTO], session: Session | AsyncSession):
        for buy_item_dto in buy_item_dto_list:
            session.add(BuyItem(**buy_item_dto.model_dump()))

    @staticmethod
    async def get_all_by_buy_id(buy_id: int, session: Session | AsyncSession) -> list[BuyItemDTO]:
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id)
        buy_items = await session_execute(stmt, session)
        return [BuyItemDTO.model_validate(buy_item, from_attributes=True) for buy_item in buy_items.scalars().all()]

    @staticmethod
    async def get_paginated_by_buy_id(sort_pairs: dict[str, int],
                                      filters: list[str],
                                      buy_id: int,
                                      page: int,
                                      session: AsyncSession) -> list[BuyItemDTO]:
        sort_methods = []
        for sort_property, sort_order in sort_pairs.items():
            sort_property, sort_order = SortProperty(int(sort_property)), SortOrder(sort_order)
            if sort_order != SortOrder.DISABLE:
                table = Subcategory if sort_property.NAME else BuyItem
                sort_column = sort_property.get_column(table)
                sort_method = (getattr(sort_column, sort_order.name.lower()))
                sort_methods.append(sort_method())
        conditions = [
            BuyItem.buy_id == buy_id
        ]
        if filters is not None:
            filter_conditions = [Subcategory.name.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        # SQLITE CRUTCH 🩼
        je = func.json_each(BuyItem.item_ids).table_valued("value").alias("je")
        stmt = (
            select(BuyItem)
            # START SQLITE CRUTCH 🩼
            .distinct(BuyItem.id)
            .join(je, literal_column("1") == literal_column("1"))
            .join(Item, Item.id == je.c.value)
            # END SQLITE CRUTCH 🩼
            # PQSL = .join(Item, Item.id.in_(BuyItem.item_ids)
            .join(Subcategory, Item.subcategory_id == Subcategory.id)
            .where(*conditions)
            .order_by(*sort_methods)
            .limit(config.PAGE_ENTRIES)
            .offset(config.PAGE_ENTRIES * page)
        )
        buy_items = await session_execute(stmt, session)
        return [BuyItemDTO.model_validate(buy_item, from_attributes=True) for buy_item in buy_items.scalars().all()]

    @staticmethod
    async def get_max_page_by_buy_id(buy_id: int, filters: list[str], session: AsyncSession | Session) -> int:
        conditions = [
            BuyItem.buy_id == buy_id
        ]
        if filters is not None:
            filter_conditions = [Subcategory.name.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        # SQLITE CRUTCH 🩼
        je = func.json_each(BuyItem.item_ids).table_valued("value").alias("je")
        sub_stmt = (select(BuyItem)
                    # START SQLITE CRUTCH 🩼
                    .distinct(BuyItem.id)
                    .join(je, literal_column("1") == literal_column("1"))
                    .join(Item, Item.id == je.c.value)
                    # END SQLITE CRUTCH 🩼
                    # PSQL = .join(Item, Item.id.in_(BuyItem.item_ids)
                    .join(Subcategory, Item.subcategory_id == Subcategory.id)
                    .where(*conditions))
        stmt = select(func.count()).select_from(sub_stmt)
        maximum_page = await session_execute(stmt, session)
        maximum_page = maximum_page.scalar_one()
        if maximum_page % config.PAGE_ENTRIES == 0:
            return maximum_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(maximum_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_id(buyItem_id: int, session: AsyncSession) -> BuyItemDTO:
        stmt = select(BuyItem).where(BuyItem.id == buyItem_id)
        buyItem = await session_execute(stmt, session)
        return BuyItemDTO.model_validate(buyItem.scalar_one(), from_attributes=True)
