from aiogram.types import InputMediaVideo, InputMediaAnimation, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from services.media import MediaService
from utils.localizator import Localizator


class SubcategoryService:

    @staticmethod
    async def get_buttons(callback_data: AllCategoriesCallback,
                          session: AsyncSession) -> tuple[InputMediaPhoto |
                                                          InputMediaAnimation |
                                                          InputMediaVideo, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        subcategories = await SubcategoryRepository.get_paginated_by_category_id(callback_data.category_id,
                                                                                 callback_data.page, session)
        for subcategory in subcategories:
            item = await ItemRepository.get_single(callback_data.category_id, subcategory.id, session)
            available_qty = await ItemRepository.get_available_qty(ItemDTO(category_id=callback_data.category_id,
                                                                           subcategory_id=subcategory.id), session)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "subcategory_button").format(
                subcategory_name=subcategory.name,
                subcategory_price=item.price,
                available_quantity=available_qty,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=AllCategoriesCallback.create(
                    callback_data.level + 1,
                    callback_data.category_id,
                    subcategory.id
                )
            )
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  SubcategoryRepository.max_page(callback_data.category_id, session),
                                                  callback_data.get_back_button())
        category_dto = await CategoryRepository.get_by_id(callback_data.category_id, session)
        caption = Localizator.get_text(BotEntity.USER, "subcategories")
        media = MediaService.convert_to_media(category_dto.media_id, caption)
        return media, kb_builder

    @staticmethod
    async def get_select_quantity_buttons(callback_data: AllCategoriesCallback,
                                          session: AsyncSession) -> tuple[InputMediaPhoto |
                                                          InputMediaAnimation |
                                                          InputMediaVideo, InlineKeyboardBuilder]:
        item_dto = await ItemRepository.get_single(callback_data.category_id, callback_data.subcategory_id, session)
        subcategory_dto = await SubcategoryRepository.get_by_id(callback_data.subcategory_id, session)
        category_dto = await CategoryRepository.get_by_id(callback_data.category_id, session)
        available_qty = await ItemRepository.get_available_qty(item_dto, session)
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
