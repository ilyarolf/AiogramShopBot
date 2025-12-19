from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from handlers.common.common import add_pagination_buttons
from models.user import User, UserDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.user import UserRepository
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
    async def get_my_profile_buttons(telegram_id: int, session: Session | AsyncSession) -> tuple[
        str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "top_up_balance_button"),
                          callback_data=MyProfileCallback.create(1, "top_up"))
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "purchase_history_button"),
                          callback_data=MyProfileCallback.create(4, "purchase_history"))
        user = await UserRepository.get_by_tgid(telegram_id, session)
        fiat_balance = round(user.top_up_amount - user.consume_records, 2)
        message = (Localizator.get_text(BotEntity.USER, "my_profile_msg")
                   .format(telegram_id=user.telegram_id,
                           fiat_balance=fiat_balance,
                           currency_text=Localizator.get_currency_text(),
                           currency_sym=Localizator.get_currency_symbol()))
        return message, kb_builder

    @staticmethod
    async def get_top_up_buttons(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.BTC.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.LTC.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.SOL.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "eth_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.ETH.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "bnb_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.BNB.value))

        kb_builder.adjust(1)
        kb_builder.row(unpacked_cb.get_back_button())
        msg_text = Localizator.get_text(BotEntity.USER, "choose_top_up_method")
        return msg_text, kb_builder

    @staticmethod
    async def get_purchase_history_buttons(callback: CallbackQuery, session: AsyncSession | Session) \
            -> tuple[str, InlineKeyboardBuilder]:
        """Get purchase history buttons using product category info."""
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        buys = await BuyRepository.get_by_buyer_id(user.id, unpacked_cb.page, session)
        kb_builder = InlineKeyboardBuilder()

        for buy in buys:
            buy_item = await BuyItemRepository.get_single_by_buy_id(buy.id, session)
            item = await ItemRepository.get_by_id(buy_item.item_id, session)
            # Get product category instead of subcategory
            product = await CategoryRepository.get_by_id(item.category_id, session)

            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "purchase_history_item").format(
                    product_name=product.name if product else "Unknown",
                    total_price=buy.total_price,
                    quantity=buy.quantity,
                    currency_sym=Localizator.get_currency_symbol()
                ),
                callback_data=MyProfileCallback.create(
                    unpacked_cb.level + 1,
                    args_for_action=buy.id
                )
            )

        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                  BuyRepository.get_max_page_purchase_history(user.id, session),
                                                  unpacked_cb.get_back_button(0))
        if len(kb_builder.as_markup().inline_keyboard) > 1:
            return Localizator.get_text(BotEntity.USER, "purchases"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "no_purchases"), kb_builder
