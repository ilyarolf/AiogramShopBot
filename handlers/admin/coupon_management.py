from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import CouponManagementCallback
from enums.language import Language
from handlers.admin.constants import CouponsManagementStates
from services.coupon_management import CouponManagementService
from utils.custom_filters import AdminIdFilter

coupons_management = Router()


async def coupon_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    msg, kb_builder = await CouponManagementService.get_coupon_management_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def pick_new_coupon_type(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CouponManagementCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CouponManagementService.coupon_creation_get_type_of_coupon_picker(callback_data, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def pick_new_coupon_usage_number(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CouponManagementCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CouponManagementService.coupon_creation_get_number_of_uses_picker(callback_data, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def request_coupon_value(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CouponManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CouponManagementService.request_coupon_value(callback_data, state, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@coupons_management.message(AdminIdFilter(), F.text, StateFilter(CouponsManagementStates.coupon_value))
async def receive_coupon_value(message: Message, state: FSMContext, language: Language):
    msg, kb_builder = await CouponManagementService.receive_coupon_value(message, state, language)
    message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def create_coupon(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CouponManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CouponManagementService.create_coupon(callback_data, state, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def view_coupons(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CouponManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CouponManagementService.view_coupons(callback_data, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def view_coupon(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CouponManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CouponManagementService.view_coupon(callback_data, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@coupons_management.callback_query(AdminIdFilter(), CouponManagementCallback.filter())
async def coupon_management_navigation(callback: CallbackQuery,
                                       state: FSMContext,
                                       callback_data: CouponManagementCallback,
                                       session: AsyncSession,
                                       language: Language):
    current_level = callback_data.level

    levels = {
        0: coupon_management_menu,
        1: pick_new_coupon_type,
        2: pick_new_coupon_usage_number,
        3: request_coupon_value,
        4: create_coupon,
        5: view_coupons,
        6: view_coupon
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "callback_data": callback_data,
        "state": state,
        "session": session,
        "language": language
    }

    await current_level_function(**kwargs)
