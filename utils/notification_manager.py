import logging
from typing import List
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.cartItem import CartItem
from services.item import ItemService
from services.subcategory import SubcategoryService
from services.category import CategoryService
from services.user import UserService
from config import ADMIN_ID_LIST
from models.user import User
from utils.localizator import Localizator, BotEntity
from utils.other_sql import RefundBuyDTO


class NotificationManager:
    @staticmethod
    async def send_refund_message(refund_data: RefundBuyDTO, bot):
        message = Localizator.get_text(BotEntity.USER, "refund_notification").format(
            total_price=refund_data.total_price,
            quantity=refund_data.quantity,
            subcategory=refund_data.subcategory,
            currency_sym=Localizator.get_currency_symbol())
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
    async def make_user_button(username: str | None):
        user_button_builder = InlineKeyboardBuilder()
        if username:
            user_button_inline = types.InlineKeyboardButton(text=username, url=f"https://t.me/{username}")
            user_button_builder.add(user_button_inline)
        return user_button_builder.as_markup()

    @staticmethod
    async def new_deposit(new_crypto_balances: dict, deposit_amount_fiat, telegram_id: int, bot):
        deposit_amount_fiat = round(deposit_amount_fiat, 2)
        merged_crypto_balances = {
            key.replace('_deposit', "").replace('_', ' ').upper(): value
            for key, value in new_crypto_balances.items()
        }
        user = await UserService.get_by_tgid(telegram_id)
        user_button = await NotificationManager.make_user_button(user.telegram_username)
        address_map = {
            "TRC": user.trx_address,
            "ERC": user.eth_address,
            "BTC": user.btc_address,
            "LTC": user.ltc_address,
            "SOL": user.sol_address
        }
        crypto_key = list(merged_crypto_balances.keys())[0]
        addr = next((address_map[key] for key in address_map if key in crypto_key), "")
        if user.telegram_username:
            message = Localizator.get_text(BotEntity.ADMIN, "notification_new_deposit_username").format(
                username=user.telegram_username,
                deposit_amount_fiat=deposit_amount_fiat,
                currency_sym=Localizator.get_currency_symbol()
            )
        else:
            message = Localizator.get_text(BotEntity.ADMIN, "notification_new_deposit_id").format(
                telegram_id=telegram_id,
                deposit_amount_fiat=deposit_amount_fiat,
                currency_sym=Localizator.get_currency_symbol()
            )
        for crypto_name, value in merged_crypto_balances.items():
            if value > 0:
                message += Localizator.get_text(BotEntity.ADMIN, "notification_crypto_deposit").format(
                    value=value,
                    crypto_name=crypto_name,
                    crypto_address=addr
                )
        message += Localizator.get_text(BotEntity.ADMIN, "notification_seed").format(seed=user.seed)
        await NotificationManager.send_to_admins(message, user_button, bot)

    @staticmethod
    async def new_buy(sold_cart_items: List[CartItem], user: User, bot):
        username = user.telegram_username
        telegram_id = user.telegram_id
        user_button = await NotificationManager.make_user_button(username)
        cart_grand_total = 0.0
        message = ""
        line_max_width = 0

        for cart_item in sold_cart_items:
            price = await ItemService.get_price_by_subcategory(cart_item.subcategory_id, cart_item.category_id)
            category = await CategoryService.get_by_primary_key(cart_item.category_id)
            subcategory = await SubcategoryService.get_by_primary_key(cart_item.subcategory_id)
            line_max_width = max(line_max_width, len(str(subcategory)))
            cart_item_total = price * cart_item.quantity
            cart_grand_total += cart_item_total

            if username:
                message += Localizator.get_text(BotEntity.ADMIN, "notification_purchase_with_tgid").format(
                    username=username,
                    total_price=cart_item_total,
                    quantity=cart_item.quantity,
                    category_name=category.name,
                    subcategory_name=subcategory.name,
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
            else:
                message += Localizator.get_text(BotEntity.ADMIN, "notification_purchase_with_username").format(
                    telegram_id=telegram_id,
                    total_price=cart_item_total,
                    quantity=cart_item.quantity,
                    category_name=category.name,
                    subcategory_name=subcategory.name,
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
        message += Localizator.get_text(BotEntity.USER, "cart_grand_total_string").format(
            cart_grand_total=cart_grand_total, currency_sym=Localizator.get_currency_symbol())
        await NotificationManager.send_to_admins(message, user_button, bot)
