from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from utils.localizator import Localizator


async def add_pagination_buttons(keyboard_builder: InlineKeyboardBuilder, callback_data, max_page_function,
                                 back_button) -> InlineKeyboardBuilder:
    maximum_page = await max_page_function
    buttons = []
    if callback_data.page > 0:
        back_page_callback = callback_data.__copy__()
        back_page_callback.page -= 1
        first_page_callback = callback_data.__copy__()
        first_page_callback.page = 0
        buttons.append(
            InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_first"),
                                 callback_data=first_page_callback.pack()))
        buttons.append(
            InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_previous"),
                                 callback_data=back_page_callback.pack()))
    if callback_data.page < maximum_page:
        last_page_callback = callback_data.__copy__()
        last_page_callback.page = maximum_page
        callback_data.page += 1
        buttons.append(
            InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_next"),
                                 callback_data=callback_data.pack()))
        buttons.append(
            InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "pagination_last"),
                                 callback_data=last_page_callback.pack()))
    keyboard_builder.row(*buttons)
    if back_button:
        keyboard_builder.row(back_button)
    return keyboard_builder


async def add_sorting_buttons(keyboard_builder: InlineKeyboardBuilder, sort_property_list: list[SortProperty],
                              callback_data: AllCategoriesCallback) -> InlineKeyboardBuilder:
    sort_cb_copy = callback_data.__copy__()
    buttons = []
    for sort_property in sort_property_list:
        sort_cb_copy.sort_property = sort_property
        buttons.append(
            InlineKeyboardButton(
                text=f"{sort_property.get_localized()} {sort_cb_copy.sort_order.get_localized()}",
                callback_data=callback_data.create(**{**sort_cb_copy.model_dump(),
                                                      "sort_order": SortOrder(
                                                          not callback_data.sort_order.value)}).pack()
            )
        )
    keyboard_builder.row(*buttons)
    return keyboard_builder
