from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.buyItem import BuyItem, BuyItemDTO


class BuyItemRepository:
    @staticmethod
    async def get_single_by_buy_id(buy_id: int, session: Session | AsyncSession):
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
        item_subcategory = await session_execute(stmt, session)
        return BuyItemDTO.model_validate(item_subcategory.scalar(), from_attributes=True)

    @staticmethod
    async def create_many(buy_item_dto_list: list[BuyItemDTO], session: Session | AsyncSession):
        for buy_item_dto in buy_item_dto_list:
            session.add(BuyItem(**buy_item_dto.model_dump()))
