from aiogram.types import InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from repositories.category import CategoryRepository
from utils.localizator import Localizator
from utils.utils import get_bot_photo_id


class CategoryService:

    @staticmethod
    async def get_buttons(session: AsyncSession,
                          callback_data: AllCategoriesCallback | None) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        if callback_data is None:
            callback_data = AllCategoriesCallback.create(0)
        categories = await CategoryRepository.get(callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        [kb_builder.button(text=category.name,
                           callback_data=AllCategoriesCallback.create(
                               level=1,
                               category_id=category.id)) for category in categories]
        kb_builder.adjust(2)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  CategoryRepository.get_maximum_page(session),
                                                  None)
        if len(kb_builder.as_markup().inline_keyboard) == 0:
            caption = Localizator.get_text(BotEntity.USER, "no_categories")
        else:
            caption = Localizator.get_text(BotEntity.USER, "all_categories")
        bot_photo_id = get_bot_photo_id()
        return InputMediaPhoto(media=bot_photo_id, caption=caption), kb_builder
