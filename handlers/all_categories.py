from typing import Union

from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.utils.callback_data import CallbackData

from models.item import Item
from models.user import User

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
        available_quantity = Item.get_available_quantity(subcategory_name)
        subcategory_inline_button = create_callback_all_categories(level=current_level + 1,
                                                                   category=category,
                                                                   subcategory=subcategory_name,
                                                                   price=subcategory_price)
        subcategories_markup.insert(
            types.InlineKeyboardButton(
                text=f"{subcategory_name}| Price: ${subcategory_price} | Quantity: {available_quantity} pcs",
                callback_data=subcategory_inline_button))
    back_button = types.InlineKeyboardButton("Back",
                                             callback_data=create_callback_all_categories(level=current_level - 1))
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
    category = all_categories_cb.parse(callback.data)['category']
    subcategory_buttons = await create_subcategory_buttons(category)
    await callback.message.edit_text("<b>Subcategories:</b>", reply_markup=subcategory_buttons, parse_mode="html")


async def select_quantity(callback: CallbackQuery):
    price = float(all_categories_cb.parse(callback.data)['price'])
    subcategory = all_categories_cb.parse(callback.data)['subcategory']
    category = all_categories_cb.parse(callback.data)['category']
    current_level = int(all_categories_cb.parse(callback.data)['level'])
    description = Item.get_description(subcategory)
    count_markup = types.InlineKeyboardMarkup()
    for i in range(1, 11):
        count_button_callback = create_callback_all_categories(level=current_level + 1, category=category,
                                                               subcategory=subcategory, price=price,
                                                               quantity=i, action="select_quantity",
                                                               total_price=price * i)
        count_button_inline = types.InlineKeyboardButton(text=str(i), callback_data=count_button_callback)
        count_markup.insert(count_button_inline)
    back_button = types.InlineKeyboardButton("Back",
                                             callback_data=create_callback_all_categories(level=current_level - 1))
    count_markup.add(back_button)
    await callback.message.edit_text(f'<b>You choose:{subcategory}\n'
                                     f'Price:${price}\n'
                                     f'Description:{description}\n'
                                     f'Quantity:</b>', reply_markup=count_markup, parse_mode='html')


async def buy_confirmation(callback: CallbackQuery):
    price = float(all_categories_cb.parse(callback.data)['price'])
    total_price = float(all_categories_cb.parse(callback.data)['total_price'])
    subcategory = all_categories_cb.parse(callback.data)['subcategory']
    category = all_categories_cb.parse(callback.data)['category']
    current_level = int(all_categories_cb.parse(callback.data)['level'])
    quantity = int(all_categories_cb.parse(callback.data)['quantity'])
    description = Item.get_description(subcategory)
    confirmation_markup = types.InlineKeyboardMarkup(row_width=2)
    confirm_button_callback = create_callback_all_categories(level=current_level + 1,
                                                             category=category,
                                                             subcategory=subcategory,
                                                             price=price,
                                                             total_price=total_price,
                                                             quantity=quantity,
                                                             action="buy_confirmation",
                                                             confirmation=True)
    decline_button_callback = create_callback_all_categories(level=current_level + 1,
                                                             category=category,
                                                             subcategory=subcategory,
                                                             price=price,
                                                             total_price=total_price,
                                                             quantity=quantity,
                                                             action="buy_confirmation",
                                                             confirmation=False)
    confirmation_button = types.InlineKeyboardButton(text="Confirm", callback_data=confirm_button_callback)
    decline_button = types.InlineKeyboardButton(text="Decline", callback_data=decline_button_callback)
    back_button = types.InlineKeyboardButton("Back",
                                             callback_data=create_callback_all_categories(level=current_level - 1,
                                                                                          category=category,
                                                                                          subcategory=subcategory,
                                                                                          price=price,
                                                                                          action='select_quantity'))
    confirmation_markup.add(confirmation_button, decline_button, back_button)
    await callback.message.edit_text(text=f'<b>You choose:{subcategory}\n'
                                          f'Price:${price}\n'
                                          f'Description:{description}\n'
                                          f'Quantity:{quantity}\n'
                                          f'Total price:${total_price}</b>', reply_markup=confirmation_markup,
                                     parse_mode='html')


async def buy_processing(callback: CallbackQuery):
    callback_data = all_categories_cb.parse(callback.data)
    confirmation = callback_data.get('confirmation') == 'True'
    total_price = float(callback_data.get('total_price'))
    quantity = int(callback_data.get('quantity'))
    subcategory = callback_data.get('subcategory')
    telegram_id = callback.from_user.id
    is_in_stock = Item.get_available_quantity(subcategory) >= quantity
    is_enough_money = User.is_buy_possible(telegram_id, total_price)
    back_to_main_markup = types.InlineKeyboardMarkup()
    back_to_main_callback = create_callback_all_categories(level=0)
    back_to_main_button = types.InlineKeyboardButton(text="🔍 All categories", callback_data=back_to_main_callback)
    back_to_main_markup.add(back_to_main_button)
    if confirmation and is_in_stock and is_enough_money:
        User.update_consume_records(callback.from_user.id, total_price)
        sold_data = Item.get_bought_items(subcategory, quantity)
        message = await create_message_with_bought_items(sold_data)
        await callback.message.edit_text(text=message, parse_mode='html')
    elif is_in_stock is False:
        await callback.message.edit_text(text='<b>Out of stock!</b>', parse_mode='html',
                                         reply_markup=back_to_main_markup)
    elif is_enough_money is False:
        await callback.message.edit_text(text='<b>Insufficient funds!</b>', parse_mode='html',
                                         reply_markup=back_to_main_markup)
    elif confirmation is False:
        await callback.message.edit_text(text='<b>Declined!</b>', parse_mode='html', reply_markup=back_to_main_markup)


async def create_message_with_bought_items(bought_data: list):
    message = "<b>"
    for count, item in enumerate(bought_data, start=1):
        private_data = item['private_data']
        message += f"Item#{count}\nData:<code>{private_data}</code>\n"
    message += "</b>"
    return message


async def navigate_categories(call: CallbackQuery, callback_data: dict):
    current_level = callback_data.get("level")

    levels = {
        "0": all_categories,
        "1": show_subcategories_in_category,
        "2": select_quantity,
        "3": buy_confirmation,
        "4": buy_processing
    }

    current_level_function = levels[current_level]

    await current_level_function(call)
