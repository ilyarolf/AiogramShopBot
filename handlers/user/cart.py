import inspect

from aiogram import types, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import CartCallback
from enums.bot_entity import BotEntity
from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

cart_router = Router()


@cart_router.message(F.text == Localizator.get_text(BotEntity.USER, "cart"), IsUserExistFilter())
async def cart_text_message(message: types.message, session: AsyncSession | Session):
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


async def delete_cart_item(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await CartService.delete_cart_item(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def checkout_processing(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await CartService.checkout_processing(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def buy_processing(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    await callback.message.edit_reply_markup()
    msg, kb_builder = await CartService.buy_processing(callback, session)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


# ========================================
# NEUE INVOICE-BASED CHECKOUT HANDLER
# ========================================

async def crypto_selection_for_checkout(**kwargs):
    """Level 3: Zeigt Crypto-Auswahl nach Checkout-Confirmation (Invoice-Flow)"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await CartService.get_crypto_selection_for_checkout(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def create_order_with_crypto(**kwargs):
    """Level 4: Erstellt Order + Invoice mit gewählter Crypto"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    await callback.message.edit_reply_markup()  # Entferne Buttons während Processing
    msg, kb_builder = await CartService.create_order_with_selected_crypto(callback, session)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback, session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: delete_cart_item,
        2: checkout_processing,
        3: crypto_selection_for_checkout,      # INVOICE-FLOW: Crypto-Auswahl
        4: create_order_with_crypto,           # INVOICE-FLOW: Order-Erstellung
        # 3: buy_processing  # OLD WALLET-FLOW (auskommentiert für Migration)
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
    }

    await current_level_function(**kwargs)
