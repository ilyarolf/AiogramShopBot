from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from enums.bot_entity import BotEntity
from models.item import ItemDTO
from repositories.category import CategoryRepository
from services.item import ItemService
from utils.localizator import Localizator


class NewItemsManager:

    @staticmethod
    async def generate_restocking_message(session: AsyncSession | Session):
        new_items = await ItemService.get_new(session)
        message = await NewItemsManager.create_text_of_items_msg(new_items, True, session)
        return message

    @staticmethod
    async def generate_in_stock_message(session: AsyncSession | Session):
        items = await ItemService.get_in_stock_items(session)
        message = await NewItemsManager.create_text_of_items_msg(items, False, session)
        return message

    @staticmethod
    async def create_text_of_items_msg(items: List[ItemDTO], is_update: bool, session: AsyncSession | Session) -> str:
        """
        Create announcement message for items.

        In tree-based system, items belong to product categories. We build the
        breadcrumb path for display, grouping by root category and showing
        product name with quantity/price.
        """
        # Group items by category path: {root_name: {product_name: (items, price)}}
        filtered_items = {}
        category_cache = {}

        for item in items:
            # Get product category (with caching)
            if item.category_id not in category_cache:
                category = await CategoryRepository.get_by_id(item.category_id, session)
                breadcrumb = await CategoryRepository.get_breadcrumb(item.category_id, session)
                category_cache[item.category_id] = (category, breadcrumb)

            category, breadcrumb = category_cache[item.category_id]

            # Use root category name (or product name if it's a root product)
            root_name = breadcrumb[0].name if breadcrumb else category.name
            product_name = category.name

            if root_name not in filtered_items:
                filtered_items[root_name] = {}
            if product_name not in filtered_items[root_name]:
                filtered_items[root_name][product_name] = {"items": [], "price": category.price}
            filtered_items[root_name][product_name]["items"].append(item)

        message = "<b>"
        if is_update is True:
            message += Localizator.get_text(BotEntity.ADMIN, "restocking_message_header")
        elif is_update is False:
            message += Localizator.get_text(BotEntity.ADMIN, "current_stock_header")

        for category_name, product_dict in filtered_items.items():
            message += Localizator.get_text(BotEntity.ADMIN, "restocking_message_category").format(
                category=category_name)
            for product_name, product_data in product_dict.items():
                message += Localizator.get_text(BotEntity.USER, "subcategory_button").format(
                    subcategory_name=product_name,
                    available_quantity=len(product_data["items"]),
                    subcategory_price=product_data["price"],
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
        message += "</b>"
        return message
