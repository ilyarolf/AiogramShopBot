from aiogram import types, Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from services.cart import CartService
from services.category import CategoryService
from services.subcategory import SubcategoryService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

all_categories_router = Router()


@all_categories_router.message(F.text == Localizator.get_text(BotEntity.USER, "all_categories"),
                               IsUserExistFilter())
async def all_categories_text_message(message: types.Message, session: AsyncSession | Session):
    import logging
    logging.info("🗂️ ALL CATEGORIES BUTTON HANDLER TRIGGERED")
    await all_categories(callback=message, session=session)


async def all_categories(**kwargs):
    message = kwargs.get("callback")
    session = kwargs.get("session")
    if isinstance(message, Message):
        msg, kb_builder = await CategoryService.get_buttons(session)
        await message.answer(msg, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        msg, kb_builder = await CategoryService.get_buttons(session, callback)
        await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def show_subcategories_in_category(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await SubcategoryService.get_buttons(callback, session)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def select_quantity(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await SubcategoryService.get_select_quantity_buttons(callback, session)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def add_to_cart_confirmation(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await SubcategoryService.get_add_to_cart_buttons(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_to_cart(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    success, message_key, format_args = await CartService.add_to_cart(callback, session)

    # Show confirmation or warning message
    message = Localizator.get_text(BotEntity.USER, message_key)
    if format_args:
        message = message.format(**format_args)

    # Show alert for failures OR warnings (stock reduced)
    show_alert = (not success) or (message_key == "add_to_cart_stock_reduced")
    await callback.answer(text=message, show_alert=show_alert)

    # Get current context and build new callback with level 1 for subcategory list
    unpacked_cb = AllCategoriesCallback.unpack(callback.data)

    # Create a new callback query object with level 1 to avoid KeyError
    # We need to use model_copy to create a new CallbackQuery with modified data
    from aiogram.types import CallbackQuery as CQ
    from copy import copy

    # Create callback data for level 1 (subcategory list)
    new_callback_data = AllCategoriesCallback.create(
        level=1,
        category_id=unpacked_cb.category_id,
        page=unpacked_cb.page
    )

    # Create a shallow copy of callback with new data string
    modified_callback = copy(callback)
    object.__setattr__(modified_callback, 'data', new_callback_data.pack())

    # Build subcategory list message and buttons with the modified callback
    msg, kb_builder = await SubcategoryService.get_buttons(modified_callback, session)

    # Edit message to show subcategory list, preserving category context
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


@all_categories_router.callback_query(AllCategoriesCallback.filter(), IsUserExistFilter())
async def navigate_categories(callback: CallbackQuery, callback_data: AllCategoriesCallback,
                              session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: all_categories,
        1: show_subcategories_in_category,
        2: select_quantity,
        3: add_to_cart_confirmation,
        4: add_to_cart
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
    }

    await current_level_function(**kwargs)
