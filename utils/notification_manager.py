import logging
from typing import Union
from db import get_db_session, close_db_session
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.subcategory import SubcategoryService
from services.category import CategoryService
from services.user import UserService
from config import ADMIN_ID_LIST
from models.user import User
from utils.localizator import Localizator
from utils.other_sql import RefundBuyDTO


class NotificationManager:
    @staticmethod
    async def send_refund_message(refund_data: RefundBuyDTO, bot):
        message = Localizator.get_text_from_key("user_notification_refund").format(total_price=refund_data.total_price,
                                                                                   quantity=refund_data.quantity,
                                                                                   subcategory=refund_data.subcategory)
        try:
            await bot.send_message(refund_data.telegram_id, f"<b>{message}</b>")
        except Exception as e:
            logging.error(e)

    @staticmethod
    async def send_to_admins(message: str, reply_markup: types.InlineKeyboardMarkup, bot):
        for admin_id in ADMIN_ID_LIST:
            try:
                await bot.send_message(admin_id, f"<b>{message}</b>", reply_markup=reply_markup)
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
    async def new_deposit(new_crypto_balances: dict, deposit_amount_usd, telegram_id: int, bot):
        deposit_amount_usd = round(deposit_amount_usd, 2)
        merged_crypto_balances = {
            key.replace('_deposit', "").replace('_', ' ').upper(): value
            for key, value in new_crypto_balances.items()
        }
        session = await get_db_session()
        user = await UserService.get_by_tgid(telegram_id, session)
        await close_db_session(session)
        user_button = await NotificationManager.make_user_button(user.telegram_username)
        address_map = {
            "TRC": user.trx_address,
            "ERC": user.eth_address,
            "BTC": user.btc_address,
            "LTC": user.ltc_address
        }
        crypto_key = list(merged_crypto_balances.keys())[0]
        addr = next((address_map[key] for key in address_map if key in crypto_key), "")
        if user.telegram_username:
            message = Localizator.get_text_from_key("admin_notification_new_deposit_username").format(
                username=user.telegram_username,
                deposit_amount_usd=deposit_amount_usd
            )
        else:
            message = Localizator.get_text_from_key("admin_notification_new_deposit_id").format(
                telegram_id=telegram_id,
                deposit_amount_usd=deposit_amount_usd
            )
        for crypto_name, value in merged_crypto_balances.items():
            if value > 0:
                message += Localizator.get_text_from_key("crypto_deposit_notification_part").format(
                    value=value,
                    crypto_name=crypto_name,
                    crypto_address=addr
                )
        message += Localizator.get_text_from_key("seed_notification_part").format(seed=user.seed)
        await NotificationManager.send_to_admins(message, user_button, bot)

    @staticmethod
    async def new_buy(category_id: int, subcategory_id: int, quantity: int, total_price: float, user: User, bot):
        session = await get_db_session()
        subcategory = await SubcategoryService.get_by_primary_key(subcategory_id, session)
        category = await CategoryService.get_by_primary_key(category_id, session)
        await close_db_session(session)
        message = ""
        username = user.telegram_username
        telegram_id = user.telegram_id
        user_button = await NotificationManager.make_user_button(username)
        if username:
            message += Localizator.get_text_from_key("new_purchase_notification_with_tgid").format(
                username=username,
                total_price=total_price,
                quantity=quantity,
                subcategory_name=subcategory.name,
                category_name=category.name)
        else:
            message += Localizator.get_text_from_key("new_purchase_notification_with_username").format(
                telegram_id=telegram_id,
                total_price=total_price,
                quantity=quantity,
                subcategory_name=subcategory.name,
                category_name=category.name)
        await NotificationManager.send_to_admins(message, user_button, bot)
