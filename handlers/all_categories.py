from typing import Union

from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.callback_data import CallbackData

from models.item import Item

all_categories_cb = CallbackData("all_categories", "level", "category", "subcategory", "price", "quantity",
                                 "total_price", "action",
                                 "confirmation")


def create_callback_all_categories(level: int,
                                   category: str = "",
                                   subcategory: str = "",
                                   price: float = 0.0,
                                   total_price: float = 0.0,
                                   quantity: int = 0,
                                   action: str = "",
                                   confirmation: bool = False):
    return all_categories_cb.new(level, category=category, subcategory=subcategory, price=price,
                                 total_price=total_price,
                                 quantity=quantity, action=action, confirmation=confirmation)


async def all_categories_text_message(message: types.message):
    await all_categories(message)


async def create_category_buttons():
    current_level = 0
    categories = Item.get_categories()
    if categories:
        categories_markup = types.InlineKeyboardMarkup(row_width=2)
        for category in categories:
            category_name = category['category']
            category_button_callback = create_callback_all_categories(level=current_level + 1, category=category_name,
                                                                      action="show_category")
            category_button = types.InlineKeyboardButton(category_name, callback_data=category_button_callback)
            categories_markup.insert(category_button)
        return categories_markup


async def create_subcategory_buttons(category: str):
    current_level = 1
    subcategories = Item.get_subcategories()
    subcategories_markup = types.InlineKeyboardMarkup(row_width=1)
    for subcategory in subcategories:
        subcategory_name = subcategory['subcategory']
        subcategory_price = subcategory['price']
        subcategory_inline_button = create_callback_all_categories(level=current_level + 1,
                                                                   category=category,
                                                                   subcategory=subcategory_name,
                                                                   price=subcategory_price)
        subcategories_markup.insert(
            types.InlineKeyboardButton(text=f"{subcategory_name}| ${subcategory_price}", callback_data=subcategory_inline_button))
    back_button = types.InlineKeyboardButton("Back", callback_data=create_callback_all_categories(level=current_level-1))
    subcategories_markup.insert(back_button)
    return subcategories_markup


async def all_categories(message: Union[Message, CallbackQuery]):
    current_level = 0
    category_inline_buttons = await create_category_buttons()
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
    #TODO("fix getter category from callback")
    category = callback.__dict__.get("category")
    subcategory_buttons = await create_subcategory_buttons(category)
    await callback.message.edit_text("<b>Subcategories:</b>", reply_markup=subcategory_buttons, parse_mode="html")


async def navigate_categories(call: CallbackQuery, callback_data: dict):
    current_level = callback_data.get("level")

    levels = {
        "0": all_categories,
        "1": show_subcategories_in_category,
        # "2": purchase_history,
        # "3": refresh_balance,
    }

    current_level_function = levels[current_level]

    await current_level_function(call)
