from typing import Union

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.cart import CartService

# add optional shipment service
# confirm (handover to existing buy process

async def create_cart_content(category_id: int, page: int = 0):
    current_level = 1
    cart_item = await CartService.g(category_id, page)
    subcategories_builder = InlineKeyboardBuilder()
    # for item in items:
    #     subcategory_price = await ItemService.get_price_by_subcategory(item.subcategory_id)
    #     available_quantity = await ItemService.get_available_quantity(item.subcategory_id)
    #     subcategory_inline_button = create_callback_all_categories(level=current_level + 1,
    #                                                                category_id=category_id,
    #                                                                subcategory_id=item.subcategory_id,
    #                                                                price=subcategory_price)
    #     subcategories_builder.add(
    #         types.InlineKeyboardButton(
    #             text=Localizator.get_text_from_key("subcategory_button").format(subcategory_name=item.subcategory.name,
    #                                                                             subcategory_price=subcategory_price,
    #                                                                             available_quantity=available_quantity),
    #             callback_data=subcategory_inline_button))
    # subcategories_builder.adjust(1)
    # return subcategories_builder


async def all_shipments(message: Union[Message, CallbackQuery]):
    pass

checkout_router = Router()