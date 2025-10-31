import inspect

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import CartCallback, OrderCallback
from enums.bot_entity import BotEntity
from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

cart_router = Router()


@cart_router.message(F.text == Localizator.get_text(BotEntity.USER, "cart"), IsUserExistFilter())
async def cart_text_message(message: types.Message, session: AsyncSession | Session):
    import logging
    logging.info("🛒 CART BUTTON HANDLER TRIGGERED")
    await show_cart(message=message, session=session)


async def show_cart(**kwargs):
    message = kwargs.get("message") or kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await CartService.create_buttons(message, session)
    if isinstance(message, Message):
        await message.answer(msg, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def delete_cart_item_confirm(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await CartService.delete_cart_item_confirm(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def delete_cart_item_execute(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await CartService.delete_cart_item_execute(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def checkout_processing(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")
    msg, kb_builder = await CartService.checkout_processing(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def buy_processing(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    await callback.message.edit_reply_markup()
    msg, kb_builder = await CartService.buy_processing(callback, session)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


# ========================================
# NEW INVOICE-BASED CHECKOUT HANDLERS
# ========================================

async def create_order_handler(**kwargs):
    """
    Level 3: Checkout → Hand off to Order Domain

    Redirects to OrderCallback Level 0 (Order Creation).
    Order domain handles:
    - Stock reservation
    - Stock adjustment confirmation
    - Address collection (physical items)
    - Payment processing
    """
    callback = kwargs.get("callback")

    # Hand off to Order domain
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from services.order import OrderService

    # Directly call order creation
    msg, kb_builder = await OrderService.create_order(callback, kwargs.get("session"), kwargs.get("state"))
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())




@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback, session: AsyncSession | Session, state: FSMContext):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: delete_cart_item_confirm,
        2: checkout_processing,
        3: create_order_handler,  # Hand off to Order domain
        4: delete_cart_item_execute,
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
        "state": state,
    }

    await current_level_function(**kwargs)
