from dataclasses import dataclass
from typing import Union

from sqlalchemy import select

from db import async_session_maker
from models.buy import Buy
from models.buyItem import BuyItem
from models.item import Item
from models.subcategory import Subcategory
from models.user import User


@dataclass
class RefundBuyDTO:
    user_id: int
    telegram_username: str
    telegram_id: id
    subcategory: str
    total_price: float
    quantity: int
    buy_id: int


class OtherSQLQuery:
    @staticmethod
    async def get_refund_data(buy_ids: Union[list[dict], int]):
        if isinstance(buy_ids, list):
            result_list = list()
            for buy_id in buy_ids:
                result_list.append(await OtherSQLQuery.get_refund_data_single(buy_id))
            return result_list
        else:
            return await OtherSQLQuery.get_refund_data_single(buy_ids)

    @staticmethod
    async def get_refund_data_single(buy_id: int):
        async with async_session_maker() as session:
            stmt = select(
                User.telegram_username,
                User.telegram_id,
                User.id.label("user_id"),
                Subcategory.name.label("subcategory"),
                Buy.total_price,
                Buy.quantity,
                Buy.id.label("buy_id")
            ).join(
                BuyItem, BuyItem.buy_id == Buy.id
            ).join(
                User, User.id == Buy.buyer_id
            ).join(
                Item, Item.id == BuyItem.item_id
            ).join(
                Subcategory, Subcategory.id == Item.subcategory_id
            ).where(
                BuyItem.buy_id == buy_id
            ).limit(1)
            buy_items = await session.execute(stmt)
            buy_items = buy_items.mappings().one()
            return RefundBuyDTO(**buy_items)
