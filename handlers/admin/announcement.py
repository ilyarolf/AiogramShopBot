from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import AnnouncementCallback, AnnouncementType
from enums.bot_entity import BotEntity
from enums.language import Language
from handlers.admin.constants import AnnouncementStates, AnnouncementsConstants
from services.announcement import AnnouncementService
from services.item import ItemService
from utils.custom_filters import AdminIdFilter
from utils.utils import get_text

announcement_router = Router()


async def announcement_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    language: Language = kwargs.get("language")
    msg, kb_builder = await AnnouncementService.get_announcement_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def send_everyone(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await callback.message.edit_text(get_text(language, BotEntity.ADMIN, "receive_msg_request"))
    await state.set_state(AnnouncementStates.announcement_msg)


@announcement_router.message(AdminIdFilter(), StateFilter(AnnouncementStates.announcement_msg))
async def receive_admin_message(message: Message, state: FSMContext, language: Language):
    await state.clear()
    if message.text and message.text.lower() == "cancel":
        await message.answer(text=get_text(language, BotEntity.ADMIN, "cancelled"))
    else:
        kb_builder = AnnouncementsConstants.get_confirmation_builder(AnnouncementType.FROM_RECEIVING_MESSAGE,
                                                                     language)
        await message.copy_to(
            chat_id=message.chat.id,
            reply_markup=kb_builder.as_markup())


async def send_generated_msg(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    callback_data: AnnouncementCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    kb_builder = AnnouncementsConstants.get_confirmation_builder(callback_data.announcement_type,
                                                                 language)
    msg = await ItemService.create_announcement_message(callback_data.announcement_type, session, language)
    await callback.message.answer(text=msg, reply_markup=kb_builder.as_markup())


async def send_confirmation(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: AnnouncementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg = await AnnouncementService.send_announcement(callback, callback_data, session, language)
    if callback.message.caption:
        await callback.message.delete()
        await callback.message.answer(text=msg)
    elif callback.message.text:
        await callback.message.edit_text(text=msg)


@announcement_router.callback_query(AdminIdFilter(), AnnouncementCallback.filter())
async def announcement_navigation(callback: CallbackQuery,
                                  state: FSMContext,
                                  callback_data: AnnouncementCallback,
                                  session: AsyncSession,
                                  language: Language):
    current_level = callback_data.level

    levels = {
        0: announcement_menu,
        1: send_everyone,
        2: send_generated_msg,
        3: send_confirmation
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
