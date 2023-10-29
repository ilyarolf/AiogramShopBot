from sqlalchemy import select, update

from db import session_maker
from models.buy import Buy
from models.user import User
from services.user import UserService
from utils.other_sql import RefundBuyDTO


class BuyService:
    @staticmethod
    def get_buys_by_buyer_id(buyer_id: int):
        with session_maker() as session:
            stmt = select(Buy).where(Buy.buyer_id == buyer_id)
            buys = session.execute(stmt)
            return list(buys.scalars().all())

    @staticmethod
    def insert_new(user: User, quantity: int, total_price: float) -> int:
        with session_maker() as session:
            new_buy = Buy(buyer_id=user.id, quantity=quantity, total_price=total_price)
            session.add(new_buy)
            session.commit()
            session.refresh(new_buy)
            return new_buy.id

    @staticmethod
    def get_not_refunded_buy_ids():
        with session_maker() as session:
            stmt = select(Buy.id).where(Buy.is_refunded == 0)
            not_refunded_buys = session.execute(stmt)
            return not_refunded_buys.scalars().all()

    @staticmethod
    def refund(buy_id: int, refund_data: RefundBuyDTO):
        UserService.reduce_consume_records(refund_data.user_id, refund_data.total_price)
        with session_maker() as session:
            stmt = update(Buy).where(Buy.id == buy_id).values(is_refunded=True)
            session.execute(stmt)
            session.commit()
