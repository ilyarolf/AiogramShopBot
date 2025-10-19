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
async def all_categories_text_message(message: types.message, session: AsyncSession | Session):
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
    await CartService.add_to_cart(callback, session)

    # Show confirmation message briefly
    await callback.answer(text=Localizator.get_text(BotEntity.USER, "item_added_to_cart"), show_alert=False)

    # Create new callback with level=1 to return to subcategory list
    unpacked_cb = AllCategoriesCallback.unpack(callback.data)
    # Create a modified callback pointing to level 1 (subcategory list) with preserved category
    new_callback_data = AllCategoriesCallback.create(
        level=1,
        category_id=unpacked_cb.category_id,
        page=unpacked_cb.page
    )

    # Manually trigger subcategory view by modifying callback data
    callback.data = new_callback_data.pack()

    # Return to subcategory list to continue shopping
    await show_subcategories_in_category(callback=callback, session=session)


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
