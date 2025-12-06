from typing import Awaitable
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import InlineKeyboardButton, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import SortingCallback, BaseCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.language import Language
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from utils.utils import get_bot_photo_id, get_text


async def add_pagination_buttons(keyboard_builder: InlineKeyboardBuilder,
                                 callback_data: BaseCallback,
                                 max_page_function: Awaitable[int],
                                 back_button: InlineKeyboardButton | None,
                                 language: Language) -> InlineKeyboardBuilder:
    maximum_page = await max_page_function
    buttons = []
    if callback_data.page > 0:
        back_page_callback = callback_data.__copy__()
        back_page_callback.page -= 1
        first_page_callback = callback_data.__copy__()
        first_page_callback.page = 0
        buttons.append(
            InlineKeyboardButton(text=get_text(language, BotEntity.COMMON, "pagination_first"),
                                 callback_data=first_page_callback.pack()))
        buttons.append(
            InlineKeyboardButton(text=get_text(language, BotEntity.COMMON, "pagination_previous"),
                                 callback_data=back_page_callback.pack()))
    if callback_data.page < maximum_page:
        last_page_callback = callback_data.__copy__()
        last_page_callback.page = maximum_page
        callback_data.page += 1
        buttons.append(
            InlineKeyboardButton(text=get_text(language, BotEntity.COMMON, "pagination_next"),
                                 callback_data=callback_data.pack()))
        buttons.append(
            InlineKeyboardButton(text=get_text(language, BotEntity.COMMON, "pagination_last"),
                                 callback_data=last_page_callback.pack()))
    keyboard_builder.row(*buttons)
    if back_button:
        keyboard_builder.row(back_button)
    return keyboard_builder


async def add_sorting_buttons(keyboard_builder: InlineKeyboardBuilder,
                              sort_property_list: list[SortProperty],
                              callback_data: SortingCallback,
                              sort_pairs: dict[str, int],
                              language: Language) -> InlineKeyboardBuilder:
    sort_cb_copy = callback_data.__copy__()
    buttons = []
    if len(keyboard_builder.as_markup().inline_keyboard) > 1:
        for sort_property in sort_property_list:
            sort_cb_copy.sort_property = sort_property
            sort_order_value = sort_pairs.get(str(sort_property.value))
            if sort_order_value is not None:
                sort_order = SortOrder(sort_order_value)
            else:
                sort_order = SortOrder.DISABLE
            buttons.append(
                InlineKeyboardButton(
                    text=f"{sort_property.get_localized(language)} {sort_order.get_localized(language)}",
                    callback_data=callback_data.create(**{**sort_cb_copy.model_dump(),
                                                          "sort_order": sort_order.next()}).pack()
                )
            )
        chunked = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
        for chunk in chunked:
            keyboard_builder.row(*chunk)
    return keyboard_builder


async def add_search_button(keyboard_builder: InlineKeyboardBuilder,
                            entity_type: EntityType,
                            callback_data: SortingCallback,
                            filters: list,
                            language: Language):
    is_search_mode = callback_data.is_filter_enabled or filters
    if len(keyboard_builder.as_markup().inline_keyboard) > 0 or is_search_mode:
        search_button_key = "cancel_search" if is_search_mode else "search"
        search_button_text = get_text(language, BotEntity.COMMON, search_button_key)
        if not is_search_mode:
            search_button_text = search_button_text.format(
                entity=entity_type.get_localized(language),
                field=get_text(language, BotEntity.COMMON, "name")
            )
        callback_copy = callback_data.copy()
        callback_copy.is_filter_enabled = not callback_copy.is_filter_enabled
        keyboard_builder.row(
            InlineKeyboardButton(
                text=search_button_text,
                callback_data=callback_copy.pack()
            )
        )
    return keyboard_builder


async def get_filters_settings(state: FSMContext,
                               callback_data: SortingCallback) -> tuple[dict[str, int], list[str]]:
    state_data = await state.get_data()
    sort_pairs = state_data.get("sort_pairs", {}).copy()
    sort_key = str(callback_data.sort_property.value)
    sort_pairs[sort_key] = callback_data.sort_order.value
    await state.update_data(sort_pairs=sort_pairs)
    filter_data = state_data.get("filter")
    if filter_data is not None:
        filters = [f.strip() for f in filter_data.split(",")]
        callback_data.is_filter_enabled = True
    else:
        filters = None
    return sort_pairs, filters


async def enable_search(callback_data: SortingCallback,
                        entity_type: EntityType,
                        state: FSMContext,
                        search_state: State,
                        language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
    kb_builder = InlineKeyboardBuilder()
    callback_data.is_filter_enabled = False
    kb_builder.button(
        text=get_text(language, BotEntity.COMMON, "cancel_search"),
        callback_data=callback_data
    )
    await state.set_state(search_state)
    await state.update_data(entity_type=entity_type.value)
    caption = get_text(language, BotEntity.COMMON, "search_by_field_request").format(
        entity=entity_type.get_localized(language),
        field=get_text(language, BotEntity.COMMON, "name")
    )
    return InputMediaPhoto(media=get_bot_photo_id(), caption=caption), kb_builder
