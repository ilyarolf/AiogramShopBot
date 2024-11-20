import math

from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func, delete
import config
from callbacks import AllCategoriesCallback
from db import session_commit, session_execute, session_refresh, get_db_session
from handlers.common.common import add_pagination_buttons
from handlers.user.constants import UserConstants
from models.item import Item
from models.subcategory import Subcategory
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from services.category import CategoryService
from utils.localizator import Localizator, BotEntity


class SubcategoryService:

    @staticmethod
    async def get_or_create_one(subcategory_name: str) -> Subcategory:
        async with get_db_session() as session:
            stmt = select(Subcategory).where(Subcategory.name == subcategory_name)
            subcategory = await session_execute(stmt, session)
            subcategory = subcategory.scalar()
            if subcategory is None:
                new_category_obj = Subcategory(name=subcategory_name)
                session.add(new_category_obj)
                await session_commit(session)
                await session_refresh(session, new_category_obj)
                return new_category_obj
            else:
                return subcategory

    @staticmethod
    async def get_to_delete(page: int = 0) -> list[Subcategory]:
        async with get_db_session() as session:
            stmt = select(Subcategory).join(Item,
                                            Item.subcategory_id == Subcategory.id).where(
                Item.is_sold == 0).distinct().limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES).group_by(Subcategory.name)
            subcategories = await session_execute(stmt, session=session)
            subcategories = subcategories.scalars().all()
            return subcategories

    @staticmethod
    async def get_maximum_page():
        async with get_db_session() as session:
            stmt = select(func.count(Subcategory.id)).distinct()
            subcategories = await session_execute(stmt, session)
            subcategories_count = subcategories.scalar_one()
            if subcategories_count % SubcategoryService.items_per_page == 0:
                return subcategories_count / SubcategoryService.items_per_page - 1
            else:
                return math.trunc(subcategories_count / SubcategoryService.items_per_page)

    @staticmethod
    async def get_maximum_page_to_delete():
        async with get_db_session() as session:
            unique_categories_subquery = (
                select(Subcategory.id)
                .join(Item, Item.subcategory_id == Subcategory.id)
                .filter(Item.is_sold == 0)
                .distinct()
            ).alias('unique_categories')
            stmt = select(func.count()).select_from(unique_categories_subquery)
            max_page = await session_execute(stmt, session)
            max_page = max_page.scalar_one()
            if max_page % config.PAGE_ENTRIES == 0:
                return max_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_by_primary_key(subcategory_id: int) -> Subcategory:
        async with get_db_session() as session:
            stmt = select(Subcategory).where(Subcategory.id == subcategory_id)
            subcategory = await session_execute(stmt, session)
            return subcategory.scalar()

    @staticmethod
    async def delete_if_not_used(subcategory_id: int):
        # TODO("Need testing")
        async with get_db_session() as session:
            stmt = select(Subcategory).join(Item, Item.subcategory_id == subcategory_id).where(
                Subcategory.id == subcategory_id)
            result = await session_execute(stmt, session)
            if result.scalar() is None:
                stmt = delete(Subcategory).where(Subcategory.id == subcategory_id)
                await session_execute(stmt, session)
                await session_commit(session)

    # new methods________________
    @staticmethod
    async def get_buttons(unpacked_cb: AllCategoriesCallback) -> InlineKeyboardBuilder:
        kb_builder = InlineKeyboardBuilder()
        subcategories = await SubcategoryRepository.get_paginated_by_category_id(unpacked_cb.category_id,
                                                                                 unpacked_cb.page)
        for subcategory in subcategories:
            price = await ItemRepository.get_price(unpacked_cb.category_id, subcategory.id)
            available_qty = await ItemRepository.get_available_qty(unpacked_cb.category_id, subcategory.id)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "subcategory_button").format(
                subcategory_name=subcategory.name,
                subcategory_price=price,
                available_quantity=available_qty,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=AllCategoriesCallback.create(
                    2,
                    unpacked_cb.category_id,
                    subcategory.id,
                    price
                )
            )
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                  SubcategoryRepository.max_page(unpacked_cb.category_id),
                                                  UserConstants.get_back_button(unpacked_cb))
        return kb_builder
