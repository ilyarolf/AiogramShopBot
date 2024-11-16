from typing import Union

from aiogram import types, Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from crypto_api.CryptoApiManager import CryptoApiManager
from handlers.common.common import add_pagination_buttons
from handlers.user.cart import create_message_with_bought_items
from services.buy import BuyService
from services.buyItem import BuyItemService
from services.item import ItemService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator, BotEntity
from utils.notification_manager import NotificationManager
from utils.tags_remover import HTMLTagsRemover

my_profile_router = Router()


class MyProfileCallback(CallbackData, prefix="my_profile"):
    level: int
    action: str
    args_for_action: Union[int, str]
    page: int


def create_callback_profile(level: int, action: str = "", args_for_action="", page=0):
    return MyProfileCallback(level=level, action=action, args_for_action=args_for_action, page=page).pack()


@my_profile_router.message(F.text == Localizator.get_text(BotEntity.USER, "my_profile"), IsUserExistFilter())
async def my_profile_text_message(message: types.message):
    await my_profile(message)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "back_to_my_profile"),
        callback_data=create_callback_profile(level=0))


async def get_my_profile_message(telegram_id: int):
    user = await UserService.get_by_tgid(telegram_id)
    fiat_balance = round(user.top_up_amount - user.consume_records, 2)
    return Localizator.get_text(BotEntity.USER, "my_profile_msg").format(telegram_id=telegram_id,
                                                                         btc_balance=user.btc_balance,
                                                                         ltc_balance=user.ltc_balance,
                                                                         sol_balance=user.sol_balance,
                                                                         usdt_trc20_balance=user.usdt_trc20_balance,
                                                                         usdt_erc20_balance=user.usdt_erc20_balance,
                                                                         usdc_erc20_balance=user.usdc_erc20_balance,
                                                                         fiat_balance=fiat_balance,
                                                                         currency_text=Localizator.get_currency_text(),
                                                                         currency_sym=Localizator.get_currency_symbol())


async def my_profile(message: Union[Message, CallbackQuery]):
    current_level = 0
    top_up_button = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "top_up_balance_button"),
        callback_data=create_callback_profile(current_level + 1, "top_up"))
    purchase_history_button = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "purchase_history_button"),
        callback_data=create_callback_profile(current_level + 4,
                                              "purchase_history"))
    my_profile_builder = InlineKeyboardBuilder()
    my_profile_builder.add(top_up_button, purchase_history_button)
    my_profile_builder.adjust(2)
    my_profile_markup = my_profile_builder.as_markup()

    if isinstance(message, Message):
        telegram_id = message.chat.id
        message_text = await get_my_profile_message(telegram_id)
        await message.answer(message_text, reply_markup=my_profile_markup)
    elif isinstance(message, CallbackQuery):
        callback = message
        telegram_id = callback.from_user.id
        message = await get_my_profile_message(telegram_id)
        raw_message_text = HTMLTagsRemover.remove_html_tags(message)
        if raw_message_text != callback.message.text:
            await callback.message.edit_text(message, reply_markup=my_profile_markup)
        else:
            await callback.answer()


async def top_up_balance(callback: CallbackQuery):
    current_level = 1
    back_to_profile_button = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.COMMON, "back_button"),
        callback_data=create_callback_profile(current_level - 1))
    top_up_methods_builder = InlineKeyboardBuilder()
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action="BTC"))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action="LTC"))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action="SOL"))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.USER, "usdt_trc20_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action="TRX_USDT"))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.USER, "usdt_erc20_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action="ETH_USDT"))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.USER, "usdc_trc20_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action="ETH_USDC"))
    top_up_methods_builder.row(back_to_profile_button)
    top_up_methods_builder.adjust(1)
    await callback.message.edit_text(
        text=Localizator.get_text(BotEntity.USER, "choose_top_up_method"),
        reply_markup=top_up_methods_builder.as_markup())
    await callback.answer()


