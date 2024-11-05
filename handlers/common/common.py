from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.localizator import Localizator, BotEntity


async def add_pagination_buttons(keyboard_builder: InlineKeyboardBuilder, callback_str: str, max_page_function,
                                 callback_unpack_function, back_button) -> InlineKeyboardBuilder:
    unpacked_callback = callback_unpack_function(callback_str)
    maximum_page = await max_page_function
    buttons = []
    if unpacked_callback.page > 0:
        back_page_callback = unpacked_callback.__copy__()
        back_page_callback.page -= 1
        first_page_callback = unpacked_callback.__copy__()
        first_page_callback.page = 0
        buttons.append(
            types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_first"),
                                       callback_data=first_page_callback.pack()))
        buttons.append(
            types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_previous"),
                                       callback_data=back_page_callback.pack()))
    if unpacked_callback.page < maximum_page:
        last_page_callback = unpacked_callback.__copy__()
        last_page_callback.page = maximum_page
        unpacked_callback.page += 1
        buttons.append(
            types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_next"),
                                       callback_data=unpacked_callback.pack()))
        buttons.append(
            types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_last"),
                                       callback_data=last_page_callback.pack()))
    keyboard_builder.row(*buttons)
    if back_button:
        keyboard_builder.row(back_button)
    return keyboard_builder
