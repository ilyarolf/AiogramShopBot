import datetime
import math

from sqlalchemy import select, update, func

import config
from db import async_session_maker
from models.buy import Buy
from models.user import User
from services.user import UserService
from utils.other_sql import RefundBuyDTO


class BuyService:
    buys_per_page = config.PAGE_ENTRIES

    @staticmethod
    async def get_buys_by_buyer_id(buyer_id: int, page: int):
        async with async_session_maker() as session:
            stmt = select(Buy).where(Buy.buyer_id == buyer_id).limit(BuyService.buys_per_page).offset(
                page * BuyService.buys_per_page)
            buys = await session.execute(stmt)
            return buys.scalars().all()

    @staticmethod
    async def get_max_page_purchase_history(buyer_id: int):
        async with async_session_maker() as session:
            stmt = select(func.count(Buy.id)).where(Buy.buyer_id == buyer_id)
            max_page = await session.execute(stmt)
            max_page = max_page.scalar_one()
            if max_page % BuyService.buys_per_page == 0:
                return max_page / BuyService.buys_per_page - 1
            else:
                return math.trunc(max_page / BuyService.buys_per_page)

    @staticmethod
    async def insert_new(user: User, quantity: int, total_price: float) -> int:
        async with async_session_maker() as session:
            new_buy = Buy(buyer_id=user.id, quantity=quantity, total_price=total_price)
            session.add(new_buy)
            await session.commit()
            await session.refresh(new_buy)
            return new_buy.id

    @staticmethod
    async def get_not_refunded_buy_ids(page: int):
        async with async_session_maker() as session:
            stmt = select(Buy.id).where(Buy.is_refunded == 0).limit(BuyService.buys_per_page).offset(
                page * BuyService.buys_per_page)
            not_refunded_buys = await session.execute(stmt)
            return not_refunded_buys.scalars().all()

    @staticmethod
    async def refund(buy_id: int, refund_data: RefundBuyDTO):
        await UserService.reduce_consume_records(refund_data.user_id, refund_data.total_price)
        async with async_session_maker() as session:
            stmt = update(Buy).where(Buy.id == buy_id).values(is_refunded=True)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_max_refund_pages():
        async with async_session_maker() as session:
            stmt = select(func.count(Buy.id)).where(Buy.is_refunded == 0)
            not_refunded_buys = await session.execute(stmt)
            not_refunded_buys = not_refunded_buys.scalar_one()
            if not_refunded_buys % BuyService.buys_per_page == 0:
                return not_refunded_buys / BuyService.buys_per_page - 1
            else:
                return math.trunc(not_refunded_buys / BuyService.buys_per_page)

    @staticmethod
    async def get_new_buys_by_timedelta(timedelta_int):
        async with async_session_maker() as session:
            current_time = datetime.datetime.now()
            one_day_interval = datetime.timedelta(days=int(timedelta_int))
            time_to_subtract = current_time - one_day_interval
            stmt = select(Buy).where(Buy.buy_datetime >= time_to_subtract)
            buys = await session.execute(stmt)
            return buys.scalars().all()

