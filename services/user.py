from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from callbacks import MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.keyboardbutton import KeyboardButton
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons
from models.user import User, UserDTO
from repositories.button_media import ButtonMediaRepository
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.media import MediaService
from utils.localizator import Localizator


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
                                     session: AsyncSession) -> tuple[InputMediaPhoto |
                                                                     InputMediaVideo |
                                                                     InputMediaAnimation, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "top_up_balance_button"),
                          callback_data=MyProfileCallback.create(level=1))
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "purchase_history_button"),
                          callback_data=MyProfileCallback.create(level=4))
        user = await UserRepository.get_by_tgid(telegram_id, session)
        fiat_balance = round(user.top_up_amount - user.consume_records, 2)
        caption = (Localizator.get_text(BotEntity.USER, "my_profile_msg")
                   .format(telegram_id=user.telegram_id,
                           fiat_balance=fiat_balance,
                           currency_text=Localizator.get_currency_text(),
                           currency_sym=Localizator.get_currency_symbol()))
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.MY_PROFILE, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def get_top_up_buttons(callback_data: MyProfileCallback) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
                          callback_data=MyProfileCallback.create(level=callback_data.level + 1,
                                                                 cryptocurrency=Cryptocurrency.BTC))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
                          callback_data=MyProfileCallback.create(level=callback_data.level + 1,
                                                                 cryptocurrency=Cryptocurrency.LTC))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
                          callback_data=MyProfileCallback.create(level=callback_data.level + 1,
                                                                 cryptocurrency=Cryptocurrency.SOL))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "eth_top_up"),
                          callback_data=MyProfileCallback.create(level=callback_data.level + 1,
                                                                 cryptocurrency=Cryptocurrency.ETH))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "bnb_top_up"),
                          callback_data=MyProfileCallback.create(level=callback_data.level + 1,
                                                                 cryptocurrency=Cryptocurrency.BNB))

        kb_builder.adjust(1)
        kb_builder.row(callback_data.get_back_button())
        msg_text = Localizator.get_text(BotEntity.USER, "choose_top_up_method")
        return msg_text, kb_builder

    @staticmethod
    async def get_purchase_history_buttons(callback: CallbackQuery, callback_data: MyProfileCallback,
                                           state: FSMContext,
                                           session: AsyncSession) \
            -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        state_data = await state.get_data()
        sort_pairs = state_data.get("sort_pairs") or {}
        sort_pairs[str(callback_data.sort_property.value)] = callback_data.sort_order.value
        await state.update_data(sort_pairs=sort_pairs)
        buys = await BuyRepository.get_by_buyer_id(sort_pairs, user.id, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for buy in buys:
            buy_item = await BuyItemRepository.get_single_by_buy_id(buy.id, session)
            item = await ItemRepository.get_by_id(buy_item.item_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "purchase_history_item").format(
                subcategory_name=subcategory.name,
                total_price=buy.total_price,
                quantity=buy.quantity,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=MyProfileCallback.create(
                    level=callback_data.level + 1,
                    buy_id=buy.id
                ))
        kb_builder.adjust(1)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.TOTAL_PRICE,
                                                            SortProperty.QUANTITY,
                                                            SortProperty.BUY_DATETIME],
                                               callback_data, sort_pairs)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  BuyRepository.get_max_page_purchase_history(user.id, session),
                                                  callback_data.get_back_button(0))
        if len(kb_builder.as_markup().inline_keyboard) > 1:
            return Localizator.get_text(BotEntity.USER, "purchases"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "no_purchases"), kb_builder
