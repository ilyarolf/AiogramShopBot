import itertools
from typing import Union

from aiogram import types
from aiogram.types import CallbackQuery, Message
from aiogram.utils.callback_data import CallbackData

from crypto_api.CryptoApiManager import CryptoApiManager
from db import db
from models.user import User

my_profile_cb = CallbackData("profile", "level", "action", "args_for_action")


def create_callback_profile(level: int, action: str = "", args_for_action=""):
    return my_profile_cb.new(level=level,
                             action=action,
                             args_for_action=args_for_action)


async def my_profile_text_message(message: types.message):
    await my_profile(message)


def get_my_profile_message(telegram_id: int):
    user = User.get(telegram_id)
    btc_balance = user["btc_balance"]
    usdt_balance = user["usdt_balance"]
    ltc_balance = user["ltc_balance"]
    usd_balance = format(user["top_up_amount"] - user["consume_records"], '.2f')
    return (f'<b>Your profile\nID:</b> <code>{telegram_id}</code>\n\n'
            f'<b>Your BTC balance:</b>\n<code>{btc_balance}</code>\n'
            f'<b>Your USDT balance:</b>\n<code>{usdt_balance}</code>\n'
            f'<b>Your LTC balance:</b>\n<code>{ltc_balance}</code>\n'
            f"<b>Your balance in USD:</b>\n{usd_balance}$")


async def my_profile(message: Union[Message, CallbackQuery]):
    current_level = 0
    top_up_button = types.InlineKeyboardButton('Top Up balance',
                                               callback_data=create_callback_profile(current_level + 1, "top_up"))
    purchase_history = types.InlineKeyboardButton('Purchase history',
                                                  callback_data=create_callback_profile(current_level + 2,
                                                                                        "purchase_history"))
    update_balance = types.InlineKeyboardButton('Refresh balance',
                                                callback_data=create_callback_profile(current_level + 3,
                                                                                      "refresh_balance"))
    my_profile_markup = types.InlineKeyboardMarkup(row_width=2)
    my_profile_markup.add(top_up_button, purchase_history, update_balance)

    if isinstance(message, Message):
        telegram_id = message.chat.id
        message_text = get_my_profile_message(telegram_id)
        await message.answer(message_text, parse_mode="HTML", reply_markup=my_profile_markup)
    elif isinstance(message, CallbackQuery):
        callback = message
        telegram_id = callback.from_user.id
        message = get_my_profile_message(telegram_id)
        await callback.message.edit_text(message, parse_mode="HTML", reply_markup=my_profile_markup)


async def top_up_balance(callback: CallbackQuery):
    telegram_id = callback.message.chat.id
    user = User.get(telegram_id)
    current_level = 1
    btc_address = user["btc_address"]
    trx_address = user["trx_address"]
    ltc_address = user["ltc_address"]
    back_to_profile_button = types.InlineKeyboardButton('Back',
                                                        callback_data=create_callback_profile(current_level - 1))
    back_button_markup = types.InlineKeyboardMarkup()
    back_button_markup.add(back_to_profile_button)
    await callback.message.edit_text(
        f'<b>Deposit to the address the amount you want to top up the Shop Bot</b> \n\n'
        f'<b>Important</b>\n<i>A unique BTC/LTC/USDT addresses is given for each deposit\n'
        f'The top up takes place within 5 minutes after the transfer</i>\n\n'
        f'<b>Your BTC address\n</b><code>{btc_address}</code>\n'
        f'<b>Your USDT TRC-20 address\n</b><code>{trx_address}</code>\n'
        f'<b>Your LTC address</b>\n<code>{ltc_address}</code>\n', parse_mode='html',
        reply_markup=back_button_markup)
    await callback.answer()


async def purchase_history(callback: CallbackQuery):
    telegram_id = callback.message.chat.id
    current_level = 2
    orders = db.cursor.execute('SELECT * FROM `buys` where `telegram_id` = ?', (telegram_id,)).fetchall()
    orders_markup = types.InlineKeyboardMarkup()
    back_to_profile_button = types.InlineKeyboardButton('Back',
                                                        callback_data=create_callback_profile(current_level - 2))
    for i in range(len(orders)):
        order_inline = types.InlineKeyboardButton(
            f'{orders[i][2]} | Total Price: {orders[i][4]}$ | Quantity: {orders[i][3]} pcs',
            callback_data=f'order_history_{orders[i][0]}')
        orders_markup.add(order_inline)
    orders_markup.add(back_to_profile_button)
    if not orders:
        await callback.message.edit_text("<b>You haven't had any orders yet</b>", reply_markup=orders_markup,
                                         parse_mode='html')
    else:
        await callback.message.edit_text('<b>Your orders</b>', reply_markup=orders_markup, parse_mode='html')
    await callback.answer()


async def refresh_balance(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    if User.can_refresh_balance(telegram_id):
        old_balances = User.get_balances(telegram_id)
        User.create_last_balance_refresh_data(telegram_id)
        addresses = User.get_addresses(telegram_id)
        new_crypto_balances = await CryptoApiManager(**addresses).get_top_ups()
        crypto_prices = await CryptoApiManager.get_crypto_prices()
        new_usd_balance = 0.0
        if sum(new_crypto_balances.values()) > sum(old_balances.values()):
            for (balance_key, balance), (crypto_key, crypto_price) in itertools.product(new_crypto_balances.items(),
                                                                                        crypto_prices.items()):
                new_value = balance * crypto_price
                new_usd_balance += new_value
            User.update_crypto_balances(telegram_id, new_crypto_balances)
            User.update_usd_balance(telegram_id, new_usd_balance)
    await callback.answer()


async def navigate(call: CallbackQuery, callback_data: dict):
    current_level = callback_data.get("level")

    levels = {
        "0": my_profile,
        "1": top_up_balance,
        "2": purchase_history,
        "3": refresh_balance,
    }

    current_level_function = levels[current_level]

    await current_level_function(call)
