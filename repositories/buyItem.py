from sqlalchemy import select
from db import get_db_session, session_execute, session_commit
from models.buyItem import BuyItem, BuyItemDTO


class BuyItemRepository:
    @staticmethod
    async def get_single_by_buy_id(buy_id: int):
        stmt = select(BuyItem).where(BuyItem.buy_id == buy_id).limit(1)
        async with get_db_session() as session:
            item_subcategory = await session_execute(stmt, session)
            return BuyItemDTO.model_validate(item_subcategory.scalar(), from_attributes=True)

    @staticmethod
    async def create_many(buy_item_dto_list: list[BuyItemDTO]):
        async with get_db_session() as session:
            for buy_item_dto in buy_item_dto_list:
                session.add(BuyItem(**buy_item_dto.model_dump()))
            await session_commit(session)