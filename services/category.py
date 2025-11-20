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
    async def get_buttons(session: AsyncSession,
                          callback_data: AllCategoriesCallback | None) -> tuple[InputMediaPhoto |
                                                                                InputMediaVideo |
                                                                                InputMediaAnimation,
    InlineKeyboardBuilder]:
        if callback_data is None:
            callback_data = AllCategoriesCallback.create(0)
        categories = await CategoryRepository.get(callback_data.sort_property, callback_data.sort_order,
                                                  callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        [kb_builder.button(text=category.name,
                           callback_data=AllCategoriesCallback.create(
                               level=1,
                               category_id=category.id)) for category in categories]
        kb_builder.adjust(2)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.NAME], callback_data)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  CategoryRepository.get_maximum_page(session),
                                                  None)
        if len(kb_builder.as_markup().inline_keyboard) == 0:
            caption = Localizator.get_text(BotEntity.USER, "no_categories")
        else:
            caption = Localizator.get_text(BotEntity.USER, "all_categories")
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.ALL_CATEGORIES, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder
