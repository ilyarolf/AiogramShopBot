import logging
from aiogram import types, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID_LIST, TOKEN
from enums.cryptocurrency import Cryptocurrency
from models.user import UserDTO
from utils.localizator import Localizator, BotEntity


class NotifcationService:

    @staticmethod
    async def make_user_button(username: str | None):
        user_button_builder = InlineKeyboardBuilder()
        if username:
            user_button_inline = types.InlineKeyboardButton(text=username, url=f"https://t.me/{username}")
            user_button_builder.add(user_button_inline)
        return user_button_builder.as_markup()

    @staticmethod
    async def send_to_admins(message: str, reply_markup: types.InlineKeyboardMarkup):
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        for admin_id in ADMIN_ID_LIST:
            try:
                await bot.send_message(admin_id, f"<b>{message}</b>", reply_markup=reply_markup)
            except Exception as e:
                logging.error(e)

    @staticmethod
    async def new_deposit(deposit_amount: float, cryptocurrency: Cryptocurrency, fiat_amount: float, user_dto: UserDTO):
        deposit_amount_fiat = round(fiat_amount, 2)
        user_button = await NotifcationService.make_user_button(user_dto.telegram_username)
        if user_dto.telegram_username:
            message = Localizator.get_text(BotEntity.ADMIN, "notification_new_deposit_username").format(
                username=user_dto.telegram_username,
                deposit_amount_fiat=deposit_amount_fiat,
                currency_sym=Localizator.get_currency_symbol()
            )
        else:
            message = Localizator.get_text(BotEntity.ADMIN, "notification_new_deposit_id").format(
                telegram_id=user_dto.telegram_id,
                deposit_amount_fiat=deposit_amount_fiat,
                currency_sym=Localizator.get_currency_symbol()
            )
        addr = getattr(user_dto, cryptocurrency.get_address_field())
        message += Localizator.get_text(BotEntity.ADMIN, "notification_crypto_deposit").format(
            value=deposit_amount,
            crypto_name=cryptocurrency.value.replace('_', ' '),
            crypto_address=addr
        )
        message += Localizator.get_text(BotEntity.ADMIN, "notification_seed").format(seed=user_dto.seed)
        await NotifcationService.send_to_admins(message, user_button)