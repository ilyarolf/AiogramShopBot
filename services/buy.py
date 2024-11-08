import datetime
import math
from sqlalchemy import select, update, func
import config
from db import session_execute, session_commit, session_refresh, get_db_session
from models.buy import Buy
from models.user import User
from services.user import UserService
from utils.other_sql import RefundBuyDTO


class BuyService:

    @staticmethod
    async def get_buys_by_buyer_id(buyer_id: int, page: int):
        async with get_db_session() as session:
            stmt = select(Buy).where(Buy.buyer_id == buyer_id).limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES)
            buys = await session_execute(stmt, session)
            return buys.scalars().all()

    @staticmethod
    async def get_max_page_purchase_history(buyer_id: int):
        async with get_db_session() as session:
            stmt = select(func.count(Buy.id)).where(Buy.buyer_id == buyer_id)
            max_page = await session_execute(stmt, session)
            max_page = max_page.scalar_one()
            if max_page % config.PAGE_ENTRIES == 0:
                return max_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def insert_new(user: User, quantity: int, total_price: float) -> int:
        async with get_db_session() as session:
            new_buy = Buy(buyer_id=user.id, quantity=quantity, total_price=total_price)
            session.add(new_buy)
            await session_commit(session)
            await session_refresh(session, new_buy)
            return new_buy.id

    @staticmethod
    async def get_not_refunded_buy_ids(page: int):
        async with get_db_session() as session:
            stmt = select(Buy.id).where(Buy.is_refunded == 0).limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES)
            not_refunded_buys = await session_execute(stmt, session)
            return not_refunded_buys.scalars().all()

    @staticmethod
    async def refund(buy_id: int, refund_data: RefundBuyDTO):
        await UserService.reduce_consume_records(refund_data.user_id, refund_data.total_price)
        async with get_db_session() as session:
            stmt = update(Buy).where(Buy.id == buy_id).values(is_refunded=True)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_max_refund_pages():
        async with get_db_session() as session:
            stmt = select(func.count(Buy.id)).where(Buy.is_refunded == 0)
            not_refunded_buys = await session_execute(stmt, session)
            not_refunded_buys = not_refunded_buys.scalar_one()
            if not_refunded_buys % config.PAGE_ENTRIES == 0:
                return not_refunded_buys / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(not_refunded_buys / config.PAGE_ENTRIES)

    @staticmethod
    async def get_new_buys_by_timedelta(timedelta_int):
        async with get_db_session() as session:
            current_time = datetime.datetime.now()
            one_day_interval = datetime.timedelta(days=int(timedelta_int))
            time_to_subtract = current_time - one_day_interval
            stmt = select(Buy).where(Buy.buy_datetime >= time_to_subtract)
            buys = await session_execute(stmt, session)
            return buys.scalars().all()
