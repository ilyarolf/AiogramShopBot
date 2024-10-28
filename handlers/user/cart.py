from typing import Union

from aiogram import types, F, Router
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from handlers.common.common import add_pagination_buttons
from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

cart_router = Router()


class CartCallback(CallbackData, prefix="cart"):
    level: int
    page: int
    cart_id: int
    cart_item_id: int
    delete_cart_item_confirmation: bool


def create_cart_callback(level: int = 0
                         , page: int = 0
                         , cart_id: int = -1
                         , cart_item_id: int = -1
                         , telegram_id: int = -1
                         , delete_cart_item_confirmation = False):
    return (CartCallback(level=level
                         , page=page
                         , cart_id=cart_id
                         , cart_item_id=cart_item_id
                         , telegram_id=telegram_id
                         , delete_cart_item_confirmation=delete_cart_item_confirmation)
            .pack())


@cart_router.message(F.text == Localizator.get_text_from_key("cart"), IsUserExistFilter())
async def cart_text_message(message: types.message):
    await show_cart(message)

# show content of cart as clickable items
async def create_cart_item_buttons(telegram_id: int, page: int):
    cart = await CartService.get_open_cart_by_user(telegram_id)
    cart_items = cart.cart_items
    if cart_items:
        cart_builder = InlineKeyboardBuilder()

        for cart_item in cart_items:
            cart_button_callback = create_cart_callback(level=1, page=page, cart_item_id=cart_item.id)

            cart_button_text = Localizator.get_text_from_key("cart_item_button").format(
                cart_item_subcategory_name=cart_item.subcategory_name,
                cart_item_quantity=str(cart_item.quantity),
                cart_item_total=str(cart_item.quantity*cart_item.a_piece_price),
                cart_item_currency=str(config.CURRENCY),
            )
            #cart_button_text = (cart_item.subcategory_name
            #                    + ' ('
            #                    + str(cart_item.quantity)
            #                    + ') = '
            #                    + str(cart_item.quantity * cart_item.a_piece_price)
            #                    + str(config.CURRENCY)
            #                    + str(" \uD83D\uDDD1"))
            cart_button = types.InlineKeyboardButton(text=cart_button_text, callback_data=cart_button_callback)
            cart_builder.add(cart_button)
        cart_builder.add()
        cart_button_checkout_callback = create_cart_callback(level=2, page=page, cart_id=cart.id)
        cart_button_checkout = types.InlineKeyboardButton(text=Localizator.get_text_from_key("checkout"),
                                                          callback_data=cart_button_checkout_callback
                                                    )

        cart_builder.add(cart_button_checkout)
        # one item per line
        cart_builder.adjust(1)
        return cart_builder


async def show_cart(message: Union[Message, CallbackQuery]):
    telegram_id = message.from_user.id
    open_cart_for_user = await CartService.get_open_cart_by_user(telegram_id)

    if open_cart_for_user is None:
        await CartService.get_or_create_cart(telegram_id)
        await message.answer(Localizator.get_text_from_key("no_cart_items"), parse_mode=ParseMode.HTML)
    elif isinstance(message, Message):
        cart_inline_buttons = await create_cart_item_buttons(message.from_user.id, 0)
        zero_level_callback = create_cart_callback(level=0)
        if cart_inline_buttons:
            cart_inline_buttons = await add_pagination_buttons(cart_inline_buttons,
                                                               zero_level_callback,
                                                               CartService.get_maximum_page(telegram_id),
                                                               CartCallback.unpack,
                                                               None)
            await message.answer(Localizator.get_text_from_key("cart"), parse_mode=ParseMode.HTML,
                                 reply_markup=cart_inline_buttons.as_markup())
            await message.answer(Localizator.get_text_from_key("cart_tap_to_delete_cart_item"), parse_mode=ParseMode.HTML)
        else:
            await message.answer(Localizator.get_text_from_key("no_cart_items"), parse_mode=ParseMode.HTML)
    elif isinstance(message, CallbackQuery):
        callback = message
        unpacked_callback = CartCallback.unpack(callback.data)
        cart_inline_buttons = await create_cart_item_buttons(message.from_user.id, unpacked_callback.page)


        if cart_inline_buttons:
            cart_inline_buttons = await add_pagination_buttons(cart_inline_buttons, callback.data,
                                                                   CartService.get_maximum_page(telegram_id),
                                                                   CartCallback.unpack, None)
            await callback.message.edit_text(Localizator.get_text_from_key("cart"), parse_mode=ParseMode.HTML,
                                             reply_markup=cart_inline_buttons.as_markup())
        else:
            await callback.message.edit_text(Localizator.get_text_from_key("no_cart_items"), parse_mode=ParseMode.HTML)


async def delete_cart_item(callback: CallbackQuery):
    unpacked_callback_query = CartCallback.unpack(callback.data)
    cart_item_id = unpacked_callback_query.cart_item_id
    cart_item = await CartService.get_cart_item_by_id(cart_item_id)
    delete_cart_item_confirmation = unpacked_callback_query.delete_cart_item_confirmation

    if delete_cart_item_confirmation:
        await CartService.remove_from_cart(cart_item_id, cart_item_id)
        await callback.message.edit_text(Localizator.get_text_from_key("delete_cart_item_confirmation_text")
                                      , parse_mode=ParseMode.HTML)

    else:
        delete_cart_item_builder = InlineKeyboardBuilder()
        confirmation_button_delete_cert_item_callback = create_cart_callback(level=1
                                                                             , page=0
                                                                             , cart_item_id=cart_item.id
                                                                             , delete_cart_item_confirmation=True)
        confirmation_button_delete_cart_item = types.InlineKeyboardButton(text=Localizator.get_text_from_key("admin_confirm"),
                                                                          callback_data=confirmation_button_delete_cert_item_callback)
        decline_button_delete_cart_item_callback = create_cart_callback(level=0
                                                                        , page=0)
        decline_button_delete_cart_item = types.InlineKeyboardButton(text=Localizator.get_text_from_key("admin_decline"),
                                                                     callback_data=decline_button_delete_cart_item_callback)
        delete_cart_item_builder.add(confirmation_button_delete_cart_item)
        delete_cart_item_builder.add(decline_button_delete_cart_item)
        delete_cart_item_builder.adjust(2)
        await callback.message.edit_text(text=Localizator.get_text_from_key("delete_cart_item_confirmation")
                                         , parse_mode=ParseMode.HTML
                                         , reply_markup=delete_cart_item_builder.as_markup()
                                         )


async def checkout_processing(callback_data: CallbackQuery):
    callback_data_unpacked = CartCallback.unpack(callback_data.data)
    telegram_id = callback_data_unpacked.telegram_id
    cart = await CartService.get_open_cart_by_user(telegram_id)
    print(cart)



@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: delete_cart_item,
        2: checkout_processing,
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)



