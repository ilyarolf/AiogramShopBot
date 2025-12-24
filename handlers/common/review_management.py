from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import ReviewManagementCallback
from enums.language import Language
from handlers.user.constants import UserStates
from services.review import ReviewService
from utils.custom_filters import IsUserExistFilter

review_management_router = Router()


async def pick_rating_for_review(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: ReviewManagementCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    msg, kb_builder = await ReviewService.get_rating_picker(callback_data, language)
    await callback.message.delete()
    await callback.message.answer(text=msg, reply_markup=kb_builder.as_markup())


async def set_review_details_state(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: ReviewManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    next_state = UserStates.review_text if callback_data.level == 2 else UserStates.review_image
    msg, kb_builder = await ReviewService.set_review_next_state(callback_data, state, next_state, language)
    message = await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def create_review(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: ReviewManagementCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    if callback_data.confirmation:
        media, kb_builder = await ReviewService.create_review(callback_data, state, session, language)
    else:
        media, kb_builder = await ReviewService.review_confirmation(callback_data, state, session, language)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def view_reviews_paginated(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: ReviewManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    media, kb_builder = await ReviewService.get_reviews_paginated(callback_data, session, language)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def view_review_single(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: ReviewManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    media, kb_builder = await ReviewService.view_review_single(callback_data, session, language)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def remove_review_details(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: ReviewManagementCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    if callback_data.confirmation:
        media, kb_builder = await ReviewService.remove_review_details(callback, callback_data, session, language)
    else:
        media, kb_builder = await ReviewService.remove_review_details_confirmation(callback_data, session, language)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


@review_management_router.message(F.text | F.photo, StateFilter(UserStates.review_text,
                                                                UserStates.review_image),
                                  IsUserExistFilter())
async def receive_review_message(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    msg, kb_builder = await ReviewService.process_review_message(message, state, session, language)
    if isinstance(msg, InputMediaPhoto):
        message = await message.answer_photo(photo=msg.media, caption=msg.caption, reply_markup=kb_builder.as_markup())
    else:
        message = await message.answer(text=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@review_management_router.callback_query(IsUserExistFilter(), ReviewManagementCallback.filter())
async def review_management_navigation(callback: CallbackQuery,
                                       state: FSMContext,
                                       callback_data: ReviewManagementCallback,
                                       session: AsyncSession,
                                       language: Language):
    current_level = callback_data.level

    levels = {
        1: pick_rating_for_review,
        2: set_review_details_state,
        3: set_review_details_state,
        4: create_review,
        5: view_reviews_paginated,
        6: view_review_single,
        7: remove_review_details,
        8: remove_review_details
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
