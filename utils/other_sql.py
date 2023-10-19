from db import db
from dataclasses import dataclass
from typing import Union


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
    def get_refund_data(buy_ids: Union[list[dict], int]):
        if isinstance(buy_ids, list):
            return list(OtherSQLQuery.get_refund_data_single(buy_id["buy_id"]) for buy_id in buy_ids)
        else:
            return OtherSQLQuery.get_refund_data_single(buy_ids)

    @staticmethod
    def get_refund_data_single(buy_id: int):
        query_result = db.cursor.execute(
            """
            SELECT DISTINCT 
                users.telegram_username, 
                users.telegram_id, 
                users.user_id, 
                items.subcategory, 
                buys.total_price, 
                buys.quantity,  
                buys.buy_id
            FROM 
                buyItem b
            JOIN 
                buys ON b.buy_id = buys.buy_id
            JOIN 
                users ON buys.user_id = users.user_id
            JOIN 
                items ON b.item_id = items.item_id
            WHERE 
                b.buy_id=?
            """,
            (buy_id,)
        ).fetchone()
        return RefundBuyDTO(**query_result)
