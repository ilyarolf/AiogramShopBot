from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from handlers.user.constants import UserStates
from services.cart import CartService
from services.category import CategoryService
from services.subcategory import SubcategoryService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

all_categories_router = Router()


@all_categories_router.message(F.text == Localizator.get_text(BotEntity.USER, "all_categories"),
                               IsUserExistFilter())
async def all_categories_text_message(message: Message, session: AsyncSession, state: FSMContext):
    await all_categories(callback=message, session=session, state=state)


async def all_categories(**kwargs):
    message: CallbackQuery | Message = kwargs.get("callback")
    callback_data: AllCategoriesCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    if isinstance(message, Message):
        await state.clear()
        media, kb_builder = await CategoryService.get_buttons(callback_data, state, session)
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
        state_data = await state.get_data()
        if callback_data.is_filter_enabled and state_data.get('filter') is not None:
            media, kb_builder = await CategoryService.get_buttons(callback_data, state, session)
        elif callback_data.is_filter_enabled:
            media, kb_builder = await CategoryService.enable_search(callback_data, EntityType.CATEGORY, state)
        else:
            media, kb_builder = await CategoryService.get_buttons(callback_data, state, session)
        await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def show_subcategories_in_category(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: AllCategoriesCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    media, kb_builder = await SubcategoryService.get_buttons(callback_data, state, session)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def select_quantity(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: AllCategoriesCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    media, kb_builder = await SubcategoryService.get_select_quantity_buttons(callback_data, session)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


async def add_to_cart_confirmation(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: AllCategoriesCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await SubcategoryService.get_add_to_cart_buttons(callback_data, session)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def add_to_cart(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: AllCategoriesCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    media, kb_builder = await CartService.add_to_cart(callback, callback_data, session)
    await callback.message.edit_media(media=media, reply_markup=kb_builder.as_markup())


@all_categories_router.message(IsUserExistFilter(), StateFilter(UserStates.filter))
async def receive_filter_message(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(filter=message.html_text)
    state_data = await state.get_data()
    entity_type = EntityType(state_data['entity_type'])
    if entity_type == EntityType.CATEGORY:
        media, kb_builder = await CategoryService.get_buttons(None, state, session)
    else:
        media, kb_builder = await SubcategoryService.get_buttons(None, state, session)
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


@all_categories_router.callback_query(AllCategoriesCallback.filter(), IsUserExistFilter())
async def navigate_categories(callback: CallbackQuery, callback_data: AllCategoriesCallback,
                              session: AsyncSession, state: FSMContext):
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
        "callback_data": callback_data,
        "state": state
    }

    await current_level_function(**kwargs)
