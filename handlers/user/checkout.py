from typing import Union

from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.cart import CartService

# add optional shipment service
# confirm (handover to existing buy process
checkout_process_router = Router()

# async def buy_processing(callback: CallbackQuery):
#     unpacked_callback = AllCategoriesCallback.unpack(callback.data)
#     confirmation = unpacked_callback.confirmation
#     total_price = unpacked_callback.total_price
#     subcategory_id = unpacked_callback.subcategory_id
#     quantity = unpacked_callback.quantity
#     telegram_id = callback.from_user.id
#     is_in_stock = await ItemService.get_available_quantity(subcategory_id) >= quantity
#     is_enough_money = await UserService.is_buy_possible(telegram_id, total_price)
#     back_to_main_builder = InlineKeyboardBuilder()
#     back_to_main_callback = create_callback_all_categories(level=0)
#     back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text_from_key("all_categories"),
#                                                     callback_data=back_to_main_callback)
#     back_to_main_builder.add(back_to_main_button)
#     bot = callback.bot
#     if confirmation and is_in_stock and is_enough_money:
#         await UserService.update_consume_records(telegram_id, total_price)
#         sold_items = await ItemService.get_bought_items(subcategory_id, quantity)
#         message = await create_message_with_bought_items(sold_items)
#         user = await UserService.get_by_tgid(telegram_id)
#         new_buy_id = await BuyService.insert_new(user, quantity, total_price)
#         await BuyItemService.insert_many(sold_items, new_buy_id)
#         await ItemService.set_items_sold(sold_items)
#         await callback.message.edit_text(text=message, parse_mode=ParseMode.HTML)
#         await NotificationManager.new_buy(subcategory_id, quantity, total_price, user, bot)
#     elif confirmation is False:
#         await callback.message.edit_text(text=Localizator.get_text_from_key("admin_declined"),
#                                          parse_mode=ParseMode.HTML,
#                                          reply_markup=back_to_main_builder.as_markup())
#     elif is_enough_money is False:
#         await callback.message.edit_text(text=Localizator.get_text_from_key("insufficient_funds"),
#                                          parse_mode=ParseMode.HTML,
#                                          reply_markup=back_to_main_builder.as_markup())
#     elif is_in_stock is False:
#         await callback.message.edit_text(text=Localizator.get_text_from_key("out_of_stock"),
#                                          parse_mode=ParseMode.HTML,
#                                          reply_markup=back_to_main_builder.as_markup())
#
#
# async def create_message_with_bought_items(bought_data: list):
#     message = "<b>"
#     for count, item in enumerate(bought_data, start=1):
#         private_data = item.private_data
#         message += Localizator.get_text_from_key("purchased_item").format(count=count, private_data=private_data)
#     message += "</b>"
#     return message