async def create_purchase_history_keyboard_builder(page: int, user_id: int):
    orders_markup_builder = InlineKeyboardBuilder()
    orders = await BuyService.get_buys_by_buyer_id(user_id, page)
    for order in orders:
        quantity = order.quantity
        total_price = order.total_price
        buy_id = order.id
        buy_item = await BuyItemService.get_buy_item_by_buy_id(buy_id)
        item = await ItemService.get_by_primary_key(buy_item.item_id)
        item_from_history_callback = create_callback_profile(5, action="get_order",
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
    telegram_id = callback.message.chat.id
    user = await UserService.get_by_tgid(telegram_id)
    orders_markup_builder, orders_num = await create_purchase_history_keyboard_builder(unpacked_callback.page, user.id)
    orders_markup_builder = await add_pagination_buttons(orders_markup_builder, callback.data,
                                                         BuyService.get_max_page_purchase_history(user.id),
                                                         MyProfileCallback.unpack, MyProfileConstants.back_to_main_menu)
    if orders_num == 0:
        await callback.message.edit_text(Localizator.get_text(BotEntity.USER, "no_purchases"),
                                         reply_markup=orders_markup_builder.as_markup())
    else:
        await callback.message.edit_text(Localizator.get_text(BotEntity.USER, "purchases"),
                                         reply_markup=orders_markup_builder.as_markup())
    await callback.answer()


async def refresh_balance(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    crypto_info = unpacked_cb.args_for_action
    if await UserService.can_refresh_balance(telegram_id):
        await UserService.create_last_balance_refresh_data(telegram_id)
        user = await UserService.get_by_tgid(telegram_id)
        addresses = await UserService.get_addresses(telegram_id)
        new_crypto_deposits = await CryptoApiManager(**addresses, user_id=user.id).get_top_up_by_crypto_name(
            crypto_info)
        crypto_prices = await CryptoApiManager.get_crypto_prices()
        deposit_usd_amount = 0.0
        bot_obj = callback.bot
        if sum(new_crypto_deposits.values()) > 0:
            for balance_key, balance in new_crypto_deposits.items():
                balance_key = balance_key.split('_')[0]
                crypto_balance_in_usd = balance * crypto_prices[balance_key]
                deposit_usd_amount += crypto_balance_in_usd
            await UserService.update_crypto_balances(telegram_id, new_crypto_deposits)
            await UserService.update_top_up_amount(telegram_id, deposit_usd_amount)
            await NotificationManager.new_deposit(new_crypto_deposits, deposit_usd_amount,
                                                  telegram_id, bot_obj)
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_refreshed_successfully"),
                                  show_alert=True)
            await my_profile(callback)
        else:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_not_refreshed"),
                                  show_alert=True)
    else:
        await callback.answer(Localizator.get_text(BotEntity.USER, "balance_refresh_timeout"), show_alert=True)


async def get_order_from_history(callback: CallbackQuery):
    current_level = 5
    buy_id = MyProfileCallback.unpack(callback.data).args_for_action
    items = await ItemService.get_items_by_buy_id(buy_id)
    message = await create_message_with_bought_items(items)
    back_builder = InlineKeyboardBuilder()
    back_builder.button(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                        callback_data=create_callback_profile(level=current_level - 1))
    await callback.message.edit_text(text=message, reply_markup=back_builder.as_markup())


async def top_up_by_method(callback: CallbackQuery):
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    current_level = unpacked_cb.level
    payment_method = unpacked_cb.args_for_action
    addr = ""
    user = await UserService.get_by_tgid(callback.from_user.id)
    bot = await callback.bot.get_me()
    if payment_method == "BTC":
        addr = user.btc_address
    elif payment_method == "LTC":
        addr = user.ltc_address
    elif payment_method == "SOL":
        addr = user.sol_address
    elif "ETH" in payment_method:
        addr = user.eth_address
    elif "TRX" in payment_method:
        addr = user.trx_address
    msg = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(bot_name=bot.first_name,
                                                                            crypto_name=payment_method.split("_")[0],
                                                                            addr=addr)
    refresh_balance_builder = InlineKeyboardBuilder()
    refresh_balance_builder.button(text=Localizator.get_text(BotEntity.USER, "refresh_balance_button"),
                                   callback_data=create_callback_profile(current_level + 1,
                                                                         args_for_action=payment_method))
    refresh_balance_builder.button(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                                   callback_data=create_callback_profile(
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
