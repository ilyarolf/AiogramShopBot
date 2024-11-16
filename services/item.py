import math
from sqlalchemy import select, func, update, distinct, delete
import config
from db import session_execute, session_commit, get_db_session
from models.buyItem import BuyItem
from models.category import Category
from models.item import Item
from models.subcategory import Subcategory


class ItemService:

    @staticmethod
    async def get_by_primary_key(item_id: int) -> Item:
        async with get_db_session() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = await session_execute(stmt, session)
            return item.scalar()

    @staticmethod
    async def get_available_quantity(subcategory_id: int, category_id: int) -> int:
        async with get_db_session() as session:
            stmt = select(func.count(Item.id)).where(Item.subcategory_id == subcategory_id,
                                                     Item.is_sold == 0, Item.category_id == category_id)
            available_quantity = await session_execute(stmt, session)
            return available_quantity.scalar()

    @staticmethod
    async def get_description(subcategory_id: int, category_id) -> str:
        async with get_db_session() as session:
            stmt = select(Item.description).where(Item.subcategory_id == subcategory_id,
                                                  Item.category_id == category_id).limit(1)
            description = await session_execute(stmt, session)
            return description.scalar()

    @staticmethod
    async def get_bought_items(category_id: int, subcategory_id: int, quantity: int):
        async with get_db_session() as session:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id,
                                      Item.category_id == category_id,
                                      Item.is_sold == 0).limit(quantity)
            result = await session_execute(stmt, session)
            bought_items = result.scalars().all()
            return list(bought_items)

    @staticmethod
    async def set_items_sold(sold_items: list[Item]):
        async with get_db_session() as session:
            for item in sold_items:
                stmt = update(Item).where(Item.id == item.id).values(is_sold=1)
                await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_items_by_buy_id(buy_id: int) -> list:
        async with get_db_session() as session:
            stmt = (
                select(Item)
                .join(BuyItem, BuyItem.item_id == Item.id)
                .where(BuyItem.buy_id == buy_id)
            )
            result = await session_execute(stmt, session)
            items = result.scalars().all()
            return items

    @staticmethod
    async def get_unsold_subcategories_by_category(category_id: int, page) -> \
            list[Item]:
        async with get_db_session() as session:
            stmt = select(Item).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
                Item.category_id == category_id, Item.is_sold == 0).group_by(Subcategory.name).limit(
                config.PAGE_ENTRIES).offset(config.PAGE_ENTRIES * page)
            subcategories = await session_execute(stmt, session)
            return subcategories.scalars().all()

    @staticmethod
    async def get_maximum_page(category_id: int):
        async with get_db_session() as session:
            subquery = select(Item.subcategory_id).where(Item.category_id == category_id, Item.is_sold == 0)
            stmt = select(func.count(distinct(subquery.c.subcategory_id)))
            maximum_page = await session_execute(stmt, session)
            maximum_page = maximum_page.scalar_one()
            if maximum_page % config.PAGE_ENTRIES == 0:
                return maximum_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(maximum_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_price_by_subcategory(subcategory_id: int, category_id: int) -> float:
        async with get_db_session() as session:
            stmt = select(Item.price).where(Item.subcategory_id == subcategory_id, Item.category_id == category_id)
            price = await session_execute(stmt, session)
            return price.scalar()

    @staticmethod
    async def set_items_not_new():
        async with get_db_session() as session:
            stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def delete_unsold_with_category_id(category_id: int):
        async with get_db_session() as session:
            stmt = delete(Item).where(Item.category_id == category_id, Item.is_sold == 0)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def delete_with_subcategory_id(subcategory_id):
        async with get_db_session() as session:
            stmt = delete(Item).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def add_many(new_items: list[Item]):
        async with get_db_session() as session:
            session.add_all(new_items)
            await session_commit(session)

    @staticmethod
    async def get_new_items() -> list[Item]:
        async with get_db_session() as session:
            stmt = select(Item).where(Item.is_new == 1)
            new_items = await session_execute(stmt, session)
            new_items = new_items.scalars().all()
            return new_items

    @staticmethod
    async def get_in_stock_items():
        async with get_db_session() as session:
            stmt = select(Item).where(Item.is_sold == 0)
            items = await session_execute(stmt, session)
            items = items.scalars().all()
            return items
