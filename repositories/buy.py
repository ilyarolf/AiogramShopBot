import datetime
import math

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import StatisticsTimeDelta
from db import session_execute, session_flush
from models.buy import Buy, BuyDTO, RefundDTO
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory
from models.user import User


class BuyRepository:
    @staticmethod
    async def get_by_buyer_id(user_id: int, page: int, session: AsyncSession) -> list[BuyDTO]:
        stmt = (select(Buy)
                .where(Buy.buyer_id == user_id)
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES))
        buys = await session_execute(stmt, session)
        return [BuyDTO.model_validate(buy, from_attributes=True) for buy in buys.scalars().all()]

    @staticmethod
    async def create(buy_dto: BuyDTO, session: Session | AsyncSession) -> int:
        buy = Buy(**buy_dto.model_dump())
        session.add(buy)
        await session_flush(session)
        return buy.id

    @staticmethod
    async def get_max_refund_page(session: Session | AsyncSession):
        stmt = select(func.count(Buy.id)).where(Buy.is_refunded == 0)
        not_refunded_buys = await session_execute(stmt, session)
        not_refunded_buys = not_refunded_buys.scalar_one()
        if not_refunded_buys % config.PAGE_ENTRIES == 0:
            return not_refunded_buys / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(not_refunded_buys / config.PAGE_ENTRIES)

    @staticmethod
    async def get_refund_data(page: int, session: Session | AsyncSession) -> list[RefundDTO]:
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
        refund_data = await session_execute(stmt, session)
        return [RefundDTO.model_validate(refund_item, from_attributes=True) for refund_item in
                refund_data.mappings().all()]

    @staticmethod
    async def get_refund_data_single(buy_id: int, session: Session | AsyncSession) -> RefundDTO:
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
        refund_data = await session_execute(stmt, session)
        return RefundDTO.model_validate(refund_data.mappings().one(), from_attributes=True)

    @staticmethod
    async def get_by_id(buy_id: int, session: Session | AsyncSession) -> BuyDTO:
        stmt = select(Buy).where(Buy.id == buy_id)
        buy = await session_execute(stmt, session)
        return BuyDTO.model_validate(buy.scalar_one(), from_attributes=True)

    @staticmethod
    async def update(buy_dto: BuyDTO, session: Session | AsyncSession):
        buy_dto_dict = buy_dto.model_dump()
        none_keys = [k for k, v in buy_dto_dict.items() if v is None]
        for k in none_keys:
            buy_dto_dict.pop(k)
        stmt = update(Buy).where(Buy.id == buy_dto.id).values(**buy_dto_dict)
        await session_execute(stmt, session)

    @staticmethod
    async def get_by_timedelta(timedelta: StatisticsTimeDelta, session: Session | AsyncSession) -> list[BuyDTO]:
        current_time = datetime.datetime.now()
        timedelta = datetime.timedelta(days=timedelta.value)
        time_interval = current_time - timedelta
        stmt = select(Buy).where(Buy.buy_datetime >= time_interval, Buy.is_refunded == False)
        buys = await session_execute(stmt, session)
        return [BuyDTO.model_validate(buy, from_attributes=True) for buy in buys.scalars().all()]

    @staticmethod
    async def get_max_page_purchase_history(buyer_id: int, session: Session | AsyncSession) -> int:
        stmt = select(func.count(Buy.id)).where(Buy.buyer_id == buyer_id)
        not_refunded_buys = await session_execute(stmt, session)
        not_refunded_buys = not_refunded_buys.scalar_one()
        if not_refunded_buys % config.PAGE_ENTRIES == 0:
            return not_refunded_buys / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(not_refunded_buys / config.PAGE_ENTRIES)
