import logging
import traceback
from datetime import datetime, timezone
from aiogram import types, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, BufferedInputFile, Message, InputMediaPhoto, InputMediaVideo, \
    InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import config
from callbacks import MyProfileCallback, ReviewManagementCallback
from config import ADMIN_ID_LIST, TOKEN
from enums.bot_entity import BotEntity
from enums.language import Language
from enums.user_role import UserRole
from models.buy import RefundDTO, BuyDTO
from models.payment import ProcessingPaymentDTO, TablePaymentDTO
from models.referral import ReferralBonusDTO
from models.review import ReviewDTO
from models.user import UserDTO
from models.withdrawal import WithdrawalDTO
from repositories.buyItem import BuyItemRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.utils import get_text


class NotificationService:

    @staticmethod
    async def make_user_button(user_dto: UserDTO) -> InlineKeyboardMarkup:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(Language.EN, BotEntity.COMMON, "user"),
            url=f"tg://user?id={user_dto.telegram_id}"
        )
        return kb_builder.as_markup()

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
    async def send_to_user(message: str, telegram_id: int, reply_markup: types.InlineKeyboardMarkup | None = None):
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        try:
            await bot.send_message(telegram_id, message, reply_markup=reply_markup)
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
        msg = get_text(user_dto.language, BotEntity.USER, "notification_payment_expired").format(
            payment_id=payment_dto.id
        )
        template = f"top_up_balance_{payment_dto.paymentType.name.lower()}_msg"
        timestamp_s = payment_dto.expireDatetime / 1000
        dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
        formatted = dt.strftime('%H:%M UTC on %B %d, %Y')
        edited_payment_message = get_text(user_dto.language, BotEntity.USER, template).format(
            crypto_name=payment_dto.cryptoCurrency.name,
            addr="***",
            crypto_amount=payment_dto.cryptoAmount,
            fiat_amount=payment_dto.fiatAmount,
            currency_text=config.CURRENCY.get_localized_text(),
            status=get_text(user_dto.language, BotEntity.USER, "status_expired"),
            payment_lifetime=formatted
        )
        await NotificationService.edit_caption(edited_payment_message, table_payment_dto.message_id,
                                               user_dto.telegram_id)
        await NotificationService.send_to_user(msg, user_dto.telegram_id)

    @staticmethod
    async def new_deposit(payment_dto: ProcessingPaymentDTO,
                          user_dto: UserDTO,
                          table_payment_dto: TablePaymentDTO,
                          referral_bonus_dto: ReferralBonusDTO):
        admin_kb_markup = await NotificationService.make_user_button(user_dto)
        currency_text = config.CURRENCY.get_localized_text()
        currency_sym = config.CURRENCY.get_localized_symbol()
        user_notification_msg = get_text(user_dto.language, BotEntity.USER, "notification_new_deposit").format(
            fiat_amount=payment_dto.fiatAmount,
            currency_text=currency_text,
            payment_id=payment_dto.id,
            referral_bonus=referral_bonus_dto.applied_referral_bonus,
        )
        await NotificationService.send_to_user(user_notification_msg, user_dto.telegram_id)
        if referral_bonus_dto.referrer_user_dto:
            referrer_notification_msg = get_text(Language.EN, BotEntity.USER, "referrer_notification").format(
                currency_sym=currency_sym,
                referrer_bonus=referral_bonus_dto.applied_referrer_bonus
            )
            admin_kb_markup = InlineKeyboardBuilder().from_markup(admin_kb_markup)
            admin_kb_markup.button(
                text=get_text(Language.EN, BotEntity.COMMON, "referrer"),
                url=f"tg://user?id={referral_bonus_dto.referrer_user_dto.telegram_id}"
            )
            admin_kb_markup.adjust(1)
            admin_kb_markup = admin_kb_markup.as_markup()
            await NotificationService.send_to_user(referrer_notification_msg,
                                                   referral_bonus_dto.referrer_user_dto.telegram_id)
        edited_payment_message = get_text(user_dto.language, BotEntity.USER, "top_up_balance_msg").format(
            crypto_name=payment_dto.cryptoCurrency.name,
            addr="***",
            crypto_amount=payment_dto.cryptoAmount,
            fiat_amount=payment_dto.fiatAmount,
            currency_text=currency_text,
            status=get_text(user_dto.language, BotEntity.USER, "status_paid")
        )
        await NotificationService.edit_caption(edited_payment_message, table_payment_dto.message_id,
                                               user_dto.telegram_id)
        if user_dto.telegram_username:
            message = get_text(Language.EN, BotEntity.ADMIN, "notification_new_deposit_username")
        else:
            message = get_text(Language.EN, BotEntity.ADMIN, "notification_new_deposit_id")
        message = message.format(
            username=user_dto.telegram_username,
            telegram_id=user_dto.telegram_id,
            deposit_amount_fiat=payment_dto.fiatAmount,
            currency_sym=currency_sym,
            value=payment_dto.cryptoAmount,
            crypto_name=payment_dto.cryptoCurrency.name,
            referral_bonus=referral_bonus_dto.applied_referral_bonus,
            referrer_bonus=referral_bonus_dto.applied_referrer_bonus
        )
        await NotificationService.send_to_admins(message, admin_kb_markup)

    @staticmethod
    async def new_buy(buy: BuyDTO, user: UserDTO, session: AsyncSession | Session):
        admin_kb_builder = await NotificationService.make_user_button(user)
        admin_kb_builder = InlineKeyboardBuilder.from_markup(admin_kb_builder)
        admin_kb_builder.button(
            text=get_text(Language.EN, BotEntity.USER, "purchase_history_item").format(
                buy_id=buy.id,
                total_price=buy.total_price,
                currency_sym=config.CURRENCY.get_localized_symbol()
            ),
            callback_data=MyProfileCallback.create(level=4,
                                                   buy_id=buy.id,
                                                   user_role=UserRole.ADMIN)
        )
        admin_kb_builder.adjust(1)
        cart_content = []
        buyItem_list = await BuyItemRepository.get_all_by_buy_id(buy.id, session)
        currency_sym = config.CURRENCY.get_localized_symbol()
        for buyItem in buyItem_list:
            item_example = await ItemRepository.get_by_id(buyItem.item_ids[0], session)
            category = await CategoryRepository.get_by_id(item_example.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item_example.subcategory_id, session)
            if user.telegram_username:
                msg = get_text(Language.EN, BotEntity.ADMIN, "notification_purchase_with_username")
            else:
                msg = get_text(Language.EN, BotEntity.ADMIN, "notification_purchase_with_tgid")
            cart_content.append(msg.format(
                username=user.telegram_username,
                telegram_id=user.telegram_id,
                total_price=item_example.price * len(buyItem.item_ids),
                quantity=len(buyItem.item_ids),
                category_name=category.name,
                subcategory_name=subcategory.name,
                currency_sym=currency_sym))
        message = "\n".join(cart_content) + "\n\n"
        price_content = []
        price_content.append(get_text(Language.EN, BotEntity.USER, "cart_total_price").format(
            cart_total_price=buy.total_price + buy.discount, currency_sym=currency_sym))
        price_content.append(get_text(Language.EN, BotEntity.USER, "cart_total_discount").format(
            cart_total_discount=buy.discount, currency_sym=currency_sym))
        price_content.append(get_text(Language.EN, BotEntity.USER, "cart_total_with_discount").format(
            cart_total_final=buy.total_price, currency_sym=currency_sym))
        message += "\n".join(price_content)
        await NotificationService.send_to_admins(message, admin_kb_builder.as_markup())

    @staticmethod
    async def refund(refund_data: RefundDTO):
        user_notification = get_text(refund_data.language, BotEntity.USER, "refund_notification").format(
            total_price=refund_data.total_price,
            quantity=len(refund_data.item_ids),
            subcategory=refund_data.subcategory_name,
            currency_sym=config.CURRENCY.get_localized_symbol())
        await NotificationService.send_to_user(user_notification, refund_data.telegram_id)

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
                           reply_markup: InlineKeyboardMarkup | None = None) -> Message:
        if isinstance(media, InputMediaPhoto):
            message = await message.answer_photo(photo=media.media,
                                                 caption=media.caption,
                                                 reply_markup=reply_markup)
        elif isinstance(media, InputMediaVideo):
            message = await message.answer_video(video=media.media,
                                                 caption=media.caption,
                                                 reply_markup=reply_markup)
        else:
            message = await message.answer_animation(animation=media.media,
                                                     caption=media.caption,
                                                     reply_markup=reply_markup)
        return message

    @staticmethod
    async def withdrawal(withdraw_dto: WithdrawalDTO):
        kb_builder = InlineKeyboardBuilder()
        [kb_builder.button(text=get_text(Language.EN, BotEntity.ADMIN, "transaction"),
                           url=f"{withdraw_dto.cryptoCurrency.get_explorer_base_url()}/tx/{tx_id}")
         for tx_id in withdraw_dto.txIdList]
        msg_text = get_text(Language.EN, BotEntity.ADMIN, "transaction_broadcasted")
        kb_builder.adjust(1)
        await NotificationService.send_to_admins(msg_text, kb_builder.as_markup())

    @staticmethod
    async def new_review_published(review_dto: ReviewDTO, session: AsyncSession):
        kb_builder = InlineKeyboardBuilder()
        buyItem_dto = await BuyItemRepository.get_by_id(review_dto.buyItem_id, session)
        item_dto = await ItemRepository.get_by_id(buyItem_dto.item_ids[0], session)
        subcategory_dto = await SubcategoryRepository.get_by_id(item_dto.subcategory_id, session)
        kb_builder.button(
            text=get_text(Language.EN, BotEntity.USER, "review").format(
                subcategory_name=subcategory_dto.name
            ),
            callback_data=ReviewManagementCallback.create(
                level=6,
                review_id=review_dto.id,
                buy_id=buyItem_dto.buy_id,
                buyItem_id=review_dto.buyItem_id,
                user_role=UserRole.ADMIN
            )
        )
        msg_text = get_text(Language.EN, BotEntity.ADMIN, "review_notification")
        await NotificationService.send_to_admins(msg_text, kb_builder.as_markup())
