import inspect

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from callbacks import AdminInventoryManagementCallback
from services.admin import AdminService
from utils.custom_filters import AdminIdFilter

inventory_management = Router()


async def inventory_management_menu(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_inventory_management_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_items(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_add_items_type()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def delete_entity(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_delete_entity_menu(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def confirm_delete(callback: CallbackQuery):
    pass


@inventory_management.callback_query(AdminIdFilter(), AdminInventoryManagementCallback.filter())
async def inventory_management_navigation(callback: CallbackQuery, state: FSMContext,
                                          callback_data: AdminInventoryManagementCallback):
    current_level = callback_data.level

    levels = {
        0: inventory_management_menu,
        1: add_items,
        2: delete_entity,
        3: confirm_delete
    }
    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
