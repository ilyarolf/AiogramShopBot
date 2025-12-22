from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import BuysManagementCallback
from enums.language import Language
from handlers.admin.constants import BuysManagementStates
from services.buys_management import BuysManagementService
from utils.custom_filters import AdminIdFilter

buys_management_router = Router()


async def set_track_number(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: BuysManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    if callback_data.confirmation:
        msg, kb_builder = await BuysManagementService.update_track_number(session, state, language)
    else:
        msg, kb_builder = await BuysManagementService.set_update_track_number_state(callback_data, state, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(chat_id=message.chat.id, msg_id=message.message_id)


@buys_management_router.message(AdminIdFilter(), F.text, StateFilter(BuysManagementStates.update_track_number))
async def receive_track_number(message: Message,
                               state: FSMContext,
                               session: AsyncSession,
                               language: Language):
    msg, kb_builder = await BuysManagementService.update_track_number_confirmation(message, state, session, language)
    await message.answer(text=msg, reply_markup=kb_builder.as_markup())


@buys_management_router.callback_query(AdminIdFilter(), BuysManagementCallback.filter())
async def announcement_navigation(callback: CallbackQuery,
                                  state: FSMContext,
                                  callback_data: BuysManagementCallback,
                                  session: AsyncSession,
                                  language: Language):
    current_level = callback_data.level

    levels = {
        1: set_track_number
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
