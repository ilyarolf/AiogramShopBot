from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaVideo, InputMediaAnimation, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons, get_filters_settings, add_search_button
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from services.media import MediaService
from utils.localizator import Localizator
from utils.utils import get_bot_photo_id


class SubcategoryService:

    @staticmethod
    async def get_buttons(callback_data: AllCategoriesCallback | None,
                          state: FSMContext,
                          session: AsyncSession) -> tuple[InputMediaPhoto |
                                                          InputMediaAnimation |
                                                          InputMediaVideo, InlineKeyboardBuilder]:
        callback_data = callback_data or AllCategoriesCallback.create(1)
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        kb_builder = InlineKeyboardBuilder()
        items = await SubcategoryRepository.get_paginated_by_category_id(sort_pairs, filters,
                                                                         callback_data.category_id,
                                                                         callback_data.page, session)
        for item in items:
            available_qty = await ItemRepository.get_available_qty(category_id=item.category_id,
                                                                   subcategory_id=item.subcategory_id,
                                                                   session=session)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "subcategory_button").format(
                subcategory_name=item.subcategory_name,
                subcategory_price=item.price,
                available_quantity=available_qty,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=AllCategoriesCallback.create(
                    level=callback_data.level + 1,
                    category_id=item.category_id,
                    subcategory_id=item.subcategory_id
                )
            )
        kb_builder.adjust(1)
        kb_builder = await add_search_button(kb_builder, EntityType.SUBCATEGORY, callback_data, filters)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.NAME, SortProperty.PRICE],
                                               callback_data, sort_pairs)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  SubcategoryRepository.get_maximum_page(callback_data.category_id, filters, session),
                                                  callback_data.get_back_button())
        caption = Localizator.get_text(BotEntity.USER, "pick_subcategory")
        if callback_data.category_id:
            category_dto = await CategoryRepository.get_by_id(callback_data.category_id, session)
            caption = caption.format(
                category_name=category_dto.name
            )
            media = MediaService.convert_to_media(category_dto.media_id, caption)
        else:
            caption = caption.format(
                category_name=Localizator.get_text(BotEntity.COMMON, "all")
            )
            media = InputMediaPhoto(media=get_bot_photo_id(), caption=caption)
        return media, kb_builder

    @staticmethod
    async def get_select_quantity_buttons(callback_data: AllCategoriesCallback,
                                          session: AsyncSession) -> tuple[InputMediaPhoto |
                                                                          InputMediaAnimation |
                                                                          InputMediaVideo, InlineKeyboardBuilder]:
        item_dto = await ItemRepository.get_single(callback_data.category_id, callback_data.subcategory_id, session)
        subcategory_dto = await SubcategoryRepository.get_by_id(callback_data.subcategory_id, session)
        category_dto = await CategoryRepository.get_by_id(callback_data.category_id, session)
        available_qty = await ItemRepository.get_available_qty(category_id=callback_data.category_id,
                                                               subcategory_id=callback_data.subcategory_id,
                                                               session=session)
        caption = Localizator.get_text(BotEntity.USER, "select_quantity").format(
            category_name=category_dto.name,
            subcategory_name=subcategory_dto.name,
            price=item_dto.price,
            description=item_dto.description,
            quantity=available_qty,
            currency_sym=Localizator.get_currency_symbol()
        )
        kb_builder = InlineKeyboardBuilder()
        for i in range(1, 11):
            kb_builder.button(text=str(i), callback_data=AllCategoriesCallback.create(
                callback_data.level + 1,
                item_dto.category_id,
                item_dto.subcategory_id,
                quantity=i
            ))
        kb_builder.adjust(3)
        kb_builder.row(callback_data.get_back_button())
        media = MediaService.convert_to_media(subcategory_dto.media_id, caption)
        return media, kb_builder

    @staticmethod
    async def get_add_to_cart_buttons(callback_data: AllCategoriesCallback, session: AsyncSession | Session) -> tuple[
        str, InlineKeyboardBuilder]:
        item = await ItemRepository.get_single(callback_data.category_id, callback_data.subcategory_id, session)
        category = await CategoryRepository.get_by_id(callback_data.category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(callback_data.subcategory_id, session)
        message_text = Localizator.get_text(BotEntity.USER, "buy_confirmation").format(
            category_name=category.name,
            subcategory_name=subcategory.name,
            price=item.price,
            description=item.description,
            quantity=callback_data.quantity,
            total_price=item.price * callback_data.quantity,
            currency_sym=Localizator.get_currency_symbol())
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=AllCategoriesCallback.create(
                              callback_data.level + 1,
                              callback_data.category_id,
                              callback_data.subcategory_id,
                              quantity=callback_data.quantity,
                              confirmation=True
                          ))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=AllCategoriesCallback.create(
                              1,
                              callback_data.category_id
                          ))
        kb_builder.row(callback_data.get_back_button())
        return message_text, kb_builder
