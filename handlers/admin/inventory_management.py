from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import InventoryManagementCallback, AddType
from enums.bot_entity import BotEntity
from handlers.admin.constants import AdminInventoryManagementStates
from services.admin import AdminService
from services.inventory_management import InventoryManagementService
from services.item import ItemService
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator

inventory_management = Router()


async def inventory_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    await state.clear()
    msg, kb_builder = await InventoryManagementService.get_inventory_management_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_items(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: InventoryManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    if callback_data.add_type is None:
        msg, kb_builder = await InventoryManagementService.get_add_items_type(callback_data)
    else:
        msg, kb_builder = await InventoryManagementService.get_add_item_msg(callback_data, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def delete_entity(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    callback_data = kwargs.get("callback_data")
    msg, kb_builder = await AdminService.get_entity_picker(callback_data, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def confirm_delete(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: InventoryManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    if callback_data.confirmation is False:
        msg, kb_builder = await InventoryManagementService.delete_confirmation(callback_data, session)
    else:
        msg, kb_builder = await InventoryManagementService.delete_entity(callback_data, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@inventory_management.message(AdminIdFilter(), F.document, StateFilter(AdminInventoryManagementStates.document))
async def add_items_document(message: Message, state: FSMContext, session: AsyncSession):
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


@inventory_management.callback_query(AdminIdFilter(), InventoryManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery, state: FSMContext,
                                          callback_data: InventoryManagementCallback,
                                          session: AsyncSession):
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
        "callback_data": callback_data
    }

    await current_level_function(**kwargs)
