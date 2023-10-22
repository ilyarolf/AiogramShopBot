from typing import Union

from aiogram import types, Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from models.buy import Buy
from models.buyItem import BuyItem
from models.item import Item
from models.user import User
from utils.notification_manager import NotificationManager


class AllCategoriesCallback(CallbackData, prefix="all_categories"):
    level: int
    category: str
    subcategory: str
    price: float
    quantity: int
    total_price: float
    confirmation: bool


def create_callback_all_categories(level: int,
                                   category: str = "",
                                   subcategory: str = "",
                                   price: float = 0.0,
                                   total_price: float = 0.0,
                                   quantity: int = 0,
                                   confirmation: bool = False):
    return AllCategoriesCallback(level=level, category=category, subcategory=subcategory, price=price,
                                 total_price=total_price,
                                 quantity=quantity, confirmation=confirmation).pack()


all_categories_router = Router()


@all_categories_router.message(F.text == "🔍 All categories")
async def all_categories_text_message(message: types.message):
    await all_categories(message)


async def create_category_buttons(current_level: int):
    categories = Item.get_categories()
    if categories:
        categories_builder = InlineKeyboardBuilder()
        categories_builder.adjust(2)
        for category in categories:
            category_name = category['category']
            category_button_callback = create_callback_all_categories(level=current_level + 1, category=category_name)
            category_button = types.InlineKeyboardButton(text=category_name, callback_data=category_button_callback)
            categories_builder.add(category_button)
        return categories_builder.as_markup()


async def create_subcategory_buttons(category: str):
    current_level = 1
    subcategories = Item.get_subcategories(category)
    subcategories_builder = InlineKeyboardBuilder()
    subcategories_builder.adjust(1)
    for subcategory in subcategories:
        subcategory_name = subcategory['subcategory']
        subcategory_price = subcategory['price']
        available_quantity = Item.get_available_quantity(subcategory_name)
        subcategory_inline_button = create_callback_all_categories(level=current_level + 1,
                                                                   category=category,
                                                                   subcategory=subcategory_name,
                                                                   price=subcategory_price)
        subcategories_builder.add(
            types.InlineKeyboardButton(
                text=f"{subcategory_name}| Price: ${subcategory_price} | Quantity: {available_quantity} pcs",
                callback_data=subcategory_inline_button))
    back_button = types.InlineKeyboardButton(text="Back",
                                             callback_data=create_callback_all_categories(level=current_level - 1))
    subcategories_builder.add(back_button)
    return subcategories_builder.as_markup()


async def all_categories(message: Union[Message, CallbackQuery]):
    current_level = 0
    category_inline_buttons = await create_category_buttons(current_level)
    if isinstance(message, Message):
        if category_inline_buttons:
            await message.answer('🔍 <b>All categories</b>', parse_mode='html', reply_markup=category_inline_buttons)
        else:
            await message.answer('<b>No categories</b>', parse_mode='html')
    elif isinstance(message, CallbackQuery):
        callback = message
        if category_inline_buttons:
            await callback.message.edit_text('🔍 <b>All categories</b>', parse_mode='html',
                                             reply_markup=category_inline_buttons)
        else:
            await callback.message.edit_text('<b>No categories</b>', parse_mode='html')


async def show_subcategories_in_category(callback: CallbackQuery):
    category = AllCategoriesCallback.unpack(callback.data).category
    subcategory_buttons = await create_subcategory_buttons(category)
    await callback.message.edit_text("<b>Subcategories:</b>", reply_markup=subcategory_buttons, parse_mode="html")


async def select_quantity(callback: CallbackQuery):
    unpacked_callback = AllCategoriesCallback.unpack(callback.data)
    price = unpacked_callback.price
    subcategory = unpacked_callback.subcategory
    category = unpacked_callback.category
    current_level = unpacked_callback.level
    description = Item.get_description(subcategory)
    count_builder = InlineKeyboardBuilder()
    count_builder.adjust(3)
    for i in range(1, 11):
        count_button_callback = create_callback_all_categories(level=current_level + 1, category=category,
                                                               subcategory=subcategory, price=price,
                                                               quantity=i, total_price=price * i)
        count_button_inline = types.InlineKeyboardButton(text=str(i), callback_data=count_button_callback)
        count_builder.add(count_button_inline)
    back_button = types.InlineKeyboardButton(text="Back",
                                             callback_data=create_callback_all_categories(level=current_level - 1,
                                                                                          category=category))
    count_builder.add(back_button)
    await callback.message.edit_text(f'<b>You choose:{subcategory}\n'
                                     f'Price:${price}\n'
                                     f'Description:{description}\n'
                                     f'Quantity:</b>', reply_markup=count_builder.as_markup(), parse_mode='html')


