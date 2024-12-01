from typing import List

from enums.bot_entity import BotEntity
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.subcategory import SubcategoryRepository
from services.item import ItemService
from utils.localizator import Localizator


class NewItemsManager:

    @staticmethod
    async def generate_restocking_message():
        new_items = await ItemService.get_new()
        message = await NewItemsManager.create_text_of_items_msg(new_items, True)
        return message

    @staticmethod
    async def generate_in_stock_message():
        items = await ItemService.get_in_stock_items()
        message = await NewItemsManager.create_text_of_items_msg(items, False)
        return message

    @staticmethod
    async def create_text_of_items_msg(items: List[ItemDTO], is_update: bool) -> str:
        filtered_items = {}
        for item in items:
            category = await CategoryRepository.get_by_id(item.category_id)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id)
            if category.name not in filtered_items:
                filtered_items[category.name] = {}
            if subcategory.name not in filtered_items[category.name]:
                filtered_items[category.name][subcategory.name] = []
            filtered_items[category.name][subcategory.name].append(item)
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
                    subcategory_name=subcategory,
                    available_quantity=len(item),
                    subcategory_price=item[0].price,
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
        message += "</b>"
        return message
