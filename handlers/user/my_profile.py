from aiogram import types, Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from services.buy import BuyService
from services.payment import PaymentService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

my_profile_router = Router()


@my_profile_router.message(F.text == Localizator.get_text(BotEntity.USER, "my_profile"), IsUserExistFilter())
async def my_profile_text_message(message: types.message, session: Session | AsyncSession):
    await my_profile(message=message, session=session)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "back_to_my_profile"),
        callback_data=MyProfileCallback.create(level=0).pack())


async def my_profile(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    session: Session | AsyncSession = kwargs.get("session")
    msg_text, kb_builder = await UserService.get_my_profile_buttons(message.from_user.id, session)
    if isinstance(message, Message):
        await message.answer(msg_text, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg_text, reply_markup=kb_builder.as_markup())


async def top_up_balance(**kwargs):
    callback = kwargs.get("callback")
    msg_text, kb_builder = await UserService.get_top_up_buttons(callback)
    await callback.message.edit_text(text=msg_text, reply_markup=kb_builder.as_markup())


async def purchase_history(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg_text, kb_builder = await UserService.get_purchase_history_buttons(callback, session)
    await callback.message.edit_text(text=msg_text, reply_markup=kb_builder.as_markup())


async def get_order_from_history(**kwargs):
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    msg, kb_builder = await BuyService.get_purchase(callback, session)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def create_payment(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    session: AsyncSession | Session = kwargs.get("session")
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    msg = await callback.message.edit_text(Localizator.get_text(BotEntity.USER, "loading"))
    text = await PaymentService.create(Cryptocurrency(unpacked_cb.args_for_action), msg, session)
    await msg.edit_text(text=text)


@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery, callback_data: MyProfileCallback, session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: my_profile,
        1: top_up_balance,
        2: create_payment,
        # 3: refresh_balance,
        4: purchase_history,
        5: get_order_from_history
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
    }

    await current_level_function(**kwargs)
