from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from callbacks import CartCallback
from enums.keyboard_button import KeyboardButton as KB
from enums.language import Language
from handlers.user.constants import UserStates
from services.cart import CartService
from services.notification import NotificationService
from utils.custom_filters import IsUserExistFilter

cart_router = Router()


@cart_router.message(F.text.in_(KB.get_localized_set(KB.CART)), IsUserExistFilter())
async def cart_text_message(message: Message, session: AsyncSession, state: FSMContext, language: Language):
    await show_cart(message=message, session=session, state=state, language=language)


async def show_cart(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    media, kb_builder = await CartService.create_buttons(message.from_user.id, callback_data, session, language)
    if isinstance(message, Message):
        await NotificationService.answer_media(message, media, kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def show_cart_item(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CartService.show_cart_item(callback_data, session, language)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def checkout_processing(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CartService.checkout_processing(callback, callback_data, state, session, language)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def buy_processing(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await callback.message.edit_reply_markup()
    msg, kb_builder = await CartService.buy_processing(callback, callback_data, state, session, language)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def set_coupon(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CartService.set_coupon(callback_data, state, language)
    message = await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def set_shipping_address(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await CartService.set_shipping_address(state, language)
    message = await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


async def pick_shipping_option(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await CartService.get_shipping_options_paginated(callback_data.page, session, language)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


@cart_router.message(F.text, IsUserExistFilter(), StateFilter(UserStates.coupon,
                                                              UserStates.shipping_address))
async def receive_purchase_details(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    media, kb_builder = await CartService.receive_purchase_details(message, state, session, language)
    message = await NotificationService.answer_media(message, media, kb_builder.as_markup())
    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)


@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery,
                                callback_data: CartCallback,
                                session: AsyncSession | Session,
                                state: FSMContext,
                                language: Language):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: show_cart_item,
        2: checkout_processing,
        3: set_coupon,
        4: set_shipping_address,
        5: pick_shipping_option,
        6: buy_processing
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
        "callback_data": callback_data,
        "state": state,
        "language": language
    }

    await current_level_function(**kwargs)
