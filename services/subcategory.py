from aiogram.types import CallbackQuery
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
from utils.localizator import Localizator


class SubcategoryService:

    @staticmethod
    async def get_buttons(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        subcategories = await SubcategoryRepository.get_paginated_by_category_id(unpacked_cb.category_id,
                                                                                 unpacked_cb.page, session)
        for subcategory in subcategories:
            item = await ItemRepository.get_single(unpacked_cb.category_id, subcategory.id, session)
            available_qty = await ItemRepository.get_available_qty(ItemDTO(category_id=unpacked_cb.category_id,
                                                                           subcategory_id=subcategory.id), session)

            # Skip subcategories with zero stock (sold out or all reserved) or no items
            if available_qty == 0 or item is None:
                continue

            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "subcategory_button").format(
                subcategory_name=subcategory.name,
                subcategory_price=item.price,
                available_quantity=available_qty,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=AllCategoriesCallback.create(
                    unpacked_cb.level + 1,
                    unpacked_cb.category_id,
                    subcategory.id
                )
            )
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                  SubcategoryRepository.max_page(unpacked_cb.category_id, session),
                                                  unpacked_cb.get_back_button())
        return Localizator.get_text(BotEntity.USER, "subcategories"), kb_builder

    @staticmethod
    async def get_select_quantity_buttons(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        item = await ItemRepository.get_single(unpacked_cb.category_id, unpacked_cb.subcategory_id, session)
        subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.subcategory_id, session)
        category = await CategoryRepository.get_by_id(unpacked_cb.category_id, session)

        # If no item exists (all sold/reserved), show error
        if item is None:
            raise ValueError(f"No items found for subcategory {unpacked_cb.subcategory_id}")

        available_qty = await ItemRepository.get_available_qty(item, session)

        # Build message with shipping info for physical items
        if item.is_physical:
            message_text = Localizator.get_text(BotEntity.USER, "select_quantity_with_shipping").format(
                category_name=category.name,
                subcategory_name=subcategory.name,
                price=item.price,
                shipping_cost=item.shipping_cost,
                description=item.description,
                quantity=available_qty,
                currency_sym=Localizator.get_currency_symbol()
            )
        else:
            message_text = Localizator.get_text(BotEntity.USER, "select_quantity").format(
                category_name=category.name,
                subcategory_name=subcategory.name,
                price=item.price,
                description=item.description,
                quantity=available_qty,
                currency_sym=Localizator.get_currency_symbol()
            )
        kb_builder = InlineKeyboardBuilder()
        for i in range(1, 11):
            kb_builder.button(text=str(i), callback_data=AllCategoriesCallback.create(
                unpacked_cb.level + 1,
                item.category_id,
                item.subcategory_id,
                quantity=i
            ))
        kb_builder.adjust(3)
        kb_builder.row(unpacked_cb.get_back_button())
        return message_text, kb_builder

    @staticmethod
    async def get_add_to_cart_buttons(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        item = await ItemRepository.get_single(unpacked_cb.category_id, unpacked_cb.subcategory_id, session)
        category = await CategoryRepository.get_by_id(unpacked_cb.category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.subcategory_id, session)

        # If no item exists (all sold/reserved), show error
        if item is None:
            raise ValueError(f"No items found for subcategory {unpacked_cb.subcategory_id}")
        message_text = Localizator.get_text(BotEntity.USER, "buy_confirmation").format(
            category_name=category.name,
            subcategory_name=subcategory.name,
            price=item.price,
            description=item.description,
            quantity=unpacked_cb.quantity,
            total_price=item.price * unpacked_cb.quantity,
            currency_sym=Localizator.get_currency_symbol())
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=AllCategoriesCallback.create(
                              unpacked_cb.level + 1,
                              unpacked_cb.category_id,
                              unpacked_cb.subcategory_id,
                              quantity=unpacked_cb.quantity,
                              confirmation=True
                          ))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=AllCategoriesCallback.create(
                              1,
                              unpacked_cb.category_id
                          ))
        kb_builder.row(unpacked_cb.get_back_button())
        return message_text, kb_builder
