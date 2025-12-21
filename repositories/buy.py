import math

from sqlalchemy import select, func, update, or_, literal_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import StatisticsTimeDelta
from db import session_execute, session_flush
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from models.buy import Buy, BuyDTO, RefundDTO
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory
from models.user import User
from utils.utils import calculate_max_page


class BuyRepository:
    @staticmethod
    async def get_by_buyer_id(sort_pairs: dict[str, int], user_id: int, page: int, session: AsyncSession) -> list[BuyDTO]:
        sort_methods = []
        for sort_property, sort_order in sort_pairs.items():
            sort_property, sort_order = SortProperty(int(sort_property)), SortOrder(sort_order)
            if sort_order != SortOrder.DISABLE:
                sort_column = sort_property.get_column(Buy)
                sort_method = (getattr(sort_column, sort_order.name.lower()))
                sort_methods.append(sort_method())
        conditions = [
            Buy.buyer_id == user_id
        ]
        stmt = (select(Buy)
                .where(*conditions)
                .limit(config.PAGE_ENTRIES)
                .offset(page * config.PAGE_ENTRIES)
                .order_by(*sort_methods))
        buys = await session_execute(stmt, session)
        return [BuyDTO.model_validate(buy, from_attributes=True) for buy in buys.scalars().all()]

    @staticmethod
    async def create(buy_dto: BuyDTO, session: Session | AsyncSession) -> BuyDTO:
        buy = Buy(**buy_dto.model_dump())
        session.add(buy)
        await session_flush(session)
        return BuyDTO.model_validate(buy, from_attributes=True)

    @staticmethod
    async def get_max_refund_page(filters: list[str], session: AsyncSession):
        conditions = [
            Buy.is_refunded == False
        ]
        if filters:
            filters = [username.replace("@", "") for username in filters]
            filter_conditions = [User.telegram_username.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        sub_stmt = (select(Buy)
                    .join(User, User.id == Buy.buyer_id)
                    .where(*conditions))
        stmt = select(func.count()).select_from(sub_stmt)
        not_refunded_buys = await session_execute(stmt, session)
        not_refunded_buys = not_refunded_buys.scalar_one()
        return calculate_max_page(not_refunded_buys)

    @staticmethod
    async def get_refund_data(sort_pairs: dict[str, int],
                              filters: list[str],
                              page: int, session: AsyncSession) -> list[RefundDTO]:
        sort_methods = []
        for sort_property, sort_order in sort_pairs.items():
            sort_property, sort_order = SortProperty(int(sort_property)), SortOrder(sort_order)
            if sort_order != SortOrder.DISABLE:
                sort_column = sort_property.get_column(Buy)
                sort_method = (getattr(sort_column, sort_order.name.lower()))
                sort_methods.append(sort_method())
        conditions = [Buy.is_refunded == False]
        if filters:
            filters = [username.replace("@", "") for username in filters]
            filter_conditions = [User.telegram_username.icontains(name) for name in filters]
            conditions.append(or_(*filter_conditions))
        # SQLITE CRUTCH 🩼
        je = func.json_each(BuyItem.item_ids).table_valued("value").alias("je")
        stmt = (select(Buy.total_price,
                       BuyItem.item_ids,
                       Buy.id.label("buy_id"),
                       User.telegram_id,
                       User.telegram_username,
                       User.id.label("user_id"),
                       Subcategory.name.label("subcategory_name"),
                       User.language)
                .join(BuyItem, BuyItem.buy_id == Buy.id)
                .join(User, User.id == Buy.buyer_id)
                # START SQLITE CRUTCH 🩼
                .join(je, literal_column("1") == literal_column("1"))
                .join(Item, Item.id == je.c.value)
                # END SQLITE CRUTCH 🩼
                # .join(Item, Item.id.in_(BuyItem.item_ids))
                .join(Subcategory, Subcategory.id == Item.subcategory_id)
                .where(*conditions)
                .distinct()
                .limit(config.PAGE_ENTRIES)
                .offset(config.PAGE_ENTRIES * page)
                .order_by(*sort_methods))
        refund_data = await session_execute(stmt, session)
        return [RefundDTO.model_validate(refund_item, from_attributes=True) for refund_item in
                refund_data.mappings().all()]

    @staticmethod
    async def get_refund_data_single(buy_id: int, session: Session | AsyncSession) -> RefundDTO:
        je = func.json_each(BuyItem.item_ids).table_valued("value").alias("je")
        stmt = (select(Buy.total_price,
                       BuyItem.item_ids,
                       Buy.id.label("buy_id"),
                       User.telegram_id,
                       User.telegram_username,
                       User.id.label("user_id"),
                       User.language,
                       Subcategory.name.label("subcategory_name"),
                       User.language)
                .join(BuyItem, BuyItem.buy_id == Buy.id)
                .join(User, User.id == Buy.buyer_id)
                # START SQLITE CRUTCH 🩼
                .join(je, literal_column("1") == literal_column("1"))
                .join(Item, Item.id == je.c.value)
                # END SQLITE CRUTCH 🩼
                # .join(Item, Item.id.in_(BuyItem.item_ids))
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
        start, end = timedelta.get_time_range()
        stmt = select(Buy).where(Buy.buy_datetime >= start,
                                 Buy.buy_datetime <= end,
                                 Buy.is_refunded == False)
        buys = await session_execute(stmt, session)
        return [BuyDTO.model_validate(buy, from_attributes=True) for buy in buys.scalars().all()]

    @staticmethod
    async def get_max_page_purchase_history(buyer_id: int, session: AsyncSession) -> int:
        conditions = [
            Buy.buyer_id == buyer_id
        ]
        stmt = select(func.count(Buy.id)).where(*conditions)
        buys = await session_execute(stmt, session)
        buys = buys.scalar_one()
        return calculate_max_page(buys)

    @staticmethod
    async def get_qty_by_buyer_id(buyer_id: int, session: AsyncSession | Session) -> int:
        stmt = (select(func.count(Buy.id))
                .where(Buy.buyer_id == buyer_id,
                       Buy.is_refunded == False))
        qty = await session_execute(stmt, session)
        return qty.scalar_one()

    @staticmethod
    async def get_spent_amount(buyer_id: int, session: AsyncSession) -> float:
        stmt = func.coalesce((select(func.sum(Buy.total_price))
                              .where(Buy.buyer_id == buyer_id,
                                     Buy.is_refunded == False)), 0)
        qty = await session_execute(stmt, session)
        return qty.scalar_one()
