from sqlalchemy import select

import config
from db import get_db_session, session_execute, session_commit, session_refresh
from models.buy import Buy, BuyDTO


class BuyRepository:
    @staticmethod
    async def get_by_buyer_id(user_id: int, page: int) -> list[BuyDTO]:
        stmt = select(Buy).where(Buy.buyer_id == user_id).limit(config.PAGE_ENTRIES).offset(
            page * config.PAGE_ENTRIES)
        async with get_db_session() as session:
            buys = await session_execute(stmt, session)
            return [BuyDTO.model_validate(buy, from_attributes=True) for buy in buys.scalars().all()]

    @staticmethod
    async def create(buy_dto: BuyDTO) -> int:
        async with get_db_session() as session:
            buy = Buy(**buy_dto.model_dump())
            session.add(buy)
            await session_commit(session)
            await session_refresh(session, buy)
            return buy.id
