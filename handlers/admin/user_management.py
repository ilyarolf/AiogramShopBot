from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import UserManagementCallback
from handlers.admin.constants import UserManagementStates
from models.buy import BuyDTO
from services.buy import BuyService
from services.user_management import UserManagementService
from utils.custom_filters import AdminIdFilter

user_management = Router()


async def user_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    await state.clear()
    msg, kb_builder = await UserManagementService.get_user_management_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def credit_management(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    if callback_data.operation is None:
        msg, kb_builder = await UserManagementService.get_credit_management_menu(callback_data)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    else:
        msg, kb_builder = await UserManagementService.request_user_entity(callback_data, state)
        message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
        await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@user_management.message(AdminIdFilter(), F.text, StateFilter(UserManagementStates.user_entity,
                                                              UserManagementStates.balance_amount))
async def balance_management(message: Message, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    match current_state:
        case UserManagementStates.user_entity:
            msg, kb_builder = await UserManagementCallback.request_balance_amount(message, state)
            message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
            await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
        case UserManagementStates.balance_amount:
            msg = await UserManagementCallback.balance_management(message, state, session)
            await message.answer(text=msg)


async def refund_buy(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await UserManagementService.get_refund_menu(callback_data, state, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def refund_confirmation(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: UserManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    if callback_data.confirmation:
        msg = await BuyService.refund(BuyDTO(id=callback_data.buy_id), session)
        await callback.message.edit_text(text=msg)
    else:
        msg, kb_builder = await UserManagementService.refund_confirmation(callback_data, session)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@user_management.callback_query(AdminIdFilter(), UserManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery, state: FSMContext,
                                          callback_data: UserManagementCallback, session: AsyncSession):
    current_level = callback_data.level

    levels = {
        0: user_management_menu,
        1: credit_management,
        2: refund_buy,
        3: refund_confirmation
    }
    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "session": session,
        "callback_data": callback_data
    }

    await current_level_function(**kwargs)
