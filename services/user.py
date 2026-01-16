import datetime

from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import MyProfileCallback, AdminMenuCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from enums.sort_property import SortProperty
from enums.user_role import UserRole
from handlers.common.common import add_pagination_buttons, add_sorting_buttons, get_filters_settings
from models.user import User, UserDTO
from repositories.button_media import ButtonMediaRepository
from repositories.buy import BuyRepository
from repositories.cart import CartRepository
from repositories.user import UserRepository
from services.media import MediaService
from utils.utils import get_text


class UserService:

    @staticmethod
    async def create_if_not_exist(user_dto: UserDTO,
                                  referrer_code: str | None,
                                  session: AsyncSession | Session) -> None:
        user = await UserRepository.get_by_tgid(user_dto.telegram_id, session)
        match user:
            case None:
                referrer_user_dto = None
                if referrer_code:
                    referrer_user_dto = await UserRepository.get_by_referrer_code(referrer_code, session)
                if referrer_user_dto:
                    user_dto.referred_by_user_id = referrer_user_dto.id
                    user_dto.referred_at = datetime.datetime.now(tz=datetime.timezone.utc)
                user_id = await UserRepository.create(user_dto, session)
                await CartRepository.get_or_create(user_id, session)
                await session_commit(session)
            case _:
                update_user_dto = UserDTO(**user.model_dump())
                update_user_dto.can_receive_messages = True
                update_user_dto.telegram_username = user_dto.telegram_username
                update_user_dto.language = user_dto.language
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
                          callback_data=MyProfileCallback.create(level=3))
        kb_builder.button(text=get_text(Language.EN, BotEntity.USER, "referral_button"),
                          callback_data=MyProfileCallback.create(level=7))
        kb_builder.button(text=get_text(Language.EN, BotEntity.USER, "language"),
                          callback_data=MyProfileCallback.create(level=6))
        kb_builder.adjust(2)
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
    async def get_purchase_history_buttons(telegram_id: int | None,
                                           callback_data: MyProfileCallback | None,
                                           state: FSMContext,
                                           session: AsyncSession,
                                           language: Language) -> tuple[str, InlineKeyboardBuilder]:
        callback_data = callback_data or MyProfileCallback.create(level=3)
        user_id = None
        if callback_data.user_role == UserRole.ADMIN:
            back_button = AdminMenuCallback.create(0).get_back_button(language, 0)
        else:
            user = await UserRepository.get_by_tgid(telegram_id, session)
            user_id = user.id
            back_button = callback_data.get_back_button(language, 0)
        sort_pairs, _ = await get_filters_settings(state, callback_data)
        buys = await BuyRepository.get_by_buyer_id(sort_pairs, user_id, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for buy in buys:
            kb_builder.button(text=get_text(language, BotEntity.USER, "purchase_history_item").format(
                buy_id=buy.id,
                total_price=buy.total_price,
                currency_sym=config.CURRENCY.get_localized_symbol()),
                callback_data=MyProfileCallback.create(
                    level=callback_data.level + 1,
                    buy_id=buy.id,
                    user_role=callback_data.user_role
                ))
        kb_builder.adjust(1)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.TOTAL_PRICE,
                                                            SortProperty.BUY_DATETIME],
                                               callback_data, sort_pairs, language)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  BuyRepository.get_max_page_purchase_history(user_id, session),
                                                  back_button, language)
        if len(kb_builder.as_markup().inline_keyboard) > 1 and callback_data.user_role == UserRole.USER:
            caption = get_text(language, BotEntity.USER, "purchases")
        elif len(kb_builder.as_markup().inline_keyboard) > 1 and callback_data.user_role == UserRole.ADMIN:
            caption = get_text(language, BotEntity.ADMIN, "pick_purchase")
        else:
            caption = get_text(language, BotEntity.USER, "no_purchases")
        return caption, kb_builder

    @staticmethod
    async def edit_language(telegram_id: int,
                            callback_data: MyProfileCallback,
                            session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        default_language = Language.EN
        back_button = callback_data.get_back_button(default_language, 0)
        if callback_data.language is None:
            msg = get_text(default_language, BotEntity.USER, "edit_language")
            for language_object in Language:
                kb_builder.button(
                    text=f"{language_object.get_flag_emoji()} {language_object.name}",
                    callback_data=callback_data.model_copy(update={"language": language_object})
                )
            kb_builder.row(callback_data.get_back_button(default_language, 0))
        elif callback_data.language is not None and callback_data.confirmation is False:
            user_dto = await UserRepository.get_by_tgid(telegram_id, session)
            msg = get_text(default_language, BotEntity.USER, "edit_language_confirmation").format(
                current_language=user_dto.language.name,
                update_language=callback_data.language.name
            )
            kb_builder.button(
                text=get_text(default_language, BotEntity.COMMON, "confirm"),
                callback_data=callback_data.model_copy(update={"confirmation": True})
            )
            kb_builder.button(
                text=get_text(default_language, BotEntity.COMMON, "cancel"),
                callback_data=back_button.callback_data
            )
        else:
            user_dto = await UserRepository.get_by_tgid(telegram_id, session)
            user_dto.language = callback_data.language
            await UserRepository.update(user_dto, session)
            await session_commit(session)
            msg = get_text(default_language, BotEntity.USER, "language_edited_successfully")
            kb_builder.row(back_button)
        kb_builder.adjust(1)
        return msg, kb_builder
