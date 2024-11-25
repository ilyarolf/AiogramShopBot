from aiogram import types, F, Router
from aiogram.types import CallbackQuery, Message

from callbacks import CartCallback
from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator, BotEntity

cart_router = Router()


@cart_router.message(F.text == Localizator.get_text(BotEntity.USER, "cart"), IsUserExistFilter())
async def cart_text_message(message: types.message):
    await show_cart(message)


async def show_cart(message: Message | CallbackQuery):
    msg, kb_builder = await CartService.create_buttons(message)
    if isinstance(message, Message):
        await message.answer(msg, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def delete_cart_item(callback: CallbackQuery):
    msg, kb_builder = await CartService.delete_cart_item(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def checkout_processing(callback: CallbackQuery):
    msg, kb_builder = await CartService.checkout_processing(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def buy_processing(callback: CallbackQuery):
    await callback.message.edit_reply_markup()
    msg, kb_builder = await CartService.buy_processing(callback)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: delete_cart_item,
        2: checkout_processing,
        3: buy_processing
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)
