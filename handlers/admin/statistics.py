from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
import config
from callbacks import StatisticsCallback
from enums.language import Language
from services.statistics import StatisticsService
from utils.custom_filters import AdminIdFilter

statistics = Router()


async def statistics_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    msg, kb_builder = await StatisticsService.get_statistics_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def timedelta_picker(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: StatisticsCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    msg, kb_builder = await StatisticsService.get_timedelta_menu(callback_data, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def entity_statistics(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: StatisticsCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await StatisticsService.get_statistics(callback_data, session, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def get_db_file(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    await callback.answer()
    with open(f"./data/{config.DB_NAME}", "rb") as f:
        await callback.message.bot.send_document(callback.from_user.id,
                                                 types.BufferedInputFile(file=f.read(), filename="database.db"))


@statistics.callback_query(AdminIdFilter(), StatisticsCallback.filter())
async def statistics_navigation(callback: CallbackQuery, state: FSMContext, callback_data: StatisticsCallback,
                                session: AsyncSession, language: Language):
    current_level = callback_data.level

    levels = {
        0: statistics_menu,
        1: timedelta_picker,
        2: entity_statistics,
        3: get_db_file
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
