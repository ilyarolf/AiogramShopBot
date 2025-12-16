from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import InventoryManagementCallback, AddType
from enums.language import Language
from handlers.admin.constants import InventoryManagementStates
from handlers.common.common import enable_search
from services.admin import AdminService
from services.inventory_management import InventoryManagementService
from services.item import ItemService
from services.notification import NotificationService
from utils.custom_filters import AdminIdFilter

inventory_management = Router()


async def inventory_management_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    msg, kb_builder = await InventoryManagementService.get_inventory_management_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_items(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: InventoryManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    if callback_data.add_type is None:
        msg, kb_builder = await InventoryManagementService.get_add_items_type(callback_data, language)
    else:
        msg, kb_builder = await InventoryManagementService.get_add_item_msg(callback_data, state, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def delete_entity(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    callback_data: InventoryManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    state_data = await state.get_data()
    if callback_data.is_filter_enabled and state_data.get('filter') is not None:
        msg, kb_builder = await AdminService.get_entity_picker(callback_data, session, state, language)
    elif callback_data.is_filter_enabled:
        media, kb_builder = await enable_search(callback_data, callback_data.entity_type, None,
                                                state, InventoryManagementStates.filter_entity, language)
        await state.update_data(entity_type=callback_data.entity_type.value, callback_prefix=callback_data.__prefix__)
        msg = media.caption
    else:
        await state.update_data(filter=None)
        await state.set_state()
        msg, kb_builder = await AdminService.get_entity_picker(callback_data, session, state, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def confirm_delete(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: InventoryManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    if callback_data.confirmation is False:
        msg, kb_builder = await InventoryManagementService.delete_confirmation(callback_data, session, language)
    else:
        msg, kb_builder = await InventoryManagementService.delete_entity(callback_data, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@inventory_management.message(AdminIdFilter(), F.document, StateFilter(InventoryManagementStates.document))
async def add_items_document(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    state_data = await state.get_data()
    await NotificationService.edit_reply_markup(message.bot,
                                                state_data['chat_id'],
                                                state_data['msg_id'])
    add_type = AddType(int(state_data['add_type']))
    file_name = message.document.file_name
    file_id = message.document.file_id
    file = await message.bot.get_file(file_id)
    await message.bot.download_file(file.file_path, file_name)
    msg = await ItemService.add_items(file_name, add_type, session, language)
    await message.answer(text=msg)
    await state.clear()


@inventory_management.message(AdminIdFilter(), F.text, StateFilter(InventoryManagementStates.category,
                                                                   InventoryManagementStates.subcategory,
                                                                   InventoryManagementStates.price,
                                                                   InventoryManagementStates.description,
                                                                   InventoryManagementStates.private_data))
async def add_items_menu(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    msg, kb_builder = await InventoryManagementService.add_item_menu(message, state, session, language)
    message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@inventory_management.message(AdminIdFilter(), F.text, StateFilter(InventoryManagementStates.filter_entity))
async def receive_filter_message(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    await state.update_data(filter=message.html_text)
    msg, kb_builder = await AdminService.get_entity_picker(None, session, state, language)
    await message.answer(text=msg, reply_markup=kb_builder.as_markup())


@inventory_management.callback_query(AdminIdFilter(), InventoryManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery,
                                          state: FSMContext,
                                          callback_data: InventoryManagementCallback,
                                          session: AsyncSession,
                                          language: Language):
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
        "callback_data": callback_data,
        "language": language
    }

    await current_level_function(**kwargs)
