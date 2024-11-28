from typing import Tuple

from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
import config
from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from models.category import Category
from models.item import Item
from db import session_execute, get_db_session
from repositories.category import CategoryRepository
from utils.localizator import Localizator


class CategoryService:

    @staticmethod
    async def get_by_primary_key(primary_key: int) -> Category:
        async with get_db_session() as session:
            stmt = select(Category).where(Category.id == primary_key)
            category = await session_execute(stmt, session)
            return category.scalar()

    @staticmethod
    async def get_to_delete(page: int = 0):
        async with get_db_session() as session:
            stmt = select(Category).join(Item, Item.category_id == Category.id
                                         ).where(Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES).group_by(Category.name)
            categories = await session_execute(stmt, session)
            return categories.scalars().all()

    @staticmethod
    async def get_unsold(page) -> list[Category]:
        async with get_db_session() as session:
            stmt = select(Category).join(Item, Item.category_id == Category.id).where(
                Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES).group_by(Category.name)
            category_names = await session_execute(stmt, session)
            return category_names.scalars().all()

    @staticmethod
    async def get_name(category_id) -> str:
        async with get_db_session() as session:
            stmt = select(Category.name).where(Category.id == category_id)
            category_name = await session.execute(stmt)
            category_name = category_name.scalar()
            if category_name is None:
                return ""
        return category_name

    @staticmethod
    async def get_buttons(callback: CallbackQuery | None = None) -> tuple[str, InlineKeyboardBuilder]:
        if callback is None:
            unpacked_cb = AllCategoriesCallback.create(0)
        else:
            unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        categories = await CategoryRepository.get(unpacked_cb.page)
        categories_builder = InlineKeyboardBuilder()
        [categories_builder.button(text=category.name,
                                   callback_data=AllCategoriesCallback.create(
                                       level=1,
                                       category_id=category.id)) for category in categories]
        categories_builder.adjust(2)
        categories_builder = await add_pagination_buttons(categories_builder, unpacked_cb,
                                                          CategoryRepository.get_maximum_page(),
                                                          None)
        if len(categories_builder.as_markup().inline_keyboard) == 0:
            return Localizator.get_text(BotEntity.USER, "no_categories"), categories_builder
        else:
            return Localizator.get_text(BotEntity.USER, "all_categories"), categories_builder
