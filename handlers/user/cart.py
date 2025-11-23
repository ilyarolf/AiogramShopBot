from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from callbacks import CartCallback
from enums.bot_entity import BotEntity
from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

cart_router = Router()


@cart_router.message(F.text == Localizator.get_text(BotEntity.USER, "cart"), IsUserExistFilter())
async def cart_text_message(message: Message, session: AsyncSession):
    await show_cart(message=message, session=session)


async def show_cart(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    media, kb_builder = await CartService.create_buttons(message, session)
    if isinstance(message, Message):
        if isinstance(media, InputMediaPhoto):
            await message.answer_photo(photo=media.media,
                                       caption=media.caption,
                                       reply_markup=kb_builder.as_markup())
        elif isinstance(media, InputMediaVideo):
            await message.answer_video(video=media.media,
                                       caption=media.caption,
                                       reply_markup=kb_builder.as_markup())
        else:
            await message.answer_animation(animation=media.media,
                                           caption=media.caption,
                                           reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def delete_cart_item(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await CartService.delete_cart_item(callback, session)
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
        1: delete_cart_item,
        2: checkout_processing,
        3: buy_processing
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
    }

    await current_level_function(**kwargs)
