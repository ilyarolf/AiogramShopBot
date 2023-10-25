from sqlalchemy import select, func

from db import async_session_maker
from models.item import Item


class ItemService:
    @staticmethod
    async def get_by_primary_key(item_id: int) -> Item:
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = await session.execute(stmt)
            return item.fetchone()

    @staticmethod
    async def get_categories() -> list[dict]:
        async with async_session_maker() as session:
            stmt = select(Item.category).distinct()
            category_list = await session.execute(stmt)
            return category_list.mappings().all()

    @staticmethod
    async def filter_by_category(category: str) -> list[dict]:
        async with async_session_maker() as session:
            stmt = select(Item).distinct().where(Item.category == category)
            subcategory_list = await session.execute(stmt)
            return subcategory_list.mappings().all()

    @staticmethod
    async def get_available_quantity(subcategory: str) -> int:
        async with async_session_maker() as session:
            stmt = select(func.count()).select_from(Item).where(
                Item.is_sold == 0 and Item.subcategory == subcategory)
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
            bought_items = await session.execute(stmt)
            return bought_items.scalars()

    @staticmethod
    async def set_items_sold(sold_items: list[Item]):
        #TODO("Doesn't work")
        async with async_session_maker() as session:
            for item in sold_items:
                item.is_sold = True
            await session.commit()