async def buy_confirmation(callback: CallbackQuery):
    unpacked_callback = AllCategoriesCallback.unpack(callback.data)
    price = unpacked_callback.price
    total_price = unpacked_callback.total_price
    subcategory = unpacked_callback.subcategory
    category = unpacked_callback.category
    current_level = unpacked_callback.level
    quantity = unpacked_callback.quantity
    description = Item.get_description(subcategory)
    confirmation_builder = InlineKeyboardBuilder()
    confirm_button_callback = create_callback_all_categories(level=current_level + 1,
                                                             category=category,
                                                             subcategory=subcategory,
                                                             price=price,
                                                             total_price=total_price,
                                                             quantity=quantity,
                                                             confirmation=True)
    decline_button_callback = create_callback_all_categories(level=current_level + 1,
                                                             category=category,
                                                             subcategory=subcategory,
                                                             price=price,
                                                             total_price=total_price,
                                                             quantity=quantity,
                                                             confirmation=False)
    confirmation_button = types.InlineKeyboardButton(text="Confirm", callback_data=confirm_button_callback)
    decline_button = types.InlineKeyboardButton(text="Decline", callback_data=decline_button_callback)
    back_button = types.InlineKeyboardButton(text="Back",
                                             callback_data=create_callback_all_categories(level=current_level - 1,
                                                                                          category=category,
                                                                                          subcategory=subcategory,
                                                                                          price=price))
    confirmation_builder.add(confirmation_button, decline_button, back_button)
    await callback.message.edit_text(text=f'<b>You choose:{subcategory}\n'
                                          f'Price:${price}\n'
                                          f'Description:{description}\n'
                                          f'Quantity:{quantity}\n'
                                          f'Total price:${total_price}</b>',
                                     reply_markup=confirmation_builder.as_markup(),
                                     parse_mode='html')


async def buy_processing(callback: CallbackQuery):
    unpacked_callback = AllCategoriesCallback.unpack(callback.data)
    confirmation = unpacked_callback.confirmation
    total_price = unpacked_callback.total_price
    subcategory = unpacked_callback.subcategory
    quantity = unpacked_callback.quantity
    telegram_id = callback.from_user.id
    is_in_stock = Item.get_available_quantity(subcategory) >= quantity
    is_enough_money = User.is_buy_possible(telegram_id, total_price)
    back_to_main_builder = InlineKeyboardBuilder()
    back_to_main_callback = create_callback_all_categories(level=0)
    back_to_main_button = types.InlineKeyboardButton(text="🔍 All categories", callback_data=back_to_main_callback)
    back_to_main_builder.add(back_to_main_button)
    if confirmation and is_in_stock and is_enough_money:
        User.update_consume_records(callback.from_user.id, total_price)
        sold_data = Item.get_bought_items(subcategory, quantity)
        message = await create_message_with_bought_items(sold_data)
        user = User.get_by_tgid(telegram_id)
        user_id = user['user_id']
        buy = Buy(user_id, quantity, total_price)
        buy.insert_new()
        BuyItem.insert_many(sold_data, buy.buy_id)
        Item.set_items_sold(sold_data)
        await callback.message.edit_text(text=message, parse_mode='html')
        await NotificationManager.new_buy(subcategory, quantity, total_price, user)
    elif is_in_stock is False:
        await callback.message.edit_text(text='<b>Out of stock!</b>', parse_mode='html',
                                         reply_markup=back_to_main_builder.as_markup())
    elif is_enough_money is False:
        await callback.message.edit_text(text='<b>Insufficient funds!</b>', parse_mode='html',
                                         reply_markup=back_to_main_builder.as_markup())
    elif confirmation is False:
        await callback.message.edit_text(text='<b>Declined!</b>', parse_mode='html',
                                         reply_markup=back_to_main_builder.as_markup())


async def create_message_with_bought_items(bought_data: list):
    message = "<b>"
    for count, item in enumerate(bought_data, start=1):
        private_data = item['private_data']
        message += f"Item#{count}\nData:<code>{private_data}</code>\n"
    message += "</b>"
    return message


@all_categories_router.callback_query(AllCategoriesCallback.filter())
async def navigate_categories(call: CallbackQuery, callback_data: AllCategoriesCallback):
    current_level = callback_data.level

    levels = {
        0: all_categories,
        1: show_subcategories_in_category,
        2: select_quantity,
        3: buy_confirmation,
        4: buy_processing
    }

    current_level_function = levels[current_level]

    await current_level_function(call)
