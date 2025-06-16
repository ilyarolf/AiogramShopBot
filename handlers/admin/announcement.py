from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AdminAnnouncementCallback, AnnouncementType
from enums.bot_entity import BotEntity
from handlers.admin.constants import AdminAnnouncementStates, AdminAnnouncementsConstants
from services.admin import AdminService
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator
from utils.new_items_manager import NewItemsManager

announcement_router = Router()


async def announcement_menu(**kwargs):
    callback = kwargs.get("callback")
    msg, kb_builder = await AdminService.get_announcement_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def send_everyone(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "receive_msg_request"))
    await state.set_state(AdminAnnouncementStates.announcement_msg)


@announcement_router.message(AdminIdFilter(), StateFilter(AdminAnnouncementStates.announcement_msg))
async def receive_admin_message(message: Message, state: FSMContext):
    await state.clear()
    if message.text and message.text.lower() == "cancel":
        await message.answer(text=Localizator.get_text(BotEntity.COMMON, "cancelled"))
    else:
        await message.copy_to(message.chat.id,
                              reply_markup=AdminAnnouncementsConstants.get_confirmation_builder(
                                  AnnouncementType.FROM_RECEIVING_MESSAGE).as_markup())


async def send_generated_msg(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    unpacked_cb = AdminAnnouncementCallback.unpack(callback.data)
    kb_builder = AdminAnnouncementsConstants.get_confirmation_builder(unpacked_cb.announcement_type)
    if unpacked_cb.announcement_type == AnnouncementType.RESTOCKING:
        msg = await NewItemsManager.generate_restocking_message(session)
        await callback.message.answer(msg, reply_markup=kb_builder.as_markup())
    else:
        msg = await NewItemsManager.generate_in_stock_message(session)
        await callback.message.answer(msg, reply_markup=kb_builder.as_markup())


async def send_confirmation(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg = await AdminService.send_announcement(callback, session)
    if callback.message.caption:
        await callback.message.delete()
        await callback.message.answer(text=msg)
    elif callback.message.text:
        await callback.message.edit_text(text=msg)


@announcement_router.callback_query(AdminIdFilter(), AdminAnnouncementCallback.filter())
async def announcement_navigation(callback: CallbackQuery, state: FSMContext, callback_data: AdminAnnouncementCallback,
                                  session: AsyncSession | Session):
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
    }

    await current_level_function(**kwargs)
