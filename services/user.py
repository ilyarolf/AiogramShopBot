from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.entity_type import EntityType
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons, get_filters_settings, add_search_button
from models.user import User, UserDTO
from repositories.button_media import ButtonMediaRepository
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.media import MediaService
from utils.utils import get_text


class UserService:

    @staticmethod
    async def create_if_not_exist(user_dto: UserDTO, session: AsyncSession | Session) -> None:
        user = await UserRepository.get_by_tgid(user_dto.telegram_id, session)
        match user:
            case None:
                user_id = await UserRepository.create(user_dto, session)
                await CartRepository.get_or_create(user_id, session)
                await session_commit(session)
            case _:
                update_user_dto = UserDTO(**user.model_dump())
                update_user_dto.can_receive_messages = True
                update_user_dto.telegram_username = user_dto.telegram_username
                await UserRepository.update(update_user_dto, session)
                await session_commit(session)

    @staticmethod
    async def get(user_dto: UserDTO, session: AsyncSession | Session) -> User | None:
        return await UserRepository.get_by_tgid(user_dto.telegram_id, session)

    @staticmethod
    async def get_my_profile_buttons(telegram_id: int,
                                     session: AsyncSession,
                                     language: Language) -> tuple[InputMediaPhoto |
                                                                     InputMediaVideo |
                                                                     InputMediaAnimation, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.USER, "top_up_balance_button"),
                          callback_data=MyProfileCallback.create(level=1))
        kb_builder.button(text=get_text(language, BotEntity.USER, "purchase_history_button"),
                          callback_data=MyProfileCallback.create(level=4))
        user = await UserRepository.get_by_tgid(telegram_id, session)
        fiat_balance = round(user.top_up_amount - user.consume_records, 2)
        caption = (get_text(language, BotEntity.USER, "my_profile_msg")
                   .format(telegram_id=user.telegram_id,
                           fiat_balance=fiat_balance,
                           currency_text=config.CURRENCY.get_localized_text(),
                           currency_sym=config.CURRENCY.get_localized_symbol()))
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.MY_PROFILE, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def get_top_up_buttons(callback_data: MyProfileCallback,
                                 language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        for cryptocurrency in Cryptocurrency:
            kb_builder.button(
                text=cryptocurrency.get_localized(language),
                callback_data=MyProfileCallback.create(level=callback_data.level + 1,
                                                       cryptocurrency=cryptocurrency)
            )
        kb_builder.adjust(1)
        kb_builder.row(callback_data.get_back_button(language))
        msg_text = get_text(language, BotEntity.USER, "choose_top_up_method")
        return msg_text, kb_builder

    @staticmethod
    async def get_purchase_history_buttons(telegram_id: int,
                                           callback_data: MyProfileCallback | None,
                                           state: FSMContext,
                                           session: AsyncSession,
                                           language: Language) -> tuple[str, InlineKeyboardBuilder]:
        callback_data = callback_data or MyProfileCallback.create(level=4)
        user = await UserRepository.get_by_tgid(telegram_id, session)
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        buys = await BuyRepository.get_by_buyer_id(sort_pairs, filters, user.id, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for buy in buys:
            buy_item = await BuyItemRepository.get_single_by_buy_id(buy.id, session)
            item = await ItemRepository.get_by_id(buy_item.item_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            kb_builder.button(text=get_text(language, BotEntity.USER, "purchase_history_item").format(
                subcategory_name=subcategory.name,
                total_price=buy.total_price,
                quantity=buy.quantity,
                currency_sym=config.CURRENCY.get_localized_symbol()),
                callback_data=MyProfileCallback.create(
                    level=callback_data.level + 1,
                    buy_id=buy.id
                ))
        kb_builder.adjust(1)
        kb_builder = await add_search_button(kb_builder, EntityType.SUBCATEGORY, callback_data, filters, language)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.TOTAL_PRICE,
                                                            SortProperty.QUANTITY,
                                                            SortProperty.BUY_DATETIME],
                                               callback_data, sort_pairs, language)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  BuyRepository.get_max_page_purchase_history(user.id, filters,
                                                                                              session),
                                                  callback_data.get_back_button(language, 0), language)
        if len(kb_builder.as_markup().inline_keyboard) > 1:
            return get_text(language, BotEntity.USER, "purchases"), kb_builder
        else:
            return get_text(language, BotEntity.USER, "no_purchases"), kb_builder
