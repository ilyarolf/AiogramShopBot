import datetime
import math

from sqlalchemy import select, func, update

import config
from callbacks import StatisticsTimeDelta
from db import get_db_session, session_execute, session_commit, session_refresh
from models.buy import Buy, BuyDTO, RefundDTO
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory
from models.user import User


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

    @staticmethod
    async def get_max_refund_page():
        stmt = select(func.count(Buy.id)).where(Buy.is_refunded == 0)
        async with get_db_session() as session:
            not_refunded_buys = await session_execute(stmt, session)
            not_refunded_buys = not_refunded_buys.scalar_one()
            if not_refunded_buys % config.PAGE_ENTRIES == 0:
                return not_refunded_buys / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(not_refunded_buys / config.PAGE_ENTRIES)

    @staticmethod
    async def get_refund_data(page: int) -> list[RefundDTO]:
        stmt = (select(Buy.total_price,
                       Buy.quantity,
                       Buy.id.label("buy_id"),
                       User.telegram_id,
                       User.telegram_username,
                       User.id.label("user_id"),
                       Subcategory.name.label("subcategory_name"))
                .join(BuyItem, BuyItem.buy_id == Buy.id)
                .join(User, User.id == Buy.buyer_id)
                .join(Item, Item.id == BuyItem.item_id)
                .join(Subcategory, Subcategory.id == Item.subcategory_id)
                .where(Buy.is_refunded == False)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(config.PAGE_ENTRIES * page))
        async with get_db_session() as session:
            refund_data = await session_execute(stmt, session)
            return [RefundDTO.model_validate(refund_item, from_attributes=True) for refund_item in
                    refund_data.mappings().all()]

    @staticmethod
    async def get_refund_data_single(buy_id: int) -> RefundDTO:
        stmt = (select(Buy.total_price,
                       Buy.quantity,
                       Buy.id.label("buy_id"),
                       User.telegram_id,
                       User.telegram_username,
                       User.id.label("user_id"),
                       Subcategory.name.label("subcategory_name"))
                .join(BuyItem, BuyItem.buy_id == Buy.id)
                .join(User, User.id == Buy.buyer_id)
                .join(Item, Item.id == BuyItem.item_id)
                .join(Subcategory, Subcategory.id == Item.subcategory_id)
                .where(Buy.is_refunded == False, Buy.id == buy_id)
                .limit(1))
        async with get_db_session() as session:
            refund_data = await session_execute(stmt, session)
            return RefundDTO.model_validate(refund_data.mappings().one(), from_attributes=True)

    @staticmethod
    async def get_by_id(buy_id: int) -> BuyDTO:
        stmt = select(Buy).where(Buy.id == buy_id)
        async with get_db_session() as session:
            buy = await session_execute(stmt, session)
            return BuyDTO.model_validate(buy.scalar_one(), from_attributes=True)

    @staticmethod
    async def update(buy_dto: BuyDTO):
        buy_dto_dict = buy_dto.__dict__
        none_keys = [k for k, v in buy_dto_dict.items() if v is None]
        for k in none_keys:
            buy_dto_dict.pop(k)
        stmt = update(Buy).where(Buy.id == buy_dto.id).values(**buy_dto_dict)
        async with get_db_session() as session:
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_by_timedelta(timedelta: StatisticsTimeDelta) -> list[BuyDTO]:
        current_time = datetime.datetime.now()
        timedelta = datetime.timedelta(days=timedelta.value)
        time_interval = current_time - timedelta
        stmt = select(Buy).where(Buy.buy_datetime >= time_interval, Buy.is_refunded == False)
        async with get_db_session() as session:
            buys = await session_execute(stmt, session)
            return [BuyDTO.model_validate(buy, from_attributes=True) for buy in buys.scalars().all()]

    @staticmethod
    async def get_max_page_purchase_history(buyerd_id: int) -> int:
        stmt = select(func.count(Buy.id)).where(Buy.buyer_id == buyerd_id)
        async with get_db_session() as session:
            not_refunded_buys = await session_execute(stmt, session)
            not_refunded_buys = not_refunded_buys.scalar_one()
            if not_refunded_buys % config.PAGE_ENTRIES == 0:
                return not_refunded_buys / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(not_refunded_buys / config.PAGE_ENTRIES)
