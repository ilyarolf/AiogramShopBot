from sqlalchemy import select, func, distinct

from db import async_session_maker
from models.buyItem import BuyItem
from models.item import Item


class ItemService:
    @staticmethod
    async def get_by_primary_key(item_id: int) -> Item:
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = await session.execute(stmt)
            return item.scalar()

    @staticmethod
    async def get_categories() -> list[dict]:
        async with async_session_maker() as session:
            stmt = select(Item.category).distinct()
            category_list = await session.execute(stmt)
            return category_list.mappings().all()

    @staticmethod
    async def get_available_quantity(subcategory: str) -> int:
        async with async_session_maker() as session:
            stmt = (
                select(func.count())
                .select_from(Item)
                .where(Item.is_sold == 0)
                .where(Item.subcategory == subcategory)
            )
            available_quantity = await session.execute(stmt)
            return available_quantity.scalar()

    @staticmethod
    async def get_description(subcategory: str) -> str:
        async with async_session_maker() as session:
            stmt = select(Item.description).where(Item.subcategory == subcategory).distinct()
            description = await session.execute(stmt)
            return description.scalar()

    @staticmethod
    async def get_bought_items(subcategory: str, quantity: int):
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.subcategory == subcategory, Item.is_sold == 0).limit(quantity)
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
    async def get_unique_subcategories(category: str) -> list[str]:
        async with async_session_maker() as session:
            stmt = select(Item.subcategory).where(Item.category == category).distinct()
            subcategories = await session.execute(stmt)
            return subcategories.scalars().all()

    @staticmethod
    async def get_price_by_subcategory(subcategory: str) -> float:
        async with async_session_maker() as session:
            stmt = select(Item.price).where(Item.subcategory == subcategory).limit(1)
            price = await session.execute(stmt)
            return price.scalar()
