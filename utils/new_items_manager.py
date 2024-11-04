from models.item import Item
from services.category import CategoryService
from services.item import ItemService
from json import load
from pathlib import Path
from datetime import date
from db import get_db_session, close_db_session
from services.subcategory import SubcategoryService
from utils.localizator import Localizator


class NewItemsManager:
    @staticmethod
    async def __parse_items_from_file(path_to_file: str) -> list[Item]:
        with open(path_to_file, "r", encoding="utf-8") as new_items_file:
            items_dict = load(new_items_file)["items"]
            new_items = list()
            session = await get_db_session()
            for item in items_dict:
                category_obj = await CategoryService.get_or_create_one(item['category'], session)
                subcategory_obj = await SubcategoryService.get_or_create_one(item['subcategory'], session)
                item['category_id'] = category_obj.id
                item['subcategory_id'] = subcategory_obj.id
                item.pop('category')
                item.pop('subcategory')
                new_items.append(Item(**item))
            await close_db_session(session)
            return new_items

    @staticmethod
    async def add(path_to_file: str):
        # TODO(Need testing)
        try:
            new_items_as_objects = await NewItemsManager.__parse_items_from_file(path_to_file)
            session = await get_db_session()
            await ItemService.add_many(new_items_as_objects, session)
            await close_db_session(session)
            Path(path_to_file).unlink(missing_ok=True)
            return len(new_items_as_objects)
        except Exception as e:
            return e

    @staticmethod
    async def generate_restocking_message():
        session = await get_db_session()
        new_items = await ItemService.get_new_items(session)
        filtered_items = {}
        for item in new_items:
            category = await CategoryService.get_by_primary_key(item.category_id, session)
            await close_db_session(session)
            if category.name not in filtered_items:
                filtered_items[category.name] = {}
            if item.subcategory not in filtered_items[category.name]:
                filtered_items[category.name][item.subcategory] = []
            filtered_items[category.name][item.subcategory].append(item)
        update_data = date.today()
        message = Localizator.get_text_from_key("new_items_message_update").format(update_data=update_data)
        for category, subcategory_item_dict in filtered_items.items():
            message += Localizator.get_text_from_key("new_items_message_category").format(category=category)
            for subcategory, item in subcategory_item_dict.items():
                message += Localizator.get_text_from_key("new_items_message_subcategory").format(
                    subcategory_name=subcategory.name,
                    items_len=len(item))
        message += "</b>"
        return message
