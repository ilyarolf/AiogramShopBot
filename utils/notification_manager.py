import logging
from typing import Union

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.subcategory import SubcategoryService
from services.user import UserService
from bot import bot
from config import ADMIN_ID_LIST
from models.user import User
from utils.localizator import Localizator
from utils.other_sql import RefundBuyDTO


class NotificationManager:
    @staticmethod
    async def send_refund_message(refund_data: RefundBuyDTO):
        message = Localizator.get_text_from_key("user_notification_refund").format(total_price=refund_data.total_price,
                                                                                   quantity=refund_data.quantity,
                                                                                   subcategory=refund_data.subcategory)
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
            message = Localizator.get_text_from_key("admin_notification_new_deposit_username").format(
                username=username,
                deposit_amount_usd=deposit_amount_usd)
        else:
            message = Localizator.get_text_from_key("admin_notification_new_deposit_id").format(
                telegram_id=telegram_id,
                deposit_amount_usd=deposit_amount_usd)
        for crypto_name, value in merged_crypto_balances:
            if value > 0:
                if crypto_name == "usdt":
                    message += Localizator.get_text_from_key("usdt_deposit_notification_part").format(
                        value=value,
                        crypto_name=crypto_name.upper(),
                        trx_address=user[
                            'trx_address'])
                else:
                    crypto_address = user[f'{crypto_name}_address']
                    message += Localizator.get_text_from_key("crypto_deposit_notification_part").format(
                        value=value,
                        crypto_name=crypto_name.upper(),
                        crypto_address=crypto_address)
        message += Localizator.get_text_from_key("seed_notification_part").format(seed=user['seed'])
        await NotificationManager.send_to_admins(message, user_button)

    @staticmethod
    async def new_buy(subcategory_id: int, quantity: int, total_price: float, user: User):
        subcategory = await SubcategoryService.get_by_primary_key(subcategory_id)
        message = ""
        username = user.telegram_username
        telegram_id = user.telegram_id
        user_button = await NotificationManager.make_user_button(username)
        if username:
            message += Localizator.get_text_from_key("new_purchase_notification_with_tgid").format(
                username=username,
                total_price=total_price,
                quantity=quantity,
                subcategory_name=subcategory.name)
        else:
            message += Localizator.get_text_from_key("new_purchase_notification_with_username").format(
                telegram_id=telegram_id,
                total_price=total_price,
                quantity=quantity,
                subcategory_name=subcategory.name)
        await NotificationManager.send_to_admins(message, user_button)
