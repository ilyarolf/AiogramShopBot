import math

from sqlalchemy import select, func, update, distinct

import config
from db import async_session_maker
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory


class ItemService:
    items_per_page = config.PAGE_ENTRIES

    @staticmethod
    async def get_by_primary_key(item_id: int) -> Item:
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = await session.execute(stmt)
            return item.scalar()

    @staticmethod
    async def get_available_quantity(subcategory_id: int) -> int:
        async with async_session_maker() as session:
            stmt = select(func.count(Item.id)).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
            available_quantity = await session.execute(stmt)
            return available_quantity.scalar()

    @staticmethod
    async def get_description(subcategory_id: int) -> str:
        async with async_session_maker() as session:
            stmt = select(Item.description, Item.subcategory_id).join(Subcategory,
                                                                      Item.subcategory_id == Subcategory.id).where(
                Item.subcategory_id == subcategory_id).limit(1)
            description = await session.execute(stmt)
            return description.scalar()

    @staticmethod
    async def get_bought_items(subcategory_id: int, quantity: int):
        async with async_session_maker() as session:
            stmt = select(Item).join(Subcategory, Item.subcategory_id == Subcategory.id).where(
                Subcategory.id == subcategory_id,
                Item.is_sold == 0).limit(quantity)
            result = await session.execute(stmt)
            bought_items = result.scalars().all()
            return list(bought_items)

    @staticmethod
    async def set_items_sold(sold_items: list[Item]):
        async with async_session_maker() as session:
            for item in sold_items:
                item = await session.merge(item)
                item.is_sold = 1
            await session.commit()

    @staticmethod
    async def get_items_by_buy_id(buy_id: int) -> list:
        async with async_session_maker() as session:
            stmt = (
                select(Item)
                .join(BuyItem, BuyItem.item_id == Item.id)
                .where(BuyItem.buy_id == buy_id)
            )
            result = await session.execute(stmt)
            items = result.scalars().all()
            return items

    @staticmethod
    async def get_unsold_subcategories_by_category(category_id: int, page) -> list[Item]:
        async with async_session_maker() as session:
            stmt = select(Item).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
                Item.category_id == category_id, Item.is_sold == 0).group_by(Subcategory.name).limit(
                ItemService.items_per_page).offset(ItemService.items_per_page * page)
            subcategories = await session.execute(stmt)
            return subcategories.scalars().all()

    @staticmethod
    async def get_maximum_page(category_id: int):
        async with async_session_maker() as session:
            subquery = select(Item.subcategory_id).where(Item.category_id == category_id, Item.is_sold == 0)
            stmt = select(func.count(distinct(subquery.c.subcategory_id)))
            maximum_page = await session.execute(stmt)
            maximum_page = maximum_page.scalar_one()
            if maximum_page % ItemService.items_per_page == 0:
                return maximum_page / ItemService.items_per_page - 1
            else:
                return math.trunc(maximum_page / ItemService.items_per_page)

    @staticmethod
    async def get_price_by_subcategory(subcategory_id: int) -> float:
        async with async_session_maker() as session:
            stmt = select(Item.price).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
                Subcategory.id == subcategory_id)
            price = await session.execute(stmt)
            return price.scalar()

    @staticmethod
    async def set_items_not_new():
        async with async_session_maker() as session:
            stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def delete_unsold_with_category_id(category_id: int):
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.category_id == category_id, Item.is_sold == 0)
            items = await session.execute(stmt)
            items = items.scalars().all()
            for item in items:
                await session.delete(item)
            await session.commit()

    @staticmethod
    async def delete_with_subcategory_id(subcategory_id):
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
            categories = await session.execute(stmt)
            categories = categories.scalars().all()
            for category in categories:
                await session.delete(category)
            await session.commit()

    @staticmethod
    async def add_many(new_items: list[Item]):
        async with async_session_maker() as session:
            session.add_all(new_items)
            await session.commit()

    @staticmethod
    async def get_new_items() -> list[Item]:
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.is_new == 1)
            new_items = await session.execute(stmt)
            new_items = new_items.scalars().all()
            return new_items
