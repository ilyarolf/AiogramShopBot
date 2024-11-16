from typing import List

from models.item import Item
from services.category import CategoryService
from services.item import ItemService
from json import load
from pathlib import Path
from services.subcategory import SubcategoryService
from utils.localizator import Localizator, BotEntity


class NewItemsManager:
    @staticmethod
    async def __parse_items_from_file(path_to_file: str) -> list[Item]:
        # TODO("Refactoring")
        new_items = list()
        with open(path_to_file, "r", encoding="utf-8") as new_items_file:
            if path_to_file.endswith(".json"):
                items_dict = load(new_items_file)["items"]
                for item in items_dict:
                    category = await CategoryService.get_or_create_one(item['category'])
                    subcategory = await SubcategoryService.get_or_create_one(item['subcategory'])
                    item['category_id'] = category.id
                    item['subcategory_id'] = subcategory.id
                    item.pop('category')
                    item.pop('subcategory')
                    new_items.append(Item(**item))
            elif path_to_file.endswith(".txt"):
                lines = new_items_file.readlines()
                for line in lines:
                    category_name, subcategory_name, description, price, private_data = line.split(":")
                    category = await CategoryService.get_or_create_one(category_name)
                    subcategory = await SubcategoryService.get_or_create_one(subcategory_name)
                    new_items.append(Item(
                        category_id=category.id,
                        subcategory_id=subcategory.id,
                        price=float(price),
                        description=description,
                        private_data=private_data
                    ))
        return new_items

    @staticmethod
    async def add(path_to_file: str):
        # TODO(Need testing)
        try:
            new_items_as_objects = await NewItemsManager.__parse_items_from_file(path_to_file)
            await ItemService.add_many(new_items_as_objects)
            return len(new_items_as_objects)
        except Exception as e:
            return e
        finally:
            Path(path_to_file).unlink(missing_ok=True)

    @staticmethod
    async def generate_restocking_message():
        new_items = await ItemService.get_new_items()
        message = await NewItemsManager.create_text_of_items_msg(new_items, True)
        return message

    @staticmethod
    async def generate_in_stock_message():
        items = await ItemService.get_in_stock_items()
        message = await NewItemsManager.create_text_of_items_msg(items, False)
        return message

    @staticmethod
    async def create_text_of_items_msg(items: List[Item], is_update: bool) -> str:
        filtered_items = {}
        for item in items:
            category = await CategoryService.get_by_primary_key(item.category_id)
            if category.name not in filtered_items:
                filtered_items[category.name] = {}
            if item.subcategory not in filtered_items[category.name]:
                filtered_items[category.name][item.subcategory] = []
            filtered_items[category.name][item.subcategory].append(item)
        message = "<b>"
        if is_update is True:
            message += Localizator.get_text(BotEntity.ADMIN, "restocking_message_header")
        elif is_update is False:
            message += Localizator.get_text(BotEntity.ADMIN, "current_stock_header")
        for category, subcategory_item_dict in filtered_items.items():
            message += Localizator.get_text(BotEntity.ADMIN, "restocking_message_category").format(
                category=category)
            for subcategory, item in subcategory_item_dict.items():
                message += Localizator.get_text(BotEntity.USER, "subcategory_button").format(
                    subcategory_name=subcategory.name,
                    available_quantity=len(item),
                    subcategory_price=item[0].price,
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
        message += "</b>"
        return message
