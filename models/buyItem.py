# from db import db
#
#
# class BuyItem:
#     def __init__(self, item_id: int, buy_id: int):
#         self.item_id = item_id
#         self.buy_id = buy_id
#
#     def insert_new(self):
#         db.cursor.execute("INSERT INTO `buyItem` (`item_id`, `buy_id`) VALUES (?,?)", (self.item_id, self.buy_id))
#         db.connect.commit()
#
#     @staticmethod
#     def insert_many(list_items: list, buy_id: int):
#         for item in list_items:
#             BuyItem(item['item_id'], buy_id).insert_new()
#
#     @staticmethod
#     def get_items_by_buy_id(buy_id: int):
#         items = db.cursor.execute("SELECT * FROM `buyItem` WHERE `buy_id`=?", (buy_id,)).fetchall()
#         return items
