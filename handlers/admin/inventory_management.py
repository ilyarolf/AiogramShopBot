from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AdminInventoryManagementCallback, AddType
from enums.bot_entity import BotEntity
from handlers.admin.constants import AdminInventoryManagementStates
from services.admin import AdminService
from services.item import ItemService
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator

inventory_management = Router()


async def inventory_management_menu(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    await state.clear()
    msg, kb_builder = await AdminService.get_inventory_management_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_items(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
    if unpacked_cb.add_type is None:
        msg, kb_builder = await AdminService.get_add_items_type(callback)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    else:
        msg, kb_builder = await AdminService.get_add_item_msg(callback, state)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def delete_entity(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await AdminService.get_delete_entity_menu(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def confirm_delete(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
    if unpacked_cb.confirmation is False:
        msg, kb_builder = await AdminService.delete_confirmation(callback, session)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    else:
        msg, kb_builder = await AdminService.delete_entity(callback, session)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@inventory_management.message(AdminIdFilter(), F.document, StateFilter(AdminInventoryManagementStates.document))
async def add_items_document(message: Message, state: FSMContext, session: AsyncSession | Session):
    if message.text and message.text.lower() == 'cancel':
        await state.clear()
        await message.answer(Localizator.get_text(BotEntity.COMMON, "cancelled"))
    state_data = await state.get_data()
    add_type = AddType(int(state_data['add_type']))
    file_name = message.document.file_name
    file_id = message.document.file_id
    file = await message.bot.get_file(file_id)
    await message.bot.download_file(file.file_path, file_name)
    msg = await ItemService.add_items(file_name, add_type, session)
    await message.answer(text=msg)
    await state.clear()


@inventory_management.callback_query(AdminIdFilter(), AdminInventoryManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery, state: FSMContext,
                                          callback_data: AdminInventoryManagementCallback,
                                          session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: inventory_management_menu,
        1: add_items,
        2: delete_entity,
        3: confirm_delete
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "session": session,
    }

    await current_level_function(**kwargs)
