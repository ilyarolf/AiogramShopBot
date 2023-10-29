from sqlalchemy import select

from db import session_maker
from models.buyItem import BuyItem
from models.item import Item


class BuyItemService:

    @staticmethod
    def insert_many(item_collection: list[Item], buy_id: int):
        for item in item_collection:
            BuyItemService.insert_new(item, buy_id)

    @staticmethod
    def insert_new(item: Item, buy_id: int):
        with session_maker() as session:
            new_buy = BuyItem(buy_id=buy_id, item_id=item.id)
            session.add(new_buy)
            session.commit()

    @staticmethod
    def get_buy_item_by_buy_id(buy_id: int) -> BuyItem:
        with session_maker() as session:
            stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
            item_subcategory = session.execute(stmt)
            return item_subcategory.scalar()
