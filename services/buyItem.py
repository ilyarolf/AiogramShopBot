from typing import Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute, session_commit
from models.buyItem import BuyItem
from models.item import Item


class BuyItemService:

    @staticmethod
    async def insert_many(item_collection: list[Item], buy_id: int, session: Union[AsyncSession, Session]):
        for item in item_collection:
            await BuyItemService.insert_new(item, buy_id, session)

    @staticmethod
    async def insert_new(item: Item, buy_id: int, session: Union[AsyncSession, Session]):
        new_buy = BuyItem(buy_id=buy_id, item_id=item.id)
        session.add(new_buy)
        await session_commit(session)

    @staticmethod
    async def get_buy_item_by_buy_id(buy_id: int, session: Union[AsyncSession, Session]) -> BuyItem:
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
        item_subcategory = await session_execute(stmt, session)
        return item_subcategory.scalar()
