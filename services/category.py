from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.keyboardbutton import KeyboardButton
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons
from repositories.button_media import ButtonMediaRepository
from repositories.category import CategoryRepository
from services.media import MediaService
from utils.localizator import Localizator


class CategoryService:

    @staticmethod
    async def get_buttons(callback_data: AllCategoriesCallback | None,
                          state: FSMContext,
                          session: AsyncSession,
                          ) -> tuple[InputMediaPhoto |
                                     InputMediaVideo |
                                     InputMediaAnimation,
    InlineKeyboardBuilder]:
        state_data = await state.get_data()
        if callback_data is None:
            callback_data = AllCategoriesCallback.create(0)
        sort_pairs = state_data.get("sort_pairs") or {}
        sort_pairs[str(callback_data.sort_property.value)] = callback_data.sort_order.value
        await state.update_data(sort_pairs=sort_pairs)
        categories = await CategoryRepository.get(sort_pairs, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        [kb_builder.button(text=category.name,
                           callback_data=AllCategoriesCallback.create(
                               level=1,
                               category_id=category.id)) for category in categories]
        kb_builder.adjust(2)
        if len(kb_builder.as_markup().inline_keyboard) == 0:
            caption = Localizator.get_text(BotEntity.USER, "no_categories")
        else:
            caption = Localizator.get_text(BotEntity.USER, "all_categories")

        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.NAME], callback_data, sort_pairs)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  CategoryRepository.get_maximum_page(session),
                                                  None)
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.ALL_CATEGORIES, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder
