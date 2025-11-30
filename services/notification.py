import logging
import traceback
from aiogram import types, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, BufferedInputFile, Message, InputMediaPhoto, InputMediaVideo, \
    InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from config import ADMIN_ID_LIST, TOKEN
from enums.bot_entity import BotEntity
from models.buy import RefundDTO
from models.cartItem import CartItemDTO
from models.payment import ProcessingPaymentDTO, TablePaymentDTO
from models.user import UserDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.localizator import Localizator


class NotificationService:

    @staticmethod
    async def make_user_button(username: str | None) -> InlineKeyboardMarkup:
        user_button_builder = InlineKeyboardBuilder()
        if username:
            user_button_inline = types.InlineKeyboardButton(text=username, url=f"https://t.me/{username}")
            user_button_builder.add(user_button_inline)
        return user_button_builder.as_markup()

    @staticmethod
    async def send_to_admins(message: str | BufferedInputFile, reply_markup: types.InlineKeyboardMarkup | None):
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        for admin_id in ADMIN_ID_LIST:
            try:
                if isinstance(message, str):
                    await bot.send_message(admin_id, f"<b>{message}</b>", reply_markup=reply_markup)
                else:
                    await bot.send_document(admin_id, message, reply_markup=reply_markup)
            except Exception as e:
                logging.error(e)
        await bot.session.close()

    @staticmethod
    async def send_to_user(message: str, telegram_id: int):
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            await bot.send_message(telegram_id, message)
        except Exception as e:
            logging.error(e)
        finally:
            await bot.session.close()

    @staticmethod
    async def edit_message(message: str, source_message_id: int, chat_id: int):
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            await bot.edit_message_text(text=message, chat_id=chat_id, message_id=source_message_id)
        except Exception as e:
            logging.error(e)
        finally:
            await bot.session.close()

    @staticmethod
    async def edit_caption(caption: str, source_message_id: int, chat_id: int):
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            await bot.edit_message_caption(caption=caption, chat_id=chat_id, message_id=source_message_id)
        except Exception as e:
            logging.error(e)
        finally:
            await bot.session.close()

    @staticmethod
    async def payment_expired(user_dto: UserDTO, payment_dto: ProcessingPaymentDTO, table_payment_dto: TablePaymentDTO):
        msg = Localizator.get_text(BotEntity.USER, "notification_payment_expired").format(
            payment_id=payment_dto.id
        )
        edited_payment_message = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(
            crypto_name=payment_dto.cryptoCurrency.name,
            addr="***",
            crypto_amount=payment_dto.cryptoAmount,
            fiat_amount=payment_dto.fiatAmount,
            currency_text=Localizator.get_currency_text(),
            status=Localizator.get_text(BotEntity.USER, "status_expired")
        )
        await NotificationService.edit_caption(edited_payment_message, table_payment_dto.message_id,
                                               user_dto.telegram_id)
        await NotificationService.send_to_user(msg, user_dto.telegram_id)

    @staticmethod
    async def new_deposit(payment_dto: ProcessingPaymentDTO, user_dto: UserDTO, table_payment_dto: TablePaymentDTO):
        user_button = await NotificationService.make_user_button(user_dto.telegram_username)
        user_notification_msg = Localizator.get_text(BotEntity.USER, "notification_new_deposit").format(
            fiat_amount=payment_dto.fiatAmount,
            currency_text=Localizator.get_currency_text(),
            payment_id=payment_dto.id
        )
        await NotificationService.send_to_user(user_notification_msg, user_dto.telegram_id)
        edited_payment_message = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(
            crypto_name=payment_dto.cryptoCurrency.name,
            addr="***",
            crypto_amount=payment_dto.cryptoAmount,
            fiat_amount=payment_dto.fiatAmount,
            currency_text=Localizator.get_currency_text(),
            status=Localizator.get_text(BotEntity.USER, "status_paid")
        )
        await NotificationService.edit_caption(edited_payment_message, table_payment_dto.message_id,
                                               user_dto.telegram_id)
        if user_dto.telegram_username:
            message = Localizator.get_text(BotEntity.ADMIN, "notification_new_deposit_username").format(
                username=user_dto.telegram_username,
                deposit_amount_fiat=payment_dto.fiatAmount,
                currency_sym=Localizator.get_currency_symbol(),
                value=payment_dto.cryptoAmount,
                crypto_name=payment_dto.cryptoCurrency.name
            )
        else:
            message = Localizator.get_text(BotEntity.ADMIN, "notification_new_deposit_id").format(
                telegram_id=user_dto.telegram_id,
                deposit_amount_fiat=payment_dto.fiatAmount,
                currency_sym=Localizator.get_currency_symbol(),
                value=payment_dto.cryptoAmount,
                crypto_name=payment_dto.cryptoCurrency.name
            )
        await NotificationService.send_to_admins(message, user_button)

    @staticmethod
    async def new_buy(sold_items: list[CartItemDTO], user: UserDTO, session: AsyncSession | Session):
        user_button = await NotificationService.make_user_button(user.telegram_username)
        cart_grand_total = 0.0
        message = ""
        for item in sold_items:
            item = await ItemRepository.get_single(subcategory_id=item.subcategory_id,
                                                   category_id=item.category_id,
                                                   session=session)
            category = await CategoryRepository.get_by_id(item.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            cart_item_total = item.price * item.quantity
            cart_grand_total += cart_item_total
            if user.telegram_username:
                message += Localizator.get_text(BotEntity.ADMIN, "notification_purchase_with_tgid").format(
                    username=user.telegram_username,
                    total_price=cart_item_total,
                    quantity=item.quantity,
                    category_name=category.name,
                    subcategory_name=subcategory.name,
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
            else:
                message += Localizator.get_text(BotEntity.ADMIN, "notification_purchase_with_username").format(
                    telegram_id=user.telegram_id,
                    total_price=cart_item_total,
                    quantity=item.quantity,
                    category_name=category.name,
                    subcategory_name=subcategory.name,
                    currency_sym=Localizator.get_currency_symbol()) + "\n"
        message += Localizator.get_text(BotEntity.USER, "cart_grand_total_string").format(
            cart_grand_total=cart_grand_total, currency_sym=Localizator.get_currency_symbol())
        await NotificationService.send_to_admins(message, user_button)

    @staticmethod
    async def refund(refund_data: RefundDTO):
        user_notification = Localizator.get_text(BotEntity.USER, "refund_notification").format(
            total_price=refund_data.total_price,
            quantity=refund_data.quantity,
            subcategory=refund_data.subcategory_name,
            currency_sym=Localizator.get_currency_symbol())
        try:
            bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
            await bot.send_message(refund_data.telegram_id, text=user_notification)
            await bot.session.close()
        except Exception as _:
            pass

    @staticmethod
    async def edit_reply_markup(bot: Bot,
                                chat_id: int,
                                message_id: int,
                                reply_markup: InlineKeyboardMarkup | None = None):
        try:
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
        except Exception as exception:
            traceback_str = traceback.format_exc()
            admin_notification = (
                f"Critical error caused by {exception}\n\n"
                f"Stack trace:\n{traceback_str}"
            )
            logging.error(admin_notification)

    @staticmethod
    async def answer_media(message: Message,
                           media: InputMediaPhoto | InputMediaVideo | InputMediaAnimation,
                           reply_markup: InlineKeyboardMarkup | None = None):
        if isinstance(media, InputMediaPhoto):
            await message.answer_photo(photo=media.media,
                                       caption=media.caption,
                                       reply_markup=reply_markup)
        elif isinstance(media, InputMediaVideo):
            await message.answer_video(video=media.media,
                                       caption=media.caption,
                                       reply_markup=reply_markup)
        else:
            await message.answer_animation(animation=media.media,
                                           caption=media.caption,
                                           reply_markup=reply_markup)
