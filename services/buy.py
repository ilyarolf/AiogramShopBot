from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InputMediaDocument, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.language import Language
from enums.sort_property import SortProperty
from handlers.common.common import get_filters_settings, add_sorting_buttons, add_pagination_buttons, add_search_button
from models.buy import BuyDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from utils.utils import get_text, get_bot_photo_id, remove_html_tags


class BuyService:

    @staticmethod
    async def refund(buy_dto: BuyDTO, session: AsyncSession | Session, language: Language) -> str:
        refund_data = await BuyRepository.get_refund_data_single(buy_dto.id, session)
        buy = await BuyRepository.get_by_id(buy_dto.id, session)
        buy.is_refunded = True
        await BuyRepository.update(buy, session)
        user = await UserRepository.get_by_tgid(refund_data.telegram_id, session)
        user.consume_records = user.consume_records - refund_data.total_price
        await UserRepository.update(user, session)
        await session_commit(session)
        await NotificationService.refund(refund_data)
        if refund_data.telegram_username:
            msg = get_text(language, BotEntity.ADMIN, "successfully_refunded_with_username")
        else:
            msg = get_text(language, BotEntity.ADMIN, "successfully_refunded_with_tgid")
        return msg.format(
            total_price=refund_data.total_price,
            telegram_id=refund_data.telegram_id,
            telegram_username=refund_data.telegram_username,
            quantity=len(refund_data.item_ids),
            subcategory=refund_data.subcategory_name,
            currency_sym=config.CURRENCY.get_localized_symbol())

    @staticmethod
    async def get_purchase(callback_data: MyProfileCallback,
                           session: AsyncSession,
                           language: Language) -> tuple[str | InputMediaDocument, InlineKeyboardBuilder]:
        buy = await BuyRepository.get_by_id(callback_data.buy_id, session)
        buyItem_dto = await BuyItemRepository.get_by_id(callback_data.buyItem_id, session)
        items = await ItemRepository.get_by_id_list(buyItem_dto.item_ids, session)
        purchased_items_msg = MessageService.create_message_with_bought_items(items, language)
        category = await CategoryRepository.get_by_id(items[0].category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(items[0].subcategory_id, session)
        us_datetime_12h = buy.buy_datetime.strftime("%m/%d/%Y, %I:%M %p")
        msg_template = get_text(language, BotEntity.USER, "purchase_details")
        msg = msg_template.format(
            category_name=category.name,
            subcategory_name=subcategory.name,
            currency_sym=config.CURRENCY.get_localized_symbol(),
            total_fiat_price=items[0].price * len(items),
            fiat_price=items[0].price,
            qty=len(items),
            purchase_datetime=us_datetime_12h,
            purchased_items=purchased_items_msg*100
        )
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(callback_data.get_back_button(language))
        if len(msg) > 1024:
            msg = msg_template.format(
                category_name=category.name,
                subcategory_name=subcategory.name,
                currency_sym=config.CURRENCY.get_localized_symbol(),
                total_fiat_price=items[0].price * len(items),
                fiat_price=items[0].price,
                qty=len(items),
                purchase_datetime=us_datetime_12h,
                purchased_items=get_text(language, BotEntity.USER, "attached")
            )
            purchased_items_msg=remove_html_tags(purchased_items_msg)
            byte_array = bytearray(purchased_items_msg, 'utf-8')
            media = InputMediaDocument(media=BufferedInputFile(byte_array, f"Purchase#{buy.id}.txt"),
                                       caption=msg)
            return media, kb_builder
        else:
            return msg, kb_builder

    @staticmethod
    async def get_purchased_item(callback_data: MyProfileCallback | None,
                                 state: FSMContext,
                                 session: AsyncSession,
                                 language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        callback_data = callback_data or MyProfileCallback.create(4, state_data.get("entity_id"))
        buy_dto = await BuyRepository.get_by_id(callback_data.buy_id, session)
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        buyItem_list = await BuyItemRepository.get_paginated_by_buy_id(sort_pairs,
                                                                       filters,
                                                                       buy_dto.id,
                                                                       callback_data.page,
                                                                       session)
        kb_builder = InlineKeyboardBuilder()
        for buyItem in buyItem_list:
            item_dto = await ItemRepository.get_by_id(buyItem.item_ids[0], session)
            subcategory_dto = await SubcategoryRepository.get_by_id(item_dto.subcategory_id, session)
            kb_builder.button(
                text=get_text(language, BotEntity.USER, "purchase_history_single_button").format(
                    subcategory_name=subcategory_dto.name,
                    qty=len(buyItem.item_ids)
                ),
                callback_data=callback_data.model_copy(update={"level": callback_data.level + 1,
                                                               "buyItem_id": buyItem.id})
            )
        kb_builder.adjust(1)
        kb_builder = await add_search_button(kb_builder, EntityType.SUBCATEGORY, callback_data, filters, language)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.NAME,
                                                            SortProperty.QUANTITY],
                                               callback_data, sort_pairs, language)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  BuyItemRepository.get_max_page_by_buy_id(callback_data.buy_id,
                                                                                           filters,
                                                                                           session),
                                                  callback_data.get_back_button(language), language)
        caption = get_text(language, BotEntity.USER, "purchase_history_pick_item")
        bot_photo_id = get_bot_photo_id()
        media = InputMediaPhoto(media=bot_photo_id, caption=caption)
        return media, kb_builder
