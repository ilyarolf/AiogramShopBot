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
    if callback.message.caption:
        await callback.message.delete()
        await callback.message.answer(text=msg, reply_markup=kb_builder.as_markup())
    else:
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def entity_statistics(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: StatisticsCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    state: FSMContext = kwargs.get("state")
    media, kb_builder = await StatisticsService.get_statistics(callback_data, session, state, language)
    await callback.message.delete()
    await callback.message.answer_photo(photo=media.media, caption=media.caption, reply_markup=kb_builder.as_markup())


@statistics.callback_query(AdminIdFilter(), StatisticsCallback.filter())
async def statistics_navigation(callback: CallbackQuery, state: FSMContext, callback_data: StatisticsCallback,
                                session: AsyncSession, language: Language):
    current_level = callback_data.level

    levels = {
        0: statistics_menu,
        1: timedelta_picker,
        2: entity_statistics,
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
