from sqlalchemy import select, func, update

from db import session_maker
from models.buyItem import BuyItem
from models.item import Item


class ItemService:
    @staticmethod
    def get_by_primary_key(item_id: int) -> Item:
        with session_maker() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = session.execute(stmt)
            return item.scalar()

    @staticmethod
    def get_unsold_categories() -> list[dict]:
        with session_maker() as session:
            stmt = select(Item.category).where(Item.is_sold == 0).distinct()
            category_list = session.execute(stmt)
            return category_list.mappings().all()

    @staticmethod
    def get_all_categories() -> list[dict]:
        with session_maker() as session:
            stmt = select(Item.category).distinct()
            category_list = session.execute(stmt)
            return category_list.mappings().all()

    @staticmethod
    def get_available_quantity(subcategory: str) -> int:
        with session_maker() as session:
            stmt = (
                select(func.count())
                .select_from(Item)
                .where(Item.is_sold == 0)
                .where(Item.subcategory == subcategory)
            )
            available_quantity = session.execute(stmt)
            return available_quantity.scalar()

    @staticmethod
    def get_description(subcategory: str) -> str:
        with session_maker() as session:
            stmt = select(Item.description).where(Item.subcategory == subcategory).distinct()
            description = session.execute(stmt)
            return description.scalar()

    @staticmethod
    def get_bought_items(subcategory: str, quantity: int):
        with session_maker() as session:
            stmt = select(Item).where(Item.subcategory == subcategory, Item.is_sold == 0).limit(quantity)
            result = session.execute(stmt)
            bought_items = result.scalars().all()
            return list(bought_items)

    @staticmethod
    def set_items_sold(sold_items: list[Item]):
        with session_maker() as session:
            for item in sold_items:
                item = session.merge(item)
                item.is_sold = 1
            session.commit()

    @staticmethod
    def get_items_by_buy_id(buy_id: int) -> list:
        with session_maker() as session:
            stmt = (
                select(Item)
                .join(BuyItem, BuyItem.item_id == Item.id)
                .where(BuyItem.buy_id == buy_id)
            )
            result = session.execute(stmt)
            items = result.scalars().all()
            return items

    @staticmethod
    def get_unsold_subcategories_by_category(category: str) -> list[str]:
        with session_maker() as session:
            stmt = select(Item.subcategory).where(Item.category == category, Item.is_sold == 0).distinct()
            subcategories = session.execute(stmt)
            return subcategories.scalars().all()

    @staticmethod
    def get_price_by_subcategory(subcategory: str) -> float:
        with session_maker() as session:
            stmt = select(Item.price).where(Item.subcategory == subcategory).limit(1)
            price = session.execute(stmt)
            return price.scalar()

    @staticmethod
    def set_items_not_new():
        with session_maker() as session:
            stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
            session.execute(stmt)
            session.commit()

    @staticmethod
    def get_unsold_subcategories():
        with session_maker() as session:
            stmt = select(Item.subcategory).where(Item.is_sold == 0).distinct()
            subcategories = session.execute(stmt)
            subcategories = subcategories.scalars().all()
            return subcategories

    @staticmethod
    def get_all_subcategories():
        with session_maker() as session:
            stmt = select(Item.subcategory).distinct()
            subcategories = session.execute(stmt)
            subcategories = subcategories.scalars().all()
            return subcategories

    @staticmethod
    def delete_category(category_name: str):
        with session_maker() as session:
            stmt = select(Item).where(Item.category == category_name, Item.is_sold == 0)
            categories = session.execute(stmt)
            categories = categories.scalars().all()
            for category in categories:
                session.delete(category)
            session.commit()

    @staticmethod
    def delete_subcategory(subcategory: str):
        with session_maker() as session:
            stmt = select(Item).where(Item.subcategory == subcategory, Item.is_sold == 0)
            subcategory_items = session.execute(stmt)
            subcategory_items = subcategory_items.scalars().all()
            for item in subcategory_items:
                session.delete(item)
            session.commit()

    @staticmethod
    def add_many(new_items: list[Item]):
        with session_maker() as session:
            session.add_all(new_items)
            session.commit()

    @staticmethod
    def get_new_items():
        with session_maker() as session:
            stmt = select(Item).where(Item.is_new == 1)
            new_items = session.execute(stmt)
            new_items = new_items.scalars().all()
            return new_items
