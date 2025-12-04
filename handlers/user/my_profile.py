from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.keyboard_button import KeyboardButton as KB
from enums.language import Language
from handlers.common.common import enable_search
from handlers.user.constants import UserStates
from services.buy import BuyService
from services.notification import NotificationService
from services.payment import PaymentService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.utils import get_bot_photo_id, get_text

my_profile_router = Router()


@my_profile_router.message(F.text.in_(KB.get_localized_set(KB.MY_PROFILE)), IsUserExistFilter())
async def my_profile_text_message(message: Message, session: AsyncSession, state: FSMContext, language: Language):
    await my_profile(message=message, session=session, state=state, language=language)


async def my_profile(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    media, kb_builder = await UserService.get_my_profile_buttons(message.from_user.id, session, language)
    if isinstance(message, Message):
        await NotificationService.answer_media(message, media, kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_media(media=media,
                                          reply_markup=kb_builder.as_markup())


async def top_up_balance(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    msg_text, kb_builder = await UserService.get_top_up_buttons(callback_data, language)
    await callback.message.edit_caption(caption=msg_text, reply_markup=kb_builder.as_markup())


async def purchase_history(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    state_data = await state.get_data()
    if callback_data.is_filter_enabled and state_data.get('filter') is not None:
        msg_text, kb_builder = await UserService.get_purchase_history_buttons(callback.from_user.id, callback_data,
                                                                              state, session, language)
    elif callback_data.is_filter_enabled:
        media, kb_builder = await enable_search(callback_data, EntityType.SUBCATEGORY, state,
                                                UserStates.filter_purchase_history, language)
        msg_text = media.caption
    else:
        await state.update_data(filter=None)
        await state.set_state()
        msg_text, kb_builder = await UserService.get_purchase_history_buttons(callback.from_user.id, callback_data,
                                                                              state, session, language)
    await callback.message.edit_caption(caption=msg_text, reply_markup=kb_builder.as_markup())


async def get_order_from_history(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    language: Language = kwargs.get("language")
    msg, kb_builder = await BuyService.get_purchase(callback_data, session, language)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def create_payment(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    language: Language = kwargs.get("language")
    msg = await callback.message.edit_caption(caption=get_text(language, BotEntity.USER, "loading"))
    response = await PaymentService.create(callback_data.cryptocurrency, msg, session, language)
    if isinstance(response, str):
        await msg.edit_caption(caption=response)
    else:
        await msg.edit_media(media=response)


@my_profile_router.message(IsUserExistFilter(), F.text, StateFilter(UserStates.filter_purchase_history))
async def receive_filter_message(message: Message, state: FSMContext, session: AsyncSession, language: Language):
    await state.update_data(filter=message.html_text)
    caption, kb_builder = await UserService.get_purchase_history_buttons(message.from_user.id,
                                                                         None, state, session, language)
    bot_photo_id = get_bot_photo_id()
    media = InputMediaPhoto(media=bot_photo_id,
                            caption=caption)
    await NotificationService.answer_media(message, media, kb_builder.as_markup())


@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery,
                   callback_data: MyProfileCallback,
                   session: AsyncSession,
                   state: FSMContext,
                   language: Language):
    current_level = callback_data.level

    levels = {
        0: my_profile,
        1: top_up_balance,
        2: create_payment,
        4: purchase_history,
        5: get_order_from_history
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
        "callback_data": callback_data,
        "state": state,
        "language": language
    }

    await current_level_function(**kwargs)
