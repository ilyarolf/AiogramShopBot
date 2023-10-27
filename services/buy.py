from sqlalchemy import select

from db import async_session_maker
from models.buy import Buy
from models.user import User


class BuyService:
    @staticmethod
    async def get_buys_by_buyer_id(buyer_id: int):
        async with async_session_maker() as session:
            stmt = select(Buy).where(Buy.buyer_id == buyer_id)
            buys = await session.execute(stmt)
            return buys.scalars()

    @staticmethod
    async def insert_new(user: User, quantity: int, total_price: float) -> int:
        async with async_session_maker() as session:
            new_buy = Buy(buyer_id=user.id, quantity=quantity, total_price=total_price)
            session.add(new_buy)
            await session.commit()
            await session.refresh(new_buy)
            return new_buy.id

    @staticmethod
    async def get_not_refunded_buy_ids():
        async with async_session_maker() as session:
            stmt = select(Buy.id).where(Buy.is_refunded == 0)
            not_refunded_buys = await session.execute(stmt)
            return not_refunded_buys.scalars().all()