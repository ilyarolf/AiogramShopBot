from aiogram import types, Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import MyProfileCallback
from enums.user import UserResponse
from handlers.common.common import add_pagination_buttons
# from handlers.user.cart import create_message_with_bought_items
from enums.cryptocurrency import Cryptocurrency
from models.user import UserDTO
from services.buy import BuyService
from services.buyItem import BuyItemService
from services.item import ItemService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator, BotEntity
from utils.tags_remover import HTMLTagsRemover

my_profile_router = Router()


@my_profile_router.message(F.text == Localizator.get_text(BotEntity.USER, "my_profile"), IsUserExistFilter())
async def my_profile_text_message(message: types.message):
    await my_profile(message)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "back_to_my_profile"),
        callback_data=MyProfileCallback.create(level=0).pack())


async def my_profile(message: Message | CallbackQuery):
    user_dto = UserDTO(telegram_id=message.from_user.id)
    msg_text, kb_builder = await UserService.get_my_profile_buttons(user_dto)
    if isinstance(message, Message):
        await message.answer(msg_text, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg_text, reply_markup=kb_builder.as_markup())


async def top_up_balance(callback: CallbackQuery):
    msg_text, kb_builder = await UserService.get_top_up_buttons(callback)
    await callback.message.edit_text(text=msg_text, reply_markup=kb_builder.as_markup())


async def purchase_history(callback: CallbackQuery):
    msg_text, kb_builder = await UserService.get_purchase_history_buttons(callback, callback.from_user.id)
    await callback.message.edit_text(text=msg_text, reply_markup=kb_builder.as_markup())


async def refresh_balance(callback: CallbackQuery):
    msg, response = await UserService.refresh_balance(callback)
    match response:
        case UserResponse.BALANCE_REFRESHED:
            await callback.answer(msg, show_alert=True)
            await my_profile(callback)
        case UserResponse.BALANCE_NOT_REFRESHED:
            await callback.answer(msg, show_alert=True)
        case UserResponse.BALANCE_REFRESH_COOLDOWN:
            await callback.answer(msg, show_alert=True)


async def get_order_from_history(callback: CallbackQuery):
    pass
    # current_level = 5
    # buy_id = MyProfileCallback.unpack(callback.data).args_for_action
    # items = await ItemService.get_items_by_buy_id(buy_id)
    # message = await create_message_with_bought_items(items)
    # back_builder = InlineKeyboardBuilder()
    # back_builder.button(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
    #                     callback_data=create_callback_profile(level=current_level - 1))
    # await callback.message.edit_text(text=message, reply_markup=back_builder.as_markup())


async def top_up_by_method(callback: CallbackQuery):
    msg, kb_builder = await UserService.get_top_up_by_msg(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery, callback_data: MyProfileCallback):
    current_level = callback_data.level

    levels = {
        0: my_profile,
        1: top_up_balance,
        2: top_up_by_method,
        3: refresh_balance,
        4: purchase_history,
        5: get_order_from_history
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)
