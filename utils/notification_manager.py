import logging
from typing import Union

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.subcategory import SubcategoryService
from services.user import UserService
from utils.CryptoAddressGenerator import CryptoAddressGenerator
from bot import bot
from config import ADMIN_ID_LIST
from models.user import User
from utils.other_sql import RefundBuyDTO


class NotificationManager:
    @staticmethod
    async def send_refund_message(refund_data: RefundBuyDTO):
        message = f"You have been refunded ${refund_data.total_price} for the purchase of {refund_data.quantity}" \
                  f" pieces of {refund_data.subcategory}"
        try:
            await bot.send_message(refund_data.telegram_id, f"<b>{message}</b>", parse_mode="html")
        except Exception as e:
            logging.error(e)

    @staticmethod
    async def send_to_admins(message: str, reply_markup: types.InlineKeyboardMarkup):
        for admin_id in ADMIN_ID_LIST:
            try:
                await bot.send_message(admin_id, f"<b>{message}</b>", parse_mode='html', reply_markup=reply_markup)
            except Exception as e:
                logging.error(e)

    @staticmethod
    async def make_user_button(username: Union[str, None]):
        user_button_builder = InlineKeyboardBuilder()
        if isinstance(username, str):
            user_button_inline = types.InlineKeyboardButton(text=username, url=f"https://t.me/{username}")
            user_button_builder.add(user_button_inline)
        return user_button_builder.as_markup()

    @staticmethod
    async def new_deposit(old_crypto_balances: dict, new_crypto_balances: dict, deposit_amount_usd, telegram_id: int):
        deposit_amount_usd = round(deposit_amount_usd, 2)
        merged_crypto_balances = [new_balance - old_balance for (new_balance, old_balance) in
                                  zip(new_crypto_balances.values(),
                                      old_crypto_balances.values())]
        merged_crypto_balances_keys = [key.split('_')[0] for key in new_crypto_balances.keys()]
        merged_crypto_balances = zip(merged_crypto_balances_keys, merged_crypto_balances)
        user = await UserService.get_by_tgid(telegram_id)
        user = user.__dict__
        username = user['telegram_username']
        user_button = await NotificationManager.make_user_button(username)
        if username:
            message = f"New deposit by user with username @{username} for ${deposit_amount_usd} with "
        else:
            message = f"New deposit by user with ID {telegram_id} for ${deposit_amount_usd} with "
        for crypto_name, value in merged_crypto_balances:
            if value > 0:
                if crypto_name == "usdt":
                    message += f"{value} {crypto_name.upper()}\nTRX address:<code>{user['trx_address']}</code>\n"
                else:
                    message += f"{value} {crypto_name.upper()}\n{crypto_name.upper()} address:<code>{user[f'{crypto_name}_address']}</code>\n"
            message += f"Seed: <code>{user['seed']}</code>"
        await NotificationManager.send_to_admins(message, user_button)

    @staticmethod
    async def new_buy(subcategory_id: int, quantity: int, total_price: float, user: User):
        subcategory = await SubcategoryService.get_by_primary_key(subcategory_id)
        message = ""
        username = user.telegram_username
        telegram_id = user.telegram_id
        user_button = await NotificationManager.make_user_button(username)
        if username:
            message += f"A new purchase by user @{username} for the amount of ${total_price} for the " \
                       f"purchase of a {quantity} pcs {subcategory.name}."
        else:
            message += f"A new purchase by user with ID:{telegram_id} for the amount of ${total_price} for the " \
                       f"purchase of a {quantity} pcs {subcategory.name}."
        await NotificationManager.send_to_admins(message, user_button)
