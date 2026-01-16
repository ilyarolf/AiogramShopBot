from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import BuysManagementCallback, MyProfileCallback
from enums.bot_entity import BotEntity
from enums.buy_status import BuyStatus
from enums.language import Language
from enums.user_role import UserRole
from handlers.admin.constants import BuysManagementStates
from repositories.buy import BuyRepository
from repositories.user import UserRepository
from services.notification import NotificationService
from utils.utils import get_text


class BuysManagementService:

    @staticmethod
    async def set_update_track_number_state(callback_data: BuysManagementCallback,
                                            state: FSMContext,
                                            language: Language) -> tuple[str, InlineKeyboardBuilder]:
        await state.set_state(BuysManagementStates.update_track_number)
        await state.update_data(buy_id=callback_data.buy_id)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=BuysManagementCallback.create(0)
        )
        return (get_text(language, BotEntity.ADMIN, "request_new_track_number")
                .format(buy_id=callback_data.buy_id), kb_builder)

    @staticmethod
    async def update_track_number_confirmation(message: Message,
                                               state: FSMContext,
                                               session: AsyncSession,
                                               language: Language):
        state_data = await state.get_data()
        await state.clear()
        state_data['track_number'] = message.html_text
        await state.update_data(**state_data)
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        buy = await BuyRepository.get_by_id(state_data['buy_id'], session)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "confirm"),
            callback_data=BuysManagementCallback.create(level=1,
                                                        buy_id=buy.id,
                                                        confirmation=True)
        )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=BuysManagementCallback.create(level=0)
        )
        kb_builder.adjust(1)
        return get_text(language, BotEntity.ADMIN, "update_track_number_confirmation").format(
            buy_id=buy.id,
            old_track_number=buy.track_number,
            new_track_number=message.text
        ), kb_builder

    @staticmethod
    async def update_track_number(session: AsyncSession,
                                  state: FSMContext,
                                  language: Language) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        buy = await BuyRepository.get_by_id(state_data['buy_id'], session)
        buy.track_number = state_data['track_number']
        buy.status = BuyStatus.COMPLETED
        await BuyRepository.update(buy, session)
        await session.commit()
        await state.clear()
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=MyProfileCallback.create(
                level=4,
                buy_id=buy.id,
                user_role=UserRole.ADMIN
            )
        )
        msg = (get_text(language, BotEntity.USER, "track_number_updated_notification")
               .format(buy_id=buy.id))
        user = await UserRepository.get_user_entity(buy.buyer_id, session)
        user_kb_builder = InlineKeyboardBuilder()
        user_kb_builder.button(
            text=get_text(language, BotEntity.USER, "purchase_history_item").format(
                buy_id=buy.id,
                total_price=buy.total_price,
                currency_sym=config.CURRENCY.get_localized_symbol()
            ),
            callback_data=MyProfileCallback.create(
                level=4,
                buy_id=buy.id
            )
        )
        await NotificationService.send_to_user(msg, user.telegram_id, user_kb_builder.as_markup())
        return get_text(language, BotEntity.ADMIN, "track_number_updated"), kb_builder
