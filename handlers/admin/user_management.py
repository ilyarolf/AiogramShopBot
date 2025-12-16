from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import UserManagementCallback
from enums.entity_type import EntityType
from enums.language import Language
from handlers.admin.constants import UserManagementStates
from handlers.common.common import enable_search
from models.buy import BuyDTO
from services.buy import BuyService
from services.user_management import UserManagementService
from utils.custom_filters import AdminIdFilter

user_management = Router()


async def user_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    msg, kb_builder = await UserManagementService.get_user_management_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def find_user(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await UserManagementService.find_user(callback_data, state, session, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def user_operation(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await UserManagementService.user_operation(callback_data, state, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@user_management.message(AdminIdFilter(), F.text, StateFilter(UserManagementStates.user_entity))
async def receive_user_entity(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    msg, kb_builder = await UserManagementService.get_user(message, state, session, language)
    message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@user_management.message(AdminIdFilter(), F.text, StateFilter(UserManagementStates.balance_amount))
async def receive_balance_management_value(message: Message,
                                           state: FSMContext,
                                           session: AsyncSession,
                                           language: Language):
    msg, kb_builder = await UserManagementService.balance_management(message, state, session, language)
    message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def refund_buy(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    state_data = await state.get_data()
    if callback_data.is_filter_enabled and state_data.get('filter') is not None:
        msg, kb_builder = await UserManagementService.get_refund_menu(callback_data, state, session, language)
    elif callback_data.is_filter_enabled:
        media, kb_builder = await enable_search(callback_data, EntityType.USER, None, state,
                                                UserManagementStates.filter_username, language)
        msg = media.caption
    else:
        await state.update_data(filter=None)
        await state.set_state()
        msg, kb_builder = await UserManagementService.get_refund_menu(callback_data, state, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def refund_confirmation(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    if callback_data.confirmation:
        msg = await BuyService.refund(BuyDTO(id=callback_data.buy_id), session, language)
        await callback.message.edit_text(text=msg)
    else:
        msg, kb_builder = await UserManagementService.refund_confirmation(callback_data, session, language)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@user_management.message(AdminIdFilter(), F.text, StateFilter(UserManagementStates.filter_username))
async def receive_filter_message(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    await state.update_data(filter=message.html_text)
    msg, kb_builder = await UserManagementService.get_refund_menu(None, state, session, language)
    await message.answer(text=msg, reply_markup=kb_builder.as_markup())


@user_management.callback_query(AdminIdFilter(), UserManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery,
                                          state: FSMContext,
                                          callback_data: UserManagementCallback,
                                          session: AsyncSession,
                                          language: Language):
    current_level = callback_data.level

    levels = {
        0: user_management_menu,
        1: find_user,
        2: user_operation,
        3: refund_buy,
        4: refund_confirmation
    }
    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "session": session,
        "callback_data": callback_data,
        "language": language
    }

    await current_level_function(**kwargs)
