from sqlalchemy import select, func, update

from db import async_session_maker
from models.buyItem import BuyItem
from models.category import Category
from models.item import Item


class ItemService:
    @staticmethod
    async def get_by_primary_key(item_id: int) -> Item:
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = await session.execute(stmt)
            return item.scalar()

    @staticmethod
    async def get_unsold_categories() -> list[str]:
        async with async_session_maker() as session:
            stmt = select(Category.name).join(Item).where(Item.is_sold == 0).distinct()
            result = await session.execute(stmt)
            category_names = result.scalars().all()
            return category_names

    @staticmethod
    async def get_all_categories() -> list[dict]:
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
    async def get_unsold_subcategories_by_category(category: str) -> list[str]:
        async with async_session_maker() as session:
            stmt = select(Item.subcategory).where(Item.category == category, Item.is_sold == 0).distinct()
            subcategories = await session.execute(stmt)
            return subcategories.scalars().all()

    @staticmethod
    async def get_price_by_subcategory(subcategory: str) -> float:
        async with async_session_maker() as session:
            stmt = select(Item.price).where(Item.subcategory == subcategory).limit(1)
            price = await session.execute(stmt)
            return price.scalar()

    @staticmethod
    async def set_items_not_new():
        async with async_session_maker() as session:
            stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_unsold_subcategories():
        async with async_session_maker() as session:
            stmt = select(Item.subcategory).where(Item.is_sold == 0).distinct()
            subcategories = await session.execute(stmt)
            subcategories = subcategories.scalars().all()
            return subcategories

    @staticmethod
    async def get_all_subcategories():
        async with async_session_maker() as session:
            stmt = select(Item.subcategory).distinct()
            subcategories = await session.execute(stmt)
            subcategories = subcategories.scalars().all()
            return subcategories

    @staticmethod
    async def delete_category(category_name: str):
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.category == category_name, Item.is_sold == 0)
            categories = await session.execute(stmt)
            categories = categories.scalars().all()
            for category in categories:
                await session.delete(category)
            await session.commit()

    @staticmethod
    async def delete_subcategory(subcategory: str):
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.subcategory == subcategory, Item.is_sold == 0)
            subcategory_items = await session.execute(stmt)
            subcategory_items = subcategory_items.scalars().all()
            for item in subcategory_items:
                await session.delete(item)
            await session.commit()

    @staticmethod
    async def add_many(new_items: list[Item]):
        async with async_session_maker() as session:
            session.add_all(new_items)
            await session.commit()

    @staticmethod
    async def get_new_items():
        async with async_session_maker() as session:
            stmt = select(Item).where(Item.is_new == 1)
            new_items = await session.execute(stmt)
            new_items = new_items.scalars().all()
            return new_items
