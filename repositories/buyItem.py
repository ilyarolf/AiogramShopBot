from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.buyItem import BuyItem, BuyItemDTO


class BuyItemRepository:
    @staticmethod
    async def get_single_by_buy_id(buy_id: int, session: Session | AsyncSession) -> BuyItemDTO:
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
        buy_item = await session_execute(stmt, session)
        return BuyItemDTO.model_validate(buy_item.scalar(), from_attributes=True)

    @staticmethod
    async def create_many(buy_item_dto_list: list[BuyItemDTO], session: Session | AsyncSession):
        for buy_item_dto in buy_item_dto_list:
            session.add(BuyItem(**buy_item_dto.model_dump()))

    @staticmethod
    async def get_all_by_buy_id(buy_id: int, session: Session | AsyncSession) -> list[BuyItemDTO]:
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id)
        buy_items = await session_execute(stmt, session)
        return [BuyItemDTO.model_validate(buy_item, from_attributes=True) for buy_item in buy_items.scalars().all()]
