from db import db


class Item:
    def __init__(self, category: str, subcategory: str, private_data: str, price: float, is_sold: bool,
                 description: str, is_new: bool):
        self.category = category
        self.subcategory = subcategory
        self.private_data = private_data
        self.price = price
        self.is_sold = is_sold
        self.description = description
        self.is_new = is_new

    @staticmethod
    def get_categories() -> list:
        categories = db.cursor.execute('SELECT DISTINCT `category` FROM `items`').fetchall()
        return categories

    @staticmethod
    def get_subcategories(category: str) -> list:
        subcategories = db.cursor.execute('SELECT DISTINCT `subcategory`, `price` FROM `items` WHERE `category` = ?',
                                          (category,)).fetchall()
        return subcategories

    @staticmethod
    def get_description(subcategory: str) -> str:
        description = db.cursor.execute('SELECT `description` FROM `items` WHERE `subcategory` = ?',
                                        (subcategory,)).fetchone()['description']
        return description

    @staticmethod
    def get_available_quantity(subcategory: str) -> int:
        available_quantity = \
            db.cursor.execute('SELECT COUNT(*) as `count` FROM `items` WHERE `subcategory`= ? and `is_sold` = ?',
                              (subcategory, 0)).fetchone()['count']
        return available_quantity

    @staticmethod
    def get_bought_items(subcategory: str, quantity: int):
        bought_items = db.cursor.execute('SELECT * FROM `items` WHERE `subcategory` = ? AND `is_sold` = ? LIMIT ?',
                                         (subcategory, False, quantity)).fetchall()
        return bought_items

    @staticmethod
    def set_items_sold(items: list):
        for item in items:
            item_id = item['item_id']
            db.cursor.execute("UPDATE `items` SET `is_sold` = ? WHERE `item_id` = ?", (True, item_id))
        db.connect.commit()

    @staticmethod
    def get(item_id: int):
        item = db.cursor.execute("SELECT * FROM `items` WHERE `item_id` = ?", (item_id, )).fetchone()
        item.pop("item_id")
        return Item(**item)

    @staticmethod
    def get_new_items():
        items = db.cursor.execute("SELECT * FROM `items` WHERE `is_new` = ?", (True, )).fetchall()
        return items
