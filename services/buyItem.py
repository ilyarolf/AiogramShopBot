from sqlalchemy import select
from db import session_execute, session_commit, get_db_session
from models.buyItem import BuyItem
from models.item import Item


class BuyItemService:

    @staticmethod
    async def insert_many(item_collection: list[Item], buy_id: int):
        for item in item_collection:
            await BuyItemService.insert_new(item, buy_id)

    @staticmethod
    async def insert_new(item: Item, buy_id: int):
        async with get_db_session() as session:
            new_buy = BuyItem(buy_id=buy_id, item_id=item.id)
            session.add(new_buy)
            await session_commit(session)

    @staticmethod
    async def get_buy_item_by_buy_id(buy_id: int) -> BuyItem:
        async with get_db_session() as session:
            stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
            item_subcategory = await session_execute(stmt, session)
            return item_subcategory.scalar()
