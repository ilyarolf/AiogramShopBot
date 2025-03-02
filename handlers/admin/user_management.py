from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import UserManagementCallback
from handlers.admin.constants import UserManagementStates
from models.buy import BuyDTO
from services.admin import AdminService
from services.buy import BuyService
from utils.custom_filters import AdminIdFilter

user_management = Router()


async def user_management_menu(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    await state.clear()
    msg, kb_builder = await AdminService.get_user_management_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def credit_management(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    unpacked_cb = UserManagementCallback.unpack(callback.data)
    if unpacked_cb.operation is None:
        msg, kb_builder = await AdminService.get_credit_management_menu(callback)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    else:
        msg, kb_builder = await AdminService.request_user_entity(callback, state)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@user_management.message(AdminIdFilter(), F.text, StateFilter(UserManagementStates.user_entity,
                                                              UserManagementStates.balance_amount))
async def balance_management(message: Message, state: FSMContext, session: AsyncSession | Session):
    current_state = await state.get_state()
    match current_state:
        case UserManagementStates.user_entity:
            msg, kb_builder = await AdminService.request_balance_amount(message, state)
            await message.answer(text=msg, reply_markup=kb_builder.as_markup())
        case UserManagementStates.balance_amount:
            msg = await AdminService.balance_management(message, state, session)
            await message.answer(text=msg)


async def refund_buy(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await AdminService.get_refund_menu(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def refund_confirmation(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    unpacked_cb = UserManagementCallback.unpack(callback.data)
    if unpacked_cb.confirmation:
        msg = await BuyService.refund(BuyDTO(id=unpacked_cb.buy_id), session)
        await callback.message.edit_text(text=msg)
    else:
        msg, kb_builder = await AdminService.refund_confirmation(callback, session)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@user_management.callback_query(AdminIdFilter(), UserManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery, state: FSMContext,
                                          callback_data: UserManagementCallback, session: Session | AsyncSession):
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
    }

    await current_level_function(**kwargs)
