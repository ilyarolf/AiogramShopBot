from typing import Union

from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData

from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

cart_router = Router()

class CartCallback(CallbackData, prefix="cart"):
    level: int
    action: str
    args_for_action: Union[int, str]
    page: int

@cart_router.message(F.text == Localizator.get_text_from_key("cart"), IsUserExistFilter())
async def cart_text_message(message: types.message):
    await show_cart(message)

#async def build_cart_items_overview(message: types.message):

        # item_from_history_callback = create_callback_profile(4, action="get_order",
        #                                                      args_for_action=str(buy_id))
        # order_inline = types.InlineKeyboardButton(
        #     text=Localizator.get_text_from_key("purchase_history_item").format(subcategory_name=item.subcategory.name,
        #                                                                        total_price=total_price,
        #                                                                        quantity=quantity),
        #     callback_data=item_from_history_callback
        # )
        # orders_markup_builder.add(order_inline)
    #orders_markup_builder.adjust(1)
    #return orders_markup_builder, len(orders)
    # show cart content
    # offer option to proceed to checkout
    # offer option to get back to all categories
    # offer option to delete items from cart (new InlineKeyboard to delete amount)
    #pass


# show content of cart as clickable items
async def show_cart(message: types.message):
    telegram_id = message.from_user.id
    open_cart_for_user = await CartService.get_open_cart_by_user(telegram_id)
    # show_cart_builder = InlineKeyboardBuilder()
    cart_items = open_cart_for_user.cart_items

    for cart_item in cart_items:
        quantity = cart_item.quantity
        a_piece_price = cart_item.a_piece_price
        total_price = a_piece_price * quantity
        subcategory_name = cart_item.subcategory_name

        cart_item_string = str(quantity) + " x " + str(subcategory_name) + " (" + str(a_piece_price) + ") = " + str(total_price)
        await message.answer(text=cart_item_string, parse_mode="HTML")


