from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import MediaManagementCallback
from handlers.admin.constants import MediaManagementStates
from services.admin import AdminService
from services.media import MediaService
from utils.custom_filters import AdminIdFilter

media_management = Router()


async def media_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    callback_data: MediaManagementCallback = kwargs.get("callback_data")
    await state.clear()
    msg, kb_builder = await MediaService.get_menu(callback_data)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def get_entity_picker(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MediaManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await AdminService.get_entity_picker(callback_data, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def entity_media_edit(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    callback_data = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await MediaService.set_entity_media_edit(callback_data, state, session)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@media_management.message(AdminIdFilter(), F.photo | F.video | F.animation, StateFilter(MediaManagementStates.media))
async def receive_new_entity_media(message: Message, state: FSMContext, session: AsyncSession):
    msg, kb_builder = await MediaService.receive_new_entity_media(message, state, session)
    await message.answer(text=msg, reply_markup=kb_builder.as_markup())


@media_management.callback_query(AdminIdFilter(), MediaManagementCallback.filter())
async def media_management_navigation(callback: CallbackQuery, state: FSMContext,
                                      callback_data: MediaManagementCallback, session: AsyncSession):
    current_level = callback_data.level

    levels = {
        0: media_management_menu,
        1: get_entity_picker,
        2: entity_media_edit,

    }
    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "session": session,
        "callback_data": callback_data
    }
    await current_level_function(**kwargs)
