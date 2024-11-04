import math
from typing import Union

from sqlalchemy import select, func, update, distinct, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute, session_commit
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory


class ItemService:

    @staticmethod
    async def get_by_primary_key(item_id: int, session: Union[AsyncSession, Session]) -> Item:
        stmt = select(Item).where(Item.id == item_id)
        item = await session_execute(stmt, session)
        return item.scalar()

    @staticmethod
    async def get_available_quantity(subcategory_id: int, session: Union[AsyncSession, Session]) -> int:
        stmt = select(func.count(Item.id)).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
        available_quantity = await session_execute(stmt, session)
        return available_quantity.scalar()

    @staticmethod
    async def get_description(subcategory_id: int, session: Union[AsyncSession, Session]) -> str:
        stmt = select(Item.description, Item.subcategory_id).where(Item.subcategory_id == subcategory_id).limit(1)
        description = await session_execute(stmt, session)
        return description.scalar()

    @staticmethod
    async def get_bought_items(subcategory_id: int, quantity: int, session: Union[AsyncSession, Session]):
        stmt = select(Item).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0).limit(quantity)
        result = await session_execute(stmt, session)
        bought_items = result.scalars().all()
        return list(bought_items)

    @staticmethod
    async def set_items_sold(sold_items: list[Item], session: Union[AsyncSession, Session]):
        for item in sold_items:
            stmt = update(Item).where(Item.id == item.id).values(is_sold=1)
            await session_execute(stmt, session)
        await session.commit()

    @staticmethod
    async def get_items_by_buy_id(buy_id: int, session: Union[AsyncSession, Session]) -> list:
        stmt = (
            select(Item)
            .join(BuyItem, BuyItem.item_id == Item.id)
            .where(BuyItem.buy_id == buy_id)
        )
        result = await session_execute(stmt, session)
        items = result.scalars().all()
        return items

    @staticmethod
    async def get_unsold_subcategories_by_category(category_id: int, page, session: Union[AsyncSession, Session]) -> \
            list[Item]:
        stmt = select(Item).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
            Item.category_id == category_id, Item.is_sold == 0).group_by(Subcategory.name).limit(
            config.PAGE_ENTRIES).offset(config.PAGE_ENTRIES * page)
        subcategories = await session_execute(stmt, session)
        return subcategories.scalars().all()

    @staticmethod
    async def get_maximum_page(category_id: int, session: Union[AsyncSession, Session]):
        subquery = select(Item.subcategory_id).where(Item.category_id == category_id, Item.is_sold == 0)
        stmt = select(func.count(distinct(subquery.c.subcategory_id)))
        maximum_page = await session_execute(stmt, session)
        maximum_page = maximum_page.scalar_one()
        if maximum_page % config.PAGE_ENTRIES == 0:
            return maximum_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(maximum_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_price_by_subcategory(subcategory_id: int, session: Union[AsyncSession, Session]) -> float:
        stmt = select(Item.price).where(Item.subcategory_id == subcategory_id)
        price = await session_execute(stmt, session)
        return price.scalar()

    @staticmethod
    async def set_items_not_new(session: Union[AsyncSession, Session]):
        stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
        await session_execute(stmt, session)
        await session_commit(session)

    @staticmethod
    async def delete_unsold_with_category_id(category_id: int, session: Union[AsyncSession, Session]):
        stmt = delete(Item).where(Item.category_id == category_id, Item.is_sold == 0)
        await session_execute(stmt, session)
        await session_commit(session)

    @staticmethod
    async def delete_with_subcategory_id(subcategory_id, session: Union[AsyncSession, Session]):
        stmt = delete(Item).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
        await session_execute(stmt, session)
        await session_commit(session)

    @staticmethod
    async def add_many(new_items: list[Item], session: Union[AsyncSession, Session]):
        session.add_all(new_items)
        await session_commit(session)

    @staticmethod
    async def get_new_items(session: Union[AsyncSession, Session]) -> list[Item]:
        stmt = select(Item).where(Item.is_new == 1)
        new_items = await session_execute(stmt, session)
        new_items = new_items.scalars().all()
        return new_items
