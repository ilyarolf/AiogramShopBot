from db import db
from dataclasses import dataclass


@dataclass
class RefundBuyDTO:
    telegram_username: str
    subcategory: str
    total_price: float
    buy_id: int


class OtherSQLQuery:
    @staticmethod
    def get_refund_data(buy_ids: list[int]):
        refund_data = list()
        for buy_id in buy_ids:
            buy_id = buy_id['buy_id']
            query_result = db.cursor.execute(
                """
                SELECT DISTINCT 
                    users.telegram_username, 
                    items.subcategory, 
                    buys.total_price,  
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
            query_result = RefundBuyDTO(**query_result)
            refund_data.append(query_result)
        return refund_data
