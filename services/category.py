from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.keyboardbutton import KeyboardButton
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons
from handlers.user.constants import UserStates
from repositories.button_media import ButtonMediaRepository
from repositories.category import CategoryRepository
from services.media import MediaService
from utils.localizator import Localizator
from utils.utils import get_bot_photo_id


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
        if state_data.get("filter") is not None:
            filters = state_data.get("filter").split(",")
            filters = [filter.strip() for filter in filters]
            callback_data.is_filter_enabled = True
        else:
            filters = None
        categories = await CategoryRepository.get(sort_pairs, filters, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        [kb_builder.button(text=category.name,
                           callback_data=AllCategoriesCallback.create(
                               level=1,
                               category_id=category.id)) for category in categories]
        if len(kb_builder.as_markup().inline_keyboard) == 0:
            caption = Localizator.get_text(BotEntity.USER, "no_categories")
        else:
            kb_builder.adjust(2)
            caption = Localizator.get_text(BotEntity.USER, "pick_category")
            kb_builder.row(InlineKeyboardButton(
                text=Localizator.get_text(BotEntity.COMMON, "pick_all_categories"),
                callback_data=AllCategoriesCallback.create(level=1).pack()
            ))
            if callback_data.is_filter_enabled or filters is not None:
                search_button_text = Localizator.get_text(BotEntity.COMMON, "cancel")
            else:
                search_button_text = Localizator.get_text(BotEntity.COMMON, "search").format(
                    entity=Localizator.get_text(BotEntity.COMMON, "category"),
                    field=Localizator.get_text(BotEntity.COMMON, "name")
                )
            kb_builder.row(InlineKeyboardButton(
                text=search_button_text,
                callback_data=AllCategoriesCallback.create(
                    level=0,
                    is_filter_enabled=not callback_data.is_filter_enabled
                ).pack())
            )
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.NAME], callback_data, sort_pairs)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  CategoryRepository.get_maximum_page(filters, session),
                                                  None)
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.ALL_CATEGORIES, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def enable_search(callback_data: AllCategoriesCallback,
                            entity_type: EntityType,
                            state: FSMContext) -> [InputMediaPhoto, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        callback_data.is_filter_enabled = False
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "cancel"),
            callback_data=callback_data
        )
        await state.set_state(UserStates.filter)
        await state.update_data(entity_type=entity_type.value)
        caption = Localizator.get_text(BotEntity.COMMON, "search_by_field_request").format(
            entity=entity_type.get_localized(),
            field=Localizator.get_text(BotEntity.COMMON, "name")
        )
        return InputMediaPhoto(media=get_bot_photo_id(), caption=caption), kb_builder
