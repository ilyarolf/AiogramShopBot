from typing import Union, List

from aiogram import types, F, Router
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from handlers.common.common import add_pagination_buttons
from handlers.user.all_categories import create_callback_all_categories
from models.cart import CartItem
from services.buy import BuyService
from services.buyItem import BuyItemService
from services.cart import CartService
from services.item import ItemService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator
from utils.notification_manager import NotificationManager

cart_router = Router()


class CartCallback(CallbackData, prefix="cart"):
    level: int
    page: int
    cart_id: int
    cart_item_id: int
    delete_cart_item_confirmation: bool
    purchase_confirmation: bool
    cart_grand_total: float


def create_cart_callback(level: int = 0
                         , page: int = 0
                         , cart_id: int = -1
                         , cart_item_id: int = -1
                         , telegram_id: int = -1
                         , delete_cart_item_confirmation = False
                         , purchase_confirmation = False
                         , cart_grand_total = 0.0):
    return (CartCallback(level=level
                         , page=page
                         , cart_id=cart_id
                         , cart_item_id=cart_item_id
                         , telegram_id=telegram_id
                         , delete_cart_item_confirmation=delete_cart_item_confirmation
                         , purchase_confirmation=purchase_confirmation
                         , cart_grand_total=cart_grand_total)
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
                cart_item_quantity=cart_item.quantity,
                cart_item_total=cart_item.quantity*cart_item.a_piece_price,
                cart_item_currency=config.CURRENCY,
            )

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
        decline_button_delete_cart_item_callback = create_cart_callback(level=0)
        decline_button_delete_cart_item = types.InlineKeyboardButton(text=Localizator.get_text_from_key("admin_decline"),
                                                                     callback_data=decline_button_delete_cart_item_callback)
        delete_cart_item_builder.add(confirmation_button_delete_cart_item)
        delete_cart_item_builder.add(decline_button_delete_cart_item)
        delete_cart_item_builder.adjust(2)
        await callback.message.edit_text(text=Localizator.get_text_from_key("delete_cart_item_confirmation")
                                         , parse_mode=ParseMode.HTML
                                         , reply_markup=delete_cart_item_builder.as_markup())


def create_cart_content_string(cart_items: List[CartItem]) -> str:

    cart_line_items_total = ""
    cart_grand_total = 0
    max_line_width = 0

    for cart_item in cart_items:
        line_item_total = cart_item.a_piece_price * cart_item.quantity
        cart_line_item = Localizator.get_text_from_key("cart_line_item").format(
            cart_item_subcategory_name=cart_item.subcategory_name
            , cart_item_quantity=cart_item.quantity
            , cart_item_total=line_item_total
            , cart_item_currency=config.CURRENCY
        )
        cart_grand_total += line_item_total
        max_line_width = max(max_line_width, len(cart_line_item))
        cart_line_items_total += cart_line_item
    dash = "-"
    cart_line_items_total += dash * min(config.MAX_LINE_WITH, max_line_width) + "\n"
    cart_line_items_total += Localizator.get_text_from_key("cart_grand_total_string").format(
        cart_grand_total=cart_grand_total
        , cart_item_currency=config.CURRENCY
    )
    return cart_line_items_total


def get_checkout_buttons_inline_builder(callback):
    unpacked_cart_callback = CartCallback.unpack(callback.data)
    cart_checkout_inline_keyboard_builder = InlineKeyboardBuilder()
    confirmation_checkout_callback = create_cart_callback(level=3)
    confirmation_button_checkout = types.InlineKeyboardButton(
        text=Localizator.get_text_from_key("admin_confirm"),
        callback_data=confirmation_checkout_callback)
    decline_checkout_callback = create_cart_callback(level=unpacked_cart_callback.level - 2)
    decline_button_checkout = types.InlineKeyboardButton(text=Localizator.get_text_from_key("admin_decline"),
                                                                 callback_data=decline_checkout_callback)
    cart_checkout_inline_keyboard_builder.add(confirmation_button_checkout)
    cart_checkout_inline_keyboard_builder.add(decline_button_checkout)
    cart_checkout_inline_keyboard_builder.adjust(2)

    return cart_checkout_inline_keyboard_builder


async def checkout_processing(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    cart = await CartService.get_open_cart_by_user(telegram_id)

    if not cart.cart_items:
        await callback.message.edit_text(Localizator.get_text_from_key("no_cart_items"))
    else:

        cart_content_string = create_cart_content_string(cart.cart_items)
        await callback.message.edit_text(cart_content_string)
        checkout_buttons_inline_builder = get_checkout_buttons_inline_builder(callback)
        await callback.message.answer(text=Localizator.get_text_from_key("cart_confirm_checkout_process")
                                         , parse_mode=ParseMode.HTML
                                         , reply_markup=checkout_buttons_inline_builder.as_markup()
                                         )


async def buy_processing(callback: CallbackQuery):
    unpacked_callback = CartCallback.unpack(callback.data)
    purchase_confirmation = unpacked_callback.purchase_confirmation
    cart_grand_total = unpacked_callback.cart_grand_total
    telegram_id = callback.from_user.id

    cart = await CartService.get_open_cart_by_user(telegram_id)
    cart_items = cart.cart_items

    is_in_stock = False
    out_of_stock_items = []

    for cart_item in cart_items:

        subcategory_id = cart_item.subcategory_id
        quantity = cart_item.quantity

        item_is_in_stock = await ItemService.get_available_quantity(subcategory_id) >= quantity
        if item_is_in_stock:
            is_in_stock: True
        else:
            is_in_stock: False
            out_of_stock_items.append(cart_item)
    is_enough_money = await UserService.is_buy_possible(telegram_id, cart_grand_total)

    back_to_main_builder = InlineKeyboardBuilder()
    back_to_main_callback = create_callback_all_categories(level=0)
    back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text_from_key("all_categories"),
                                                    callback_data=back_to_main_callback)
    back_to_main_builder.add(back_to_main_button)

    bot = callback.bot
    if purchase_confirmation and is_in_stock and is_enough_money:

        await UserService.update_consume_records(telegram_id, cart_grand_total)

        for cart_item in cart_items:

            sold_items = await ItemService.get_bought_items(cart_item.subcategory_id, cart_item.quantity)
            message = await create_message_with_bought_items(sold_items)
            user = await UserService.get_by_tgid(telegram_id)
            cart_item_total = cart_item.quantity * cart_item.a_piece_price
            new_buy_id = await BuyService.insert_new(user, cart_item.quantity, cart_item_total)
            await BuyItemService.insert_many(sold_items, new_buy_id)
            await ItemService.set_items_sold(sold_items)
            await callback.message.edit_text(text=message, parse_mode=ParseMode.HTML)
            await NotificationManager.new_buy(cart_item.subcategory_id, cart_item.quantity, cart_item_total, user, bot)

    elif purchase_confirmation is False:
        await callback.message.edit_text(text=Localizator.get_text_from_key("admin_declined"),
                                         parse_mode=ParseMode.HTML,
                                         reply_markup=back_to_main_builder.as_markup())
    elif is_enough_money is False:
        await callback.message.edit_text(text=Localizator.get_text_from_key("insufficient_funds"),
                                         parse_mode=ParseMode.HTML,
                                         reply_markup=back_to_main_builder.as_markup())
    elif is_in_stock is False:
        await callback.message.edit_text(text=Localizator.get_text_from_key("out_of_stock"),
                                         parse_mode=ParseMode.HTML,
                                         reply_markup=back_to_main_builder.as_markup())


async def create_message_with_bought_items(bought_data: list):
    message = "<b>"
    for count, item in enumerate(bought_data, start=1):
        private_data = item.private_data
        message += Localizator.get_text_from_key("purchased_item").format(count=count, private_data=private_data)
    message += "</b>"
    return message


async def checkout_finalization(callback_data: CallbackQuery):
    pass


@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: delete_cart_item,
        2: checkout_processing,
        3: buy_processing,
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)



