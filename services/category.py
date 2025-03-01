from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from repositories.category import CategoryRepository
from utils.localizator import Localizator


class CategoryService:

    @staticmethod
    async def get_buttons(session: AsyncSession | Session, callback: CallbackQuery | None = None) -> tuple[str, InlineKeyboardBuilder]:
        if callback is None:
            unpacked_cb = AllCategoriesCallback.create(0)
        else:
            unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        categories = await CategoryRepository.get(unpacked_cb.page, session)
        categories_builder = InlineKeyboardBuilder()
        [categories_builder.button(text=category.name,
                                   callback_data=AllCategoriesCallback.create(
                                       level=1,
                                       category_id=category.id)) for category in categories]
        categories_builder.adjust(2)
        categories_builder = await add_pagination_buttons(categories_builder, unpacked_cb,
                                                          CategoryRepository.get_maximum_page(session),
                                                          None)
        if len(categories_builder.as_markup().inline_keyboard) == 0:
            return Localizator.get_text(BotEntity.USER, "no_categories"), categories_builder
        else:
            return Localizator.get_text(BotEntity.USER, "all_categories"), categories_builder
