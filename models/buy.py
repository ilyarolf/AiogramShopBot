from db import db
from models.user import User
from utils.other_sql import RefundBuyDTO


class Buy:
    def __init__(self, user_id, quantity, total_price, buy_id=None):
        if buy_id is None:
            self.buy_id = self.__get_next_buy_id()
        else:
            self.buy_id = buy_id
        self.user_id = user_id
        self.quantity = quantity
        self.total_price = total_price

    def __get_next_buy_id(self):
        last_id = db.cursor.execute("SELECT MAX(buy_id) FROM `buys`").fetchone()["MAX(buy_id)"]
        if last_id is not None:
            return last_id + 1
        else:
            return 0

    def insert_new(self):
        db.cursor.execute("INSERT INTO `buys` (`buy_id`, `user_id`, `quantity`, `total_price`) VALUES (?, ?, ?, ?)",
                          (self.buy_id, self.user_id, self.quantity, self.total_price))
        db.connect.commit()

    @staticmethod
    def get_not_refunded_buy_ids():
        not_refunded_buys = db.cursor.execute("SELECT `buy_id` FROM `buys` WHERE `is_refunded` = ?",
                                              (False,)).fetchall()
        return not_refunded_buys

    @staticmethod
    def get_buy_by_primary_key(buy_id: int):
        buy = db.cursor.execute("SELECT * FROM `buys` WHERE `buy_id` = ?", (buy_id,)).fetchone()
        buy.pop("buy_datetime")
        buy.pop("is_refunded")
        return Buy(**buy)

    @staticmethod
    def refund(buy_id: int, refund_data: RefundBuyDTO):
        User.reduce_consume_records(refund_data.user_id, refund_data.total_price)
        db.cursor.execute("UPDATE `buys` SET `is_refunded` = ? WHERE `buy_id` = ?", (True, buy_id))
        db.connect.commit()
