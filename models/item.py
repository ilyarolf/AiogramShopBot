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
        print(categories)
        return categories


if __name__ == '__main__':
    Item.get_categories()
