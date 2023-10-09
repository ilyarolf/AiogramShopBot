from db import db
from typesDTO.itemDTO import ItemDTO
from json import load
from pathlib import Path


class NewItemsManager:
    @staticmethod
    def __parse_items_from_file(path_to_file: str) -> list[ItemDTO]:
        with open(path_to_file, "r", encoding="utf-8") as new_items_file:
            items_dict = load(new_items_file)["items"]
            new_items = [ItemDTO(**item) for item in items_dict]
            return new_items

    @staticmethod
    def __add_new_items_to_db(items: list[ItemDTO]):
        for item in items:
            db.cursor.execute("INSERT INTO `items` "
                              "(`category`, `subcategory`, `private_data`, `price`, `description`) "
                              "VALUES (?, ?, ?, ?, ?)",
                              (item.category, item.subcategory, item.private_data, item.price, item.description))
        db.connect.commit()

    @staticmethod
    def add(path_to_file: str):
        try:
            new_items_as_objects = NewItemsManager.__parse_items_from_file(path_to_file)
            NewItemsManager.__add_new_items_to_db(new_items_as_objects)
            Path(path_to_file).unlink(missing_ok=True)
            return len(new_items_as_objects)
        except Exception as e:
            return e
