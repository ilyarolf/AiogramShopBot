import math

from sqlalchemy import select, func, update, distinct

import config
from db import session_maker
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory


class ItemService:
    items_per_page = config.PAGE_ENTRIES

    @staticmethod
    def get_by_primary_key(item_id: int) -> Item:
        with session_maker() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = session.execute(stmt)
            return item.scalar()

    @staticmethod
    def get_available_quantity(subcategory_id: int) -> int:
        with session_maker() as session:
            stmt = select(func.count(Item.id)).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
            available_quantity = session.execute(stmt)
            return available_quantity.scalar()

    @staticmethod
    def get_description(subcategory_id: int) -> str:
        with session_maker() as session:
            stmt = select(Item.description, Item.subcategory_id).join(Subcategory,
                                                                      Item.subcategory_id == Subcategory.id).where(
                Item.subcategory_id == subcategory_id).limit(1)
            description = session.execute(stmt)
            return description.scalar()

    @staticmethod
    def get_bought_items(subcategory_id: int, quantity: int):
        with session_maker() as session:
            stmt = select(Item).join(Subcategory, Item.subcategory_id == Subcategory.id).where(
                Subcategory.id == subcategory_id,
                Item.is_sold == 0).limit(quantity)
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
    def get_unsold_subcategories_by_category(category_id: int, page) -> list[Item]:
        with session_maker() as session:
            stmt = select(Item).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
                Item.category_id == category_id, Item.is_sold == 0).group_by(Subcategory.name).limit(
                ItemService.items_per_page).offset(ItemService.items_per_page * page)
            subcategories = session.execute(stmt)
            return subcategories.scalars().all()

    @staticmethod
    def get_maximum_page(category_id: int):
        with session_maker() as session:
            subquery = select(Item.subcategory_id).where(Item.category_id == category_id, Item.is_sold == 0)
            stmt = select(func.count(distinct(subquery.c.subcategory_id)))
            maximum_page = session.execute(stmt)
            maximum_page = maximum_page.scalar_one()
            if maximum_page % ItemService.items_per_page == 0:
                return maximum_page / ItemService.items_per_page - 1
            else:
                return math.trunc(maximum_page / ItemService.items_per_page)

    @staticmethod
    def get_price_by_subcategory(subcategory_id: int) -> float:
        with session_maker() as session:
            stmt = select(Item.price).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
                Subcategory.id == subcategory_id)
            price = session.execute(stmt)
            return price.scalar()

    @staticmethod
    def set_items_not_new():
        with session_maker() as session:
            stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
            session.execute(stmt)
            session.commit()

    @staticmethod
    def delete_unsold_with_category_id(category_id: int):
        with session_maker() as session:
            stmt = select(Item).where(Item.category_id == category_id, Item.is_sold == 0)
            items = session.execute(stmt)
            items = items.scalars().all()
            for item in items:
                session.delete(item)
            session.commit()

    @staticmethod
    def delete_with_subcategory_id(subcategory_id):
        with session_maker() as session:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
            categories = session.execute(stmt)
            categories = categories.scalars().all()
            for category in categories:
                session.delete(category)
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
