from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from callbacks import CartCallback
from enums.bot_entity import BotEntity
from services.cart import CartService
from services.notification import NotificationService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

cart_router = Router()


@cart_router.message(F.text == Localizator.get_text(BotEntity.USER, "cart"), IsUserExistFilter())
async def cart_text_message(message: Message, session: AsyncSession):
    await show_cart(message=message, session=session)


async def show_cart(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    media, kb_builder = await CartService.create_buttons(message.from_user.id, callback_data, session)
    if isinstance(message, Message):
        await NotificationService.answer_media(message, media, kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def show_cart_item(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: CartCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await CartService.show_cart_item(callback_data, session)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def checkout_processing(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await CartService.checkout_processing(callback, session)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def buy_processing(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    await callback.message.edit_reply_markup()
    msg, kb_builder = await CartService.buy_processing(callback, session)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback, session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: show_cart_item,
        2: checkout_processing,
        3: buy_processing
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
        "callback_data": callback_data
    }

    await current_level_function(**kwargs)
