import logging
import traceback
from datetime import datetime, timezone
from aiogram import types, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, BufferedInputFile, Message, InputMediaPhoto, InputMediaVideo, \
    InputMediaAnimation, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import config
from callbacks import MyProfileCallback, ReviewManagementCallback
from config import ADMIN_ID_LIST, TOKEN
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from enums.user_role import UserRole
from models.buy import RefundDTO, BuyDTO
from models.payment import ProcessingPaymentDTO, TablePaymentDTO
from models.referral import ReferralBonusDTO
from models.review import ReviewDTO
from models.user import UserDTO
from models.withdrawal import WithdrawalDTO
from services.multibot import MultibotService
from utils.telegram import create_bot
from repositories.buyItem import BuyItemRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.utils import get_text


class NotificationService:
    PRIVACY_RESTRICTED_PATTERN = "BUTTON_USER_PRIVACY_RESTRICTED"
    TG_USER_URL_PREFIX = "tg://user?id="

    @staticmethod
    def get_username_link(user_dto: UserDTO) -> str | None:
        if user_dto.telegram_username:
            return f"https://t.me/{user_dto.telegram_username}"
        return None

    @staticmethod
    async def get_preferred_user_link(user_dto: UserDTO) -> str | None:
        if user_dto.telegram_id is None:
            return NotificationService.get_username_link(user_dto)
        bot = create_bot(TOKEN)
        try:
            chat = await bot.get_chat(user_dto.telegram_id)
            if chat.has_private_forwards is not True:
                return f"{NotificationService.TG_USER_URL_PREFIX}{user_dto.telegram_id}"
        except Exception as exception:
            logging.warning(
                "Could not inspect chat privacy settings for telegram_id=%s: %s",
                user_dto.telegram_id,
                exception
            )
        finally:
            await bot.session.close()
        return NotificationService.get_username_link(user_dto)

    @staticmethod
    async def add_user_button(kb_builder: InlineKeyboardBuilder, user_dto: UserDTO, text: str | None = None) -> bool:
        user_link = await NotificationService.get_preferred_user_link(user_dto)
        if user_link is None:
            return False
        kb_builder.button(
            text=text or get_text(Language.EN, BotEntity.COMMON, "user"),
            url=user_link
        )
        return True

    @staticmethod
    def _is_privacy_restricted_error(exception: Exception) -> bool:
        return isinstance(exception, TelegramBadRequest) and NotificationService.PRIVACY_RESTRICTED_PATTERN in str(
            exception
        )

    @staticmethod
    def _strip_privacy_restricted_buttons(
            reply_markup: InlineKeyboardMarkup | None
    ) -> InlineKeyboardMarkup | None:
        if reply_markup is None:
            return None
        filtered_rows: list[list[InlineKeyboardButton]] = []
        for row in reply_markup.inline_keyboard:
            filtered_row = []
            for button in row:
                if button.url and button.url.startswith(NotificationService.TG_USER_URL_PREFIX):
                    continue
                filtered_row.append(button)
            if filtered_row:
                filtered_rows.append(filtered_row)
        if not filtered_rows:
            return None
        return InlineKeyboardMarkup(inline_keyboard=filtered_rows)

    @staticmethod
    async def _execute_with_privacy_fallback(operation_name: str,
                                             execute,
                                             reply_markup: InlineKeyboardMarkup | None,
                                             chat_id: int | None = None):
        try:
            return await execute(reply_markup)
        except Exception as exception:
            if not NotificationService._is_privacy_restricted_error(exception):
                raise
            sanitized_markup = NotificationService._strip_privacy_restricted_buttons(reply_markup)
            logging.warning(
                "Privacy-restricted markup fallback triggered during %s for chat_id=%s",
                operation_name,
                chat_id
            )
            return await execute(sanitized_markup)

    @staticmethod
    async def make_user_button(user_dto: UserDTO) -> InlineKeyboardMarkup | None:
        kb_builder = InlineKeyboardBuilder()
        await NotificationService.add_user_button(kb_builder, user_dto)
        return kb_builder.as_markup() if list(kb_builder.buttons) else None

    @staticmethod
    async def send_to_admins(message: str | BufferedInputFile, reply_markup: types.InlineKeyboardMarkup | None):
        bot = create_bot(TOKEN)
        for admin_id in ADMIN_ID_LIST:
            try:
                if isinstance(message, str):
                    async def _send(current_markup):
                        return await bot.send_message(admin_id, f"<b>{message}</b>", reply_markup=current_markup)
                else:
                    async def _send(current_markup):
                        return await bot.send_document(admin_id, message, reply_markup=current_markup)
                await NotificationService._execute_with_privacy_fallback(
                    operation_name="send_to_admins",
                    execute=_send,
                    reply_markup=reply_markup,
                    chat_id=admin_id
                )
            except Exception as e:
                logging.error(e)
        await bot.session.close()

    @staticmethod
    async def send_to_user(message: str, telegram_id: int, reply_markup: types.InlineKeyboardMarkup | None = None):
        if config.MULTIBOT:
            await MultibotService.send_message_to_user(message, telegram_id, reply_markup=reply_markup)
            return
        bot = create_bot(TOKEN)
        try:
            await bot.send_message(telegram_id, message, reply_markup=reply_markup)
        except Exception as e:
            logging.error(e)
        finally:
            await bot.session.close()

    @staticmethod
    async def edit_message(message: str, source_message_id: int, chat_id: int):
        bot = create_bot(TOKEN)
        try:
            await bot.edit_message_text(text=message, chat_id=chat_id, message_id=source_message_id)
        except Exception as e:
            logging.error(e)
        finally:
            await bot.session.close()

    @staticmethod
    async def edit_caption(caption: str, source_message_id: int, chat_id: int):
        bot = create_bot(TOKEN)
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
            admin_kb_builder = InlineKeyboardBuilder()
            if admin_kb_markup:
                admin_kb_builder = InlineKeyboardBuilder().from_markup(admin_kb_markup)
            await NotificationService.add_user_button(
                admin_kb_builder,
                referral_bonus_dto.referrer_user_dto,
                text=get_text(Language.EN, BotEntity.COMMON, "referrer")
            )
            admin_kb_builder.adjust(1)
            admin_kb_markup = admin_kb_builder.as_markup() if list(admin_kb_builder.buttons) else None
            await NotificationService.send_to_user(referrer_notification_msg,
                                                   referral_bonus_dto.referrer_user_dto.telegram_id)
        msg_template = "top_up_balance_payment_msg" if payment_dto.cryptoCurrency in Cryptocurrency.get_stablecoins() else "top_up_balance_deposit_msg"
        timestamp_s = payment_dto.expireDatetime / 1000
        dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
        formatted = dt.strftime('%H:%M UTC on %B %d, %Y')
        edited_payment_message = get_text(user_dto.language, BotEntity.USER, msg_template).format(
            crypto_name=payment_dto.cryptoCurrency.name,
            addr="***",
            crypto_amount=payment_dto.cryptoAmount,
            fiat_amount=payment_dto.fiatAmount,
            currency_text=currency_text,
            status=get_text(user_dto.language, BotEntity.USER, "status_paid"),
            payment_lifetime=formatted
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
        admin_kb_markup = await NotificationService.make_user_button(user)
        admin_kb_builder = InlineKeyboardBuilder()
        if admin_kb_markup:
            admin_kb_builder = InlineKeyboardBuilder.from_markup(admin_kb_markup)
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
        item_map = await ItemRepository.get_by_id_map(
            [buy_item.item_ids[0] for buy_item in buyItem_list if buy_item.item_ids],
            session
        )
        category_map = {
            category.id: category
            for category in await CategoryRepository.get_by_ids(
                [item.category_id for item in item_map.values()],
                session
            )
        }
        subcategory_map = {
            subcategory.id: subcategory
            for subcategory in await SubcategoryRepository.get_by_ids(
                [item.subcategory_id for item in item_map.values()],
                session
            )
        }
        currency_sym = config.CURRENCY.get_localized_symbol()
        for buyItem in buyItem_list:
            item_example = item_map[buyItem.item_ids[0]]
            category = category_map[item_example.category_id]
            subcategory = subcategory_map[item_example.subcategory_id]
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
            async def _answer(current_markup):
                return await message.answer_photo(photo=media.media,
                                                  caption=media.caption,
                                                  reply_markup=current_markup)
        elif isinstance(media, InputMediaVideo):
            async def _answer(current_markup):
                return await message.answer_video(video=media.media,
                                                  caption=media.caption,
                                                  reply_markup=current_markup)
        else:
            async def _answer(current_markup):
                return await message.answer_animation(animation=media.media,
                                                      caption=media.caption,
                                                      reply_markup=current_markup)
        return await NotificationService._execute_with_privacy_fallback(
            operation_name="answer_media",
            execute=_answer,
            reply_markup=reply_markup,
            chat_id=message.chat.id
        )

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
        item_map = await ItemRepository.get_by_id_map([buyItem_dto.item_ids[0]], session)
        item_dto = item_map[buyItem_dto.item_ids[0]]
        subcategory_map = {
            subcategory.id: subcategory
            for subcategory in await SubcategoryRepository.get_by_ids([item_dto.subcategory_id], session)
        }
        subcategory_dto = subcategory_map[item_dto.subcategory_id]
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
