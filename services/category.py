from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.keyboardbutton import KeyboardButton
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons, add_search_button, get_filters_settings
from repositories.button_media import ButtonMediaRepository
from repositories.category import CategoryRepository
from services.media import MediaService
from utils.localizator import Localizator


class CategoryService:

    @staticmethod
    async def get_buttons(
            callback_data: AllCategoriesCallback | None,
            state: FSMContext,
            session: AsyncSession,
    ) -> tuple[InputMediaPhoto | InputMediaVideo | InputMediaAnimation, InlineKeyboardBuilder]:
        callback_data = callback_data or AllCategoriesCallback.create(0)
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        categories = await CategoryRepository.get(
            sort_pairs, filters, callback_data.page, session
        )
        kb_builder = InlineKeyboardBuilder()
        for category in categories:
            kb_builder.button(
                text=category.name,
                callback_data=AllCategoriesCallback.create(
                    level=1, category_id=category.id
                )
            )

        has_categories = len(categories) > 0
        if not has_categories:
            caption = Localizator.get_text(BotEntity.USER, "no_categories")
        else:
            kb_builder.adjust(2)
            caption = Localizator.get_text(BotEntity.USER, "pick_category")
            kb_builder.row(
                InlineKeyboardButton(
                    text=Localizator.get_text(BotEntity.COMMON, "pick_all_categories"),
                    callback_data=AllCategoriesCallback.create(level=1).pack()
                )
            )
        kb_builder = await add_search_button(kb_builder, EntityType.CATEGORY, callback_data, filters)
        kb_builder = await add_sorting_buttons(
            kb_builder, [SortProperty.NAME], callback_data, sort_pairs
        )
        kb_builder = await add_pagination_buttons(
            kb_builder, callback_data, CategoryRepository.get_maximum_page(filters, session), None
        )
        button_media = await ButtonMediaRepository.get_by_button(
            KeyboardButton.ALL_CATEGORIES, session
        )
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder
