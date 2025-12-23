from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons, add_search_button, get_filters_settings
from repositories.button_media import ButtonMediaRepository
from repositories.category import CategoryRepository
from services.media import MediaService
from utils.utils import get_text


class CategoryService:

    @staticmethod
    async def get_buttons(
            callback_data: AllCategoriesCallback | None,
            state: FSMContext,
            session: AsyncSession,
            language: Language
    ) -> tuple[InputMediaPhoto | InputMediaVideo | InputMediaAnimation, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        callback_data = callback_data or AllCategoriesCallback.create(1, **state_data.get("entity_id_dict"))
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        categories = await CategoryRepository.get(
            sort_pairs, filters, callback_data.item_type, callback_data.page, session
        )
        kb_builder = InlineKeyboardBuilder()
        for category in categories:
            kb_builder.button(
                text=category.name,
                callback_data=AllCategoriesCallback.create(level=callback_data.level + 1,
                                                           item_type=callback_data.item_type,
                                                           category_id=category.id
                )
            )

        has_categories = len(categories) > 0
        if not has_categories:
            caption = get_text(language, BotEntity.USER, "no_categories")
        else:
            kb_builder.adjust(2)
            if callback_data.item_type:
                item_type = callback_data.item_type.get_localized(language)
            else:
                item_type = get_text(language, BotEntity.COMMON, "all")
            caption = get_text(language, BotEntity.USER, "pick_category").format(
                item_type=item_type
            )
            kb_builder.row(
                InlineKeyboardButton(
                    text=get_text(language, BotEntity.COMMON, "pick_all_categories"),
                    callback_data=AllCategoriesCallback.create(level=callback_data.level + 1,
                                                               item_type=callback_data.item_type).pack()
                )
            )
        kb_builder = await add_search_button(kb_builder, EntityType.CATEGORY, callback_data, filters, language)
        kb_builder = await add_sorting_buttons(
            kb_builder, [SortProperty.NAME], callback_data, sort_pairs, language
        )
        kb_builder = await add_pagination_buttons(
            kb_builder, callback_data, CategoryRepository.get_maximum_page(filters, session),
            callback_data.get_back_button(language, 0), language
        )
        button_media = await ButtonMediaRepository.get_by_button(
            KeyboardButton.ALL_CATEGORIES, session
        )
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder
