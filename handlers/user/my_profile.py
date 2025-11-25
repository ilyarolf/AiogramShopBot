from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from services.buy import BuyService
from services.payment import PaymentService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

my_profile_router = Router()


@my_profile_router.message(F.text == Localizator.get_text(BotEntity.USER, "my_profile"), IsUserExistFilter())
async def my_profile_text_message(message: types.message, session: AsyncSession):
    await my_profile(message=message, session=session)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "back_to_my_profile"),
        callback_data=MyProfileCallback.create(level=0).pack())


async def my_profile(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    media, kb_builder = await UserService.get_my_profile_buttons(message.from_user.id, session)
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
        await callback.message.edit_media(media=media,
                                          reply_markup=kb_builder.as_markup())


async def top_up_balance(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    msg_text, kb_builder = await UserService.get_top_up_buttons(callback_data)
    await callback.message.edit_caption(caption=msg_text, reply_markup=kb_builder.as_markup())


async def purchase_history(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    state: FSMContext = kwargs.get("state")
    msg_text, kb_builder = await UserService.get_purchase_history_buttons(callback, callback_data, state, session)
    await callback.message.edit_caption(caption=msg_text, reply_markup=kb_builder.as_markup())


async def get_order_from_history(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    session: AsyncSession = kwargs.get("session")
    msg, kb_builder = await BuyService.get_purchase(callback_data, session)
    await callback.message.edit_caption(caption=msg, reply_markup=kb_builder.as_markup())


async def create_payment(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession = kwargs.get("session")
    callback_data: MyProfileCallback = kwargs.get("callback_data")
    msg = await callback.message.edit_caption(caption=Localizator.get_text(BotEntity.USER, "loading"))
    response = await PaymentService.create(callback_data.cryptocurrency, msg, session)
    if isinstance(response, str):
        await msg.edit_caption(caption=response)
    else:
        await msg.edit_media(media=response)


@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery, callback_data: MyProfileCallback, session: AsyncSession,
                   state: FSMContext):
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
        "state": state
    }

    await current_level_function(**kwargs)
