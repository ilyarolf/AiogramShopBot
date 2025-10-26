import logging
from aiogram import types, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from config import ADMIN_ID_LIST, TOKEN
from enums.bot_entity import BotEntity
from models.buy import RefundDTO
from models.cartItem import CartItemDTO
from models.item import ItemDTO
from models.payment import ProcessingPaymentDTO, DepositRecordDTO
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
    async def payment_expired(user_dto: UserDTO, payment_dto: ProcessingPaymentDTO, deposit_record: DepositRecordDTO):
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
        await NotificationService.edit_message(edited_payment_message, deposit_record.message_id,
                                               user_dto.telegram_id)
        await NotificationService.send_to_user(msg, user_dto.telegram_id)

    @staticmethod
    async def new_deposit(payment_dto: ProcessingPaymentDTO, user_dto: UserDTO, deposit_record: DepositRecordDTO):
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
        await NotificationService.edit_message(edited_payment_message, deposit_record.message_id,
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
            price = await ItemRepository.get_price(ItemDTO(subcategory_id=item.subcategory_id,
                                                           category_id=item.category_id), session)
            category = await CategoryRepository.get_by_id(item.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            cart_item_total = price * item.quantity
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
    async def payment_underpayment_retry(
        user: UserDTO,
        invoice_number: str,
        paid_crypto: float,
        required_crypto: float,
        remaining_crypto: float,
        crypto_currency,
        new_invoice_number: str,
        new_payment_address: str,
        new_expires_at
    ):
        """
        Notifies user about underpayment and provides new invoice for remaining amount.

        Called after first underpayment - gives user 30 more minutes to pay remaining amount.
        """
        msg = Localizator.get_text(BotEntity.USER, "payment_underpayment_retry").format(
            invoice_number=invoice_number,
            paid_crypto=paid_crypto,
            crypto_currency=crypto_currency.value,
            required_crypto=required_crypto,
            remaining_crypto=remaining_crypto,
            new_invoice_number=new_invoice_number,
            new_payment_address=new_payment_address,
            new_expires_at=new_expires_at.strftime('%d.%m.%Y %H:%M')
        )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def payment_cancelled_underpayment(
        user: UserDTO,
        invoice_number: str,
        total_paid_fiat: float,
        penalty_amount: float,
        net_wallet_credit: float,
        currency_sym: str
    ):
        """
        Notifies user about order cancellation due to second underpayment.

        Informs about 5% penalty and wallet credit.
        """
        msg = Localizator.get_text(BotEntity.USER, "payment_cancelled_underpayment").format(
            invoice_number=invoice_number,
            total_paid_fiat=f"{total_paid_fiat:.2f}",
            penalty_amount=f"{penalty_amount:.2f}",
            net_wallet_credit=f"{net_wallet_credit:.2f}",
            currency_sym=currency_sym
        )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def payment_late(
        user: UserDTO,
        invoice_number: str,
        paid_fiat: float,
        penalty_amount: float,
        net_wallet_credit: float,
        currency_sym: str
    ):
        """
        Notifies user about late payment.

        Payment received after deadline - 5% penalty applied, wallet credited.
        """
        msg = Localizator.get_text(BotEntity.USER, "payment_late").format(
            invoice_number=invoice_number,
            paid_fiat=f"{paid_fiat:.2f}",
            penalty_amount=f"{penalty_amount:.2f}",
            net_wallet_credit=f"{net_wallet_credit:.2f}",
            currency_sym=currency_sym
        )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def payment_overpayment_wallet_credit(
        user: UserDTO,
        invoice_number: str,
        overpayment_amount: float,
        currency_sym: str
    ):
        """
        Notifies user about overpayment credited to wallet.

        Significant overpayment (>0.1%) - excess credited to wallet.
        """
        msg = Localizator.get_text(BotEntity.USER, "payment_overpayment_wallet_credit").format(
            invoice_number=invoice_number,
            overpayment_amount=f"{overpayment_amount:.2f}",
            currency_sym=currency_sym
        )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def payment_success(
        user: UserDTO,
        invoice_number: str
    ):
        """
        Notifies user about successful payment (exact or minor overpayment).
        """
        msg = Localizator.get_text(BotEntity.USER, "payment_success").format(
            invoice_number=invoice_number
        )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def notify_double_payment(
        user: UserDTO,
        amount: float,
        invoice_number: str
    ):
        """
        Notifies user about double payment (payment for already completed order).
        Entire amount credited to wallet.
        """
        msg = (
            f"⚠️ <b>Double Payment Detected</b>\n\n"
            f"We received a duplicate payment for order-id {invoice_number}.\n\n"
            f"💰 <b>Amount credited to wallet:</b> {amount:.2f} {Localizator.get_currency_symbol()}\n\n"
            f"Your order was already completed. The payment has been fully credited to your wallet balance."
        )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def notify_order_cancelled_wallet_refund(
        user: UserDTO,
        invoice_number: str,
        refund_info: dict,
        currency_sym: str
    ):
        """
        Notifies user about order cancellation and wallet refund.
        Shows processing fee if applicable.
        """
        original_amount = refund_info['original_amount']
        penalty_amount = refund_info['penalty_amount']
        refund_amount = refund_info['refund_amount']
        penalty_percent = refund_info['penalty_percent']

        if penalty_amount > 0:
            # Cancellation with processing fee and strike
            reason = refund_info.get('reason', 'UNKNOWN')

            # Build reason-specific explanation
            if 'TIMEOUT' in reason.upper():
                reason_text = (
                    f"⏱️ <b>Grund:</b> Ihre Reservierungszeit ist abgelaufen.\n\n"
                    f"Während der Reservierungszeit konnten andere Kunden diese Artikel nicht kaufen. "
                    f"Daher wird eine Bearbeitungsgebühr fällig."
                )
            elif 'reservation_fee' in reason.lower():
                reason_text = (
                    f"⏱️ <b>Grund:</b> Stornierung nach Ablauf der Kulanzfrist.\n\n"
                    f"Ihre Artikel waren reserviert und konnten von anderen Kunden nicht gekauft werden. "
                    f"Daher wird eine Reservierungsgebühr fällig."
                )
            else:
                reason_text = (
                    f"⚠️ <b>Grund:</b> Stornierung nach Ablauf der Kulanzfrist.\n\n"
                    f"Eine Bearbeitungsgebühr wird fällig, da die kostenlose Stornierungsfrist bereits abgelaufen war."
                )

            # Build wallet details section
            if original_amount > 0:
                wallet_section = (
                    f"💰 <b>Guthaben-Rückerstattung:</b>\n"
                    f"• Verwendetes Guthaben: {original_amount:.2f} {currency_sym}\n"
                    f"• Bearbeitungsgebühr ({penalty_percent}%): -{penalty_amount:.2f} {currency_sym}\n"
                    f"• <b>Zurückerstattet: {refund_amount:.2f} {currency_sym}</b>"
                )
            else:
                wallet_section = (
                    f"💸 <b>Reservierungsgebühr:</b>\n"
                    f"• Bestellwert: {refund_info.get('base_amount', 0):.2f} {currency_sym}\n"
                    f"• Gebühr ({penalty_percent}%): -{penalty_amount:.2f} {currency_sym}\n"
                    f"• <b>Von Ihrem Guthaben abgezogen</b>"
                )

            msg = (
                f"❌ <b>Bestellung storniert</b>\n\n"
                f"📋 Bestellnummer: {invoice_number}\n\n"
                f"{reason_text}\n\n"
                f"{wallet_section}\n\n"
                f"⚠️ <b>Strike erhalten</b> - Diese Stornierung führte zu einem Strike auf Ihrem Konto.\n\n"
                f"ℹ️ Weitere Informationen finden Sie in unseren AGB."
            )
        else:
            # Full refund (no fee)
            msg = (
                f"🔔 <b>Order Cancelled</b>\n\n"
                f"Order-id {invoice_number} has been cancelled.\n\n"
                f"💰 <b>Full wallet refund:</b> {refund_amount:.2f} {currency_sym}\n\n"
                f"Your wallet balance has been fully restored."
            )

        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def order_shipped(user_id: int, invoice_number: str, session: AsyncSession | Session):
        """
        Sends notification to user when their order has been marked as shipped.
        """
        from repositories.user import UserRepository

        user = await UserRepository.get_by_id(user_id, session)
        msg = Localizator.get_text(BotEntity.USER, "order_shipped_notification").format(
            invoice_number=invoice_number
        )
        await NotificationService.send_to_user(msg, user.telegram_id)

    @staticmethod
    async def order_awaiting_shipment(user_id: int, invoice_number: str, session: AsyncSession | Session):
        """
        Sends notification to admins when a new order with physical items is awaiting shipment.
        """
        from repositories.user import UserRepository

        user = await UserRepository.get_by_id(user_id, session)
        username = f"@{user.telegram_username}" if user.telegram_username else f"ID:{user.telegram_id}"

        msg = Localizator.get_text(BotEntity.ADMIN, "order_awaiting_shipment_notification").format(
            invoice_number=invoice_number,
            username=username
        )
        await NotificationService.send_to_admins(msg, None)
