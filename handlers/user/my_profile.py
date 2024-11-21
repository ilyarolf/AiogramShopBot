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
        callback_data=MyProfileCallback.create(level=0))


async def my_profile(message: Message | CallbackQuery):
    user_dto = UserDTO(telegram_id=message.from_user.id)
    msg_text, kb_builder = await UserService.get_my_profile_buttons(user_dto)
    if isinstance(message, Message):
        await message.answer(msg_text, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg_text, reply_markup=kb_builder.as_markup())


async def top_up_balance(callback: CallbackQuery):
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    msg_text, kb_builder = await UserService.get_top_up_buttons(unpacked_cb)
    await callback.message.edit_text(
        text=msg_text,
        reply_markup=kb_builder.as_markup())


async def create_purchase_history_keyboard_builder(page: int, user_id: int):
    # TODO (refactoring)
    orders_markup_builder = InlineKeyboardBuilder()
    orders = await BuyService.get_buys_by_buyer_id(user_id, page)
    for order in orders:
        quantity = order.quantity
        total_price = order.total_price
        buy_id = order.id
        buy_item = await BuyItemService.get_buy_item_by_buy_id(buy_id)
        item = await ItemService.get_by_primary_key(buy_item.item_id)
        item_from_history_callback = MyProfileCallback.create(5, action="get_order",
                                                              args_for_action=str(buy_id))
        orders_markup_builder.button(
            text=Localizator.get_text(BotEntity.USER, "purchase_history_item").format(
                subcategory_name=item.subcategory.name,
                total_price=total_price,
                quantity=quantity,
                currency_sym=Localizator.get_currency_symbol()),
            callback_data=item_from_history_callback)
    orders_markup_builder.adjust(1)
    return orders_markup_builder, len(orders)


async def purchase_history(callback: CallbackQuery):
    unpacked_callback = MyProfileCallback.unpack(callback.data)
    msg_text, kb_builder = await UserService.get_purchase_history_buttons(unpacked_callback, callback.from_user.id)
    await callback.message.edit_text(text=msg_text, reply_markup=kb_builder.as_markup())


async def refresh_balance(callback: CallbackQuery):
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    cryptocurrency = Cryptocurrency(unpacked_cb.args_for_action)
    response = await UserService.refresh_balance(UserDTO(telegram_id=callback.from_user.id), cryptocurrency)
    match response:
        case UserResponse.BALANCE_REFRESHED:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_refreshed_successfully"),
                                  show_alert=True)
            await my_profile(callback)
        case UserResponse.BALANCE_NOT_REFRESHED:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_not_refreshed"),
                                  show_alert=True)
        case UserResponse.BALANCE_REFRESH_COOLDOWN:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_refresh_timeout"), show_alert=True)


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
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    current_level = unpacked_cb.level
    payment_method = Cryptocurrency(unpacked_cb.args_for_action)
    user = await UserService.get(UserDTO(telegram_id=callback.from_user.id))
    bot = await callback.bot.get_me()
    addr = getattr(user, payment_method.get_address_field())
    msg = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(
        bot_name=bot.first_name,
        crypto_name=payment_method.value.replace('_', ' '),
        addr=addr)
    refresh_balance_builder = InlineKeyboardBuilder()
    refresh_balance_builder.button(text=Localizator.get_text(BotEntity.USER, "refresh_balance_button"),
                                   callback_data=MyProfileCallback.create(current_level + 1,
                                                                          args_for_action=payment_method.value))
    refresh_balance_builder.button(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                                   callback_data=MyProfileCallback.create(
                                       level=current_level - 1))
    await callback.message.edit_text(text=msg, reply_markup=refresh_balance_builder.as_markup())


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
