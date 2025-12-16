from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import UserManagementCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.language import Language
from enums.sort_property import SortProperty
from enums.user_management_operation import UserManagementOperation
from handlers.admin.constants import AdminConstants, UserManagementStates
from handlers.common.common import add_sorting_buttons, add_pagination_buttons, get_filters_settings, add_search_button
from repositories.buy import BuyRepository
from repositories.user import UserRepository
from services.notification import NotificationService
from utils.utils import get_text


class UserManagementService:
    @staticmethod
    async def get_user_management_menu(language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "find_user"),
                          callback_data=UserManagementCallback.create(1))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "make_refund"),
                          callback_data=UserManagementCallback.create(3))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button(language))
        return get_text(language, BotEntity.ADMIN, "user_management"), kb_builder

    @staticmethod
    async def find_user(callback_data: UserManagementCallback, state: FSMContext, session: AsyncSession,
                        language: Language):
        if callback_data.user_id:
            return await UserManagementService.get_user(callback_data, state, session, language)
        else:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                              callback_data=UserManagementCallback.create(0))
            await state.set_state(UserManagementStates.user_entity)
            return get_text(language, BotEntity.ADMIN, "credit_management_request_user_entity"), kb_builder

    @staticmethod
    async def request_balance_amount(message: Message,
                                     state: FSMContext,
                                     language: Language) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(level=1, user_id=state_data['user_id']))
        await state.update_data(user_entity=message.text)
        await state.set_state(UserManagementStates.balance_amount)
        operation = UserManagementOperation(int(state_data['operation']))
        match operation:
            case UserManagementOperation.ADD_BALANCE:
                return get_text(language, BotEntity.ADMIN, "credit_management_plus_operation").format(
                    currency_text=config.CURRENCY.get_localized_text()), kb_builder
            case UserManagementOperation.REDUCE_BALANCE:
                return get_text(language, BotEntity.ADMIN, "credit_management_minus_operation").format(
                    currency_text=config.CURRENCY.get_localized_text()), kb_builder

    @staticmethod
    async def balance_management(message: Message,
                                 state: FSMContext,
                                 session: AsyncSession,
                                 language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        state_data = await state.get_data()
        user_id = state_data['user_id']
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=UserManagementCallback.create(level=1, user_id=user_id)
        )
        try:
            await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
            user = await UserRepository.get_user_entity(user_id, session)
            operation = UserManagementOperation(int(state_data['operation']))
            amount = float(message.text)
            assert (amount > 0)
            if operation == UserManagementOperation.ADD_BALANCE:
                user.top_up_amount += float(message.text)
                await UserRepository.update(user, session)
                await session_commit(session)
                msg = get_text(language, BotEntity.ADMIN, "credit_management_added_success")
            else:
                user.consume_records += float(message.text)
                await UserRepository.update(user, session)
                await session_commit(session)
                msg = get_text(language, BotEntity.ADMIN, "credit_management_reduced_success")
            await state.clear()
            msg = msg.format(
                amount=message.text,
                telegram_id=user.telegram_id,
                currency_text=config.CURRENCY.get_localized_text())
            return msg, kb_builder
        except Exception as _:
            return await UserManagementService.request_balance_amount(message, state, language)

    @staticmethod
    async def get_refund_menu(callback_data: UserManagementCallback | None,
                              state: FSMContext,
                              session: AsyncSession,
                              language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        callback_data = callback_data or UserManagementCallback.create(3)
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        refund_data = await BuyRepository.get_refund_data(sort_pairs, filters, callback_data.page, session)
        for refund_item in refund_data:
            callback = UserManagementCallback.create(
                callback_data.level + 1,
                UserManagementOperation.REFUND,
                buy_id=refund_item.buy_id)
            if refund_item.telegram_username:
                kb_builder.button(text=get_text(language, BotEntity.ADMIN, "refund_by_username").format(
                    telegram_username=refund_item.telegram_username,
                    total_price=refund_item.total_price,
                    subcategory=refund_item.subcategory_name,
                    currency_sym=config.CURRENCY.get_localized_symbol()),
                    callback_data=callback)
            else:
                kb_builder.button(text=get_text(language, BotEntity.ADMIN, "refund_by_tgid").format(
                    telegram_id=refund_item.telegram_id,
                    total_price=refund_item.total_price,
                    subcategory=refund_item.subcategory_name,
                    currency_sym=config.CURRENCY.get_localized_symbol()),
                    callback_data=callback)
        kb_builder.adjust(1)
        kb_builder = await add_search_button(kb_builder, EntityType.USER, callback_data, filters, language)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.QUANTITY,
                                                            SortProperty.TOTAL_PRICE,
                                                            SortProperty.BUY_DATETIME],
                                               callback_data,
                                               sort_pairs, language)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  BuyRepository.get_max_refund_page(filters, session),
                                                  callback_data.get_back_button(language, 0), language)
        return get_text(language, BotEntity.ADMIN, "refund_menu"), kb_builder

    @staticmethod
    async def refund_confirmation(callback_data: UserManagementCallback,
                                  session: AsyncSession,
                                  language: Language):
        callback_data.confirmation = True
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "confirm"),
                          callback_data=callback_data)
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        refund_data = await BuyRepository.get_refund_data_single(callback_data.buy_id, session)
        if refund_data.telegram_username:
            return get_text(language, BotEntity.ADMIN, "refund_confirmation_by_username").format(
                telegram_username=refund_data.telegram_username,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                total_price=refund_data.total_price,
                currency_sym=config.CURRENCY.get_localized_symbol()), kb_builder
        else:
            return get_text(language, BotEntity.ADMIN, "refund_confirmation_by_tgid").format(
                telegram_id=refund_data.telegram_id,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                total_price=refund_data.total_price,
                currency_sym=config.CURRENCY.get_localized_symbol()), kb_builder

    @staticmethod
    async def get_user(message: Message | UserManagementCallback,
                       state: FSMContext,
                       session: AsyncSession,
                       language: Language) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        if isinstance(message, Message):
            await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
            user = await UserRepository.get_user_entity(message.html_text.replace("@", ""), session)
        else:
            user = await UserRepository.get_user_entity(message.user_id, session)
        kb_builder = InlineKeyboardBuilder()
        if user is None:
            msg = get_text(language, BotEntity.ADMIN, "credit_management_user_not_found")
        else:
            kb_builder.button(
                text=get_text(language, BotEntity.ADMIN, "credit_management_add_balance"),
                callback_data=UserManagementCallback.create(level=2,
                                                            operation=UserManagementOperation.ADD_BALANCE,
                                                            user_id=user.id)
            )
            kb_builder.button(
                text=get_text(language, BotEntity.ADMIN, "credit_management_reduce_balance"),
                callback_data=UserManagementCallback.create(level=2,
                                                            operation=UserManagementOperation.REDUCE_BALANCE,
                                                            user_id=user.id)
            )
            kb_builder.button(
                text=get_text(language, BotEntity.ADMIN, "ban"),
                callback_data=UserManagementCallback.create(level=2,
                                                            operation=UserManagementOperation.BAN,
                                                            user_id=user.id)
            )
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "user"),
                url=f"tg://user?id={user.telegram_id}"
            )
            total_purchases_qty = await BuyRepository.get_qty_by_buyer_id(user.id, session)
            total_spent_amount = await BuyRepository.get_spent_amount(user.id, session)
            msg = get_text(language, BotEntity.ADMIN, "user_info").format(
                username=f"@{user.telegram_username}" if user.telegram_username else "null",
                is_banned=user.is_banned,
                total_purchases_qty=total_purchases_qty,
                currency_sym=config.CURRENCY.get_localized_symbol(),
                total_spent_amount=total_spent_amount,
                balance=user.top_up_amount - user.consume_records,
                registered_at=user.registered_at.strftime("%m/%d/%Y, %I:%M %p")
            )
        await state.set_state()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=UserManagementCallback.create(0)
        )
        kb_builder.adjust(1)
        return msg, kb_builder

    @staticmethod
    async def user_operation(callback_data: UserManagementCallback,
                             state: FSMContext,
                             session: AsyncSession,
                             language: Language) -> tuple[str, InlineKeyboardBuilder]:
        if callback_data.operation == UserManagementOperation.BAN:
            user_dto = await UserRepository.get_user_entity(callback_data.user_id, session)
            user_dto.is_banned = not user_dto.is_banned
            await UserRepository.update(user_dto, session)
            await session_commit(session)
            return await UserManagementService.get_user(callback_data, state, session, language)
        else:
            await state.update_data(operation=callback_data.operation.value, user_id=callback_data.user_id)
            await state.set_state(UserManagementStates.balance_amount)
            if callback_data.operation == UserManagementOperation.ADD_BALANCE:
                msg = get_text(language, BotEntity.ADMIN, "credit_management_plus_operation")
            else:
                msg = get_text(language, BotEntity.ADMIN, "credit_management_minus_operation")
            msg = msg.format(
                currency_text=config.CURRENCY.get_localized_text()
            )
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "cancel"),
                callback_data=callback_data.model_copy(update={"level": callback_data.level-1, "operation": None})
            )
            return msg, kb_builder
