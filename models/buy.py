from db import db


class Buy:
    def __init__(self, user_id, quantity, total_price):
        self.buy_id = self.__get_next_buy_id()
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
        db.cursor.execute("INSERT INTO `buys` (`user_id`, `quantity`, `total_price`) VALUES (?, ?, ?)",
                          (self.user_id, self.quantity, self.total_price))
        db.connect.commit()
