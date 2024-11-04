import json

from dataclasses import asdict

from models.item import ItemDTO


class NewItemsGenerator:

    @staticmethod
    def create_items_file(items: list[ItemDTO]):
        with open("output_items.txt", "w", encoding="utf-8") as f:
            dict_list = [asdict(item) for item in items]
            json.dump(dict_list, f)

    @staticmethod
    def generate_items_as_dto(filepath: str, category: str, subcategory: str, price: float,
                              description: str) -> list[ItemDTO]:
        items_list = list()
        with open(filepath, "r") as f:
            for line in f.readlines():
                items_list.append(ItemDTO(category, subcategory, line.strip(), price, description))
            return items_list

    @staticmethod
    def generate_blank_items_as_dto(count: int, category: str, subcategory: str, price: float,
                                    description: str):
        items_list = list()
        for i in range(count):
            items_list.append(ItemDTO(category, subcategory, "Contact Admin", price, description))
        return items_list


if __name__ == "__main__":
    pass
