from aiogram import types, Router, F
from aiogram.types import Message, CallbackQuery
from callbacks import AllCategoriesCallback
from services.cart import CartService
from services.category import CategoryService
from services.subcategory import SubcategoryService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator, BotEntity

all_categories_router = Router()


@all_categories_router.message(F.text == Localizator.get_text(BotEntity.USER, "all_categories"),
                               IsUserExistFilter())
async def all_categories_text_message(message: types.message):
    await all_categories(message)


async def all_categories(message: Message | CallbackQuery):
    if isinstance(message, Message):
        msg, kb_builder = await CategoryService.get_buttons()
        await message.answer(msg, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        msg, kb_builder = await CategoryService.get_buttons(callback)
        await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def show_subcategories_in_category(callback: CallbackQuery):
    msg, kb_builder = await SubcategoryService.get_buttons(callback)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def select_quantity(callback: CallbackQuery):
    msg, kb_builder = await SubcategoryService.get_select_quantity_buttons(callback)
    await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def add_to_cart_confirmation(callback: CallbackQuery):
    msg, kb_builder = await SubcategoryService.get_add_to_cart_buttons(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def add_to_cart(callback: CallbackQuery):
    await CartService.add_to_cart(callback)
    await callback.message.edit_text(text=Localizator.get_text(BotEntity.USER, "item_added_to_cart"))


@all_categories_router.callback_query(AllCategoriesCallback.filter(), IsUserExistFilter())
async def navigate_categories(call: CallbackQuery, callback_data: AllCategoriesCallback):
    current_level = callback_data.level

    levels = {
        0: all_categories,
        1: show_subcategories_in_category,
        2: select_quantity,
        3: add_to_cart_confirmation,
        4: add_to_cart
    }

    current_level_function = levels[current_level]

    await current_level_function(call)
