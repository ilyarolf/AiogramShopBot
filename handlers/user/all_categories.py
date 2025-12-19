from aiogram import types, Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from services.cart import CartService
from services.category import CategoryService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

all_categories_router = Router()


@all_categories_router.message(F.text == Localizator.get_text(BotEntity.USER, "all_categories"),
                               IsUserExistFilter())
async def all_categories_text_message(message: types.message, session: AsyncSession | Session):
    await all_categories(callback=message, session=session)


async def all_categories(**kwargs):
    """Show categories at current navigation level."""
    message = kwargs.get("callback")
    session = kwargs.get("session")

    if isinstance(message, Message):
        msg, kb_builder, image_file_id = await CategoryService.get_buttons(session)
        if image_file_id:
            await message.answer_photo(
                photo=image_file_id,
                caption=msg,
                reply_markup=kb_builder.as_markup()
            )
        else:
            await message.answer(msg, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        msg, kb_builder, image_file_id = await CategoryService.get_buttons(session, callback)

        # Determine if we need to switch between photo and text message
        current_message = callback.message
        has_photo = current_message.photo is not None if current_message else False

        if image_file_id:
            if has_photo:
                # Update existing photo message
                await callback.message.edit_media(
                    media=InputMediaPhoto(media=image_file_id, caption=msg),
                    reply_markup=kb_builder.as_markup()
                )
            else:
                # Switch from text to photo - delete and send new
                await callback.message.delete()
                await callback.message.answer_photo(
                    photo=image_file_id,
                    caption=msg,
                    reply_markup=kb_builder.as_markup()
                )
        else:
            if has_photo:
                # Switch from photo to text - delete and send new
                await callback.message.delete()
                await callback.message.answer(msg, reply_markup=kb_builder.as_markup())
            else:
                # Update existing text message
                await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def select_quantity(**kwargs):
    """Show quantity selection for a product."""
    callback = kwargs.get("callback")
    session = kwargs.get("session")

    msg, kb_builder, image_file_id = await CategoryService.get_product_details(callback, session)
    current_message = callback.message
    has_photo = current_message.photo is not None if current_message else False

    if image_file_id:
        if has_photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=image_file_id, caption=msg),
                reply_markup=kb_builder.as_markup()
            )
        else:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=image_file_id,
                caption=msg,
                reply_markup=kb_builder.as_markup()
            )
    else:
        if has_photo:
            await callback.message.delete()
            await callback.message.answer(msg, reply_markup=kb_builder.as_markup())
        else:
            await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def add_to_cart_confirmation(**kwargs):
    """Show add to cart confirmation."""
    callback = kwargs.get("callback")
    session = kwargs.get("session")

    msg, kb_builder, image_file_id = await CategoryService.get_add_to_cart_buttons(callback, session)
    current_message = callback.message
    has_photo = current_message.photo is not None if current_message else False

    if image_file_id:
        if has_photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=image_file_id, caption=msg),
                reply_markup=kb_builder.as_markup()
            )
        else:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=image_file_id,
                caption=msg,
                reply_markup=kb_builder.as_markup()
            )
    else:
        if has_photo:
            await callback.message.delete()
            await callback.message.answer(msg, reply_markup=kb_builder.as_markup())
        else:
            await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_to_cart(**kwargs):
    """Add item to cart."""
    callback = kwargs.get("callback")
    session = kwargs.get("session")

    await CartService.add_to_cart(callback, session)

    # Clean up photo message if present
    current_message = callback.message
    if current_message.photo:
        await callback.message.delete()
        await callback.message.answer(text=Localizator.get_text(BotEntity.USER, "item_added_to_cart"))
    else:
        await callback.message.edit_text(text=Localizator.get_text(BotEntity.USER, "item_added_to_cart"))


@all_categories_router.callback_query(AllCategoriesCallback.filter(), IsUserExistFilter())
async def navigate_categories(callback: CallbackQuery, callback_data: AllCategoriesCallback,
                              session: AsyncSession | Session):
    """
    Dynamic navigation through category tree.

    Levels work as follows:
    - Level 0: Root categories (or any non-product category view)
    - When clicking a non-product category: stay at same level, just change category_id
    - When clicking a product category: move to level 1 (quantity selection)
    - Level 1: Quantity selection for product
    - Level 2: Add to cart confirmation
    - Level 3: Add to cart execution
    """
    current_level = callback_data.level

    if current_level == 0:
        # Navigation mode - show categories/children
        await all_categories(callback=callback, session=session)
    elif current_level == 1:
        # Quantity selection mode
        await select_quantity(callback=callback, session=session)
    elif current_level == 2:
        # Add to cart confirmation
        await add_to_cart_confirmation(callback=callback, session=session)
    elif current_level == 3:
        # Execute add to cart
        await add_to_cart(callback=callback, session=session)
    else:
        # Fallback to navigation
        await all_categories(callback=callback, session=session)
