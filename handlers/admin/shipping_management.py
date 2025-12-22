from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import ShippingManagementCallback
from enums.language import Language
from handlers.admin.constants import ShippingManagementStates
from services.shipping_management import ShippingManagementService
from utils.custom_filters import AdminIdFilter

shipping_management = Router()


async def shipping_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    msg, kb_builder = await ShippingManagementService.get_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def create_shipping_option(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await ShippingManagementService.create_shipping_option(callback, state, session, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def view_all_shipping_option(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await ShippingManagementService.view_all(callback, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def view_shipping_option_single(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await ShippingManagementService.view_single(callback, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def edit_shipping_option(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await ShippingManagementService.edit_property(callback, state, session, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@shipping_management.message(AdminIdFilter(), F.text, StateFilter(ShippingManagementStates.shipping_name,
                                                                  ShippingManagementStates.shipping_price))
async def receive_shipping_option_data(message: Message,
                                       state: FSMContext,
                                       language: Language):
    msg, kb_builder = await ShippingManagementService.receive_shipping_option_data(message, state, language)
    message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@shipping_management.message(AdminIdFilter(), F.text, StateFilter(ShippingManagementStates.edit_property))
async def receive_shipping_option_edit_value(message: Message,
                                             state: FSMContext,
                                             session: AsyncSession,
                                             language: Language):
    msg, kb_builder = await ShippingManagementService.edit_property_confirmation(message, state, session, language)
    message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@shipping_management.callback_query(AdminIdFilter(), ShippingManagementCallback.filter())
async def shipping_management_navigation(callback: CallbackQuery, state: FSMContext,
                                         callback_data: ShippingManagementCallback,
                                         session: AsyncSession,
                                         language: Language):
    current_level = callback_data.level
    levels = {
        0: shipping_management_menu,
        1: create_shipping_option,
        2: view_all_shipping_option,
        3: view_shipping_option_single,
        4: edit_shipping_option
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "session": session,
        "language": language
    }

    await current_level_function(**kwargs)
