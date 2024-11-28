import inspect

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
import config
from callbacks import StatisticsCallback
from services.admin import AdminService
from utils.custom_filters import AdminIdFilter

statistics = Router()


async def statistics_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    msg, kb_builder = await AdminService.get_statistics_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def timedelta_picker(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_timedelta_menu(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def entity_statistics(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_statistics(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def get_db_file(callback: CallbackQuery):
    await callback.answer()
    with open(f"./data/{config.DB_NAME}", "rb") as f:
        await callback.message.bot.send_document(callback.from_user.id,
                                                 types.BufferedInputFile(file=f.read(), filename="database.db"))


@statistics.callback_query(AdminIdFilter(), StatisticsCallback.filter())
async def statistics_navigation(callback: CallbackQuery, state: FSMContext, callback_data: StatisticsCallback):
    current_level = callback_data.level

    levels = {
        0: statistics_menu,
        1: timedelta_picker,
        2: entity_statistics,
        3: get_db_file
    }
    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
