import datetime
import hashlib
import hmac
import re

from fastapi import APIRouter, Request, HTTPException

import config
from db import get_db_session, session_commit
from models.deposit import DepositDTO
from models.payment import ProcessingPaymentDTO
from repositories.deposit import DepositRepository
from repositories.invoice import InvoiceRepository
from repositories.payment import PaymentRepository
from repositories.user import UserRepository
from services.cart import format_crypto_amount
from services.notification import NotificationService
from services.order import OrderService

processing_router = APIRouter(prefix=f"{config.WEBHOOK_PATH}cryptoprocessing")


def __security_check(x_signature_header: str | None, payload: bytes):
    if x_signature_header is None:
        return True
    else:
        secret_key = config.KRYPTO_EXPRESS_API_SECRET.encode("utf-8")
        hmac_sha512 = hmac.new(secret_key, re.sub(rb'\s+', b'', payload), hashlib.sha512)
        generated_signature = hmac_sha512.hexdigest()
        return hmac.compare_digest(generated_signature, x_signature_header)


@processing_router.post("/event")
async def fetch_crypto_event(payment_dto: ProcessingPaymentDTO, request: Request):
    """
    Webhook endpoint for KryptoExpress payment notifications.
    Handles both DEPOSIT (balance top-ups) and PAYMENT (order payments).
    """
    import logging
    request_body = await request.body()

    # Enhanced logging for webhook events
    logging.info("=" * 80)
    logging.info("🔔 KRYPTOEXPRESS WEBHOOK RECEIVED")
    logging.info(f"Payment ID: {payment_dto.id}")
    logging.info(f"Payment Type: {payment_dto.paymentType}")
    logging.info(f"Is Paid: {payment_dto.isPaid}")
    logging.info(f"Crypto: {payment_dto.cryptoCurrency} | Amount: {format_crypto_amount(payment_dto.cryptoAmount)}")
    logging.info(f"Fiat: {payment_dto.fiatCurrency} | Amount: {payment_dto.fiatAmount}")
    logging.info(f"Raw Body: {request_body.decode('utf-8')}")
    logging.info("=" * 80)

    is_security_pass = __security_check(request.headers.get("X-Signature"), request_body)
    if is_security_pass is False:
        logging.error("❌ WEBHOOK SECURITY CHECK FAILED - Invalid HMAC signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    logging.info("✅ Webhook security check passed")

    async with get_db_session() as session:
        # Check if this is an order PAYMENT (invoice-based) or DEPOSIT (balance top-up)
        invoice = await InvoiceRepository.get_by_payment_processing_id(payment_dto.id, session)

        if invoice:
            logging.info(f"📋 Payment type: ORDER PAYMENT (Invoice {invoice.invoice_number})")
            # This is an order PAYMENT (invoice-based)
            await _handle_order_payment(payment_dto, invoice, session)
        else:
            logging.info(f"💳 Payment type: DEPOSIT (Balance Top-up)")
            # This is a DEPOSIT (balance top-up) - existing logic
            await _handle_deposit_payment(payment_dto, session)

        logging.info("✅ Webhook processing completed successfully")
        logging.info("=" * 80 + "\n")
        return "200"


async def _handle_deposit_payment(payment_dto: ProcessingPaymentDTO, session):
    """Handles DEPOSIT payments (balance top-ups) - existing logic"""
    import logging

    logging.info(f"💰 Processing DEPOSIT payment (ID: {payment_dto.id})")

    user = await PaymentRepository.get_user_by_payment_id(payment_dto.id, session)
    deposit_record = await PaymentRepository.get_by_processing_payment_id(payment_dto.id, session)

    logging.info(f"User: {user.telegram_id} | Deposit already paid: {deposit_record.is_paid}")

    if payment_dto.isPaid is True and deposit_record.is_paid is False:
        logging.info(f"✅ DEPOSIT CONFIRMED: Adding {payment_dto.fiatAmount} {payment_dto.fiatCurrency} to user {user.telegram_id}")
        user.top_up_amount += payment_dto.fiatAmount
        await UserRepository.update(user, session)
        deposit_record.is_paid = True
        await PaymentRepository.update(deposit_record, session)
        await DepositRepository.create(DepositDTO(
            user_id=user.id,
            network=payment_dto.cryptoCurrency,
            amount=int(payment_dto.cryptoAmount*pow(10, payment_dto.cryptoCurrency.get_divider())),
            deposit_datetime=datetime.datetime.now()
        ), session)
        await session_commit(session)
        await NotificationService.new_deposit(payment_dto, user, deposit_record)
    elif payment_dto.isPaid is False:
        await NotificationService.payment_expired(user, payment_dto, deposit_record)


async def _handle_order_payment(payment_dto: ProcessingPaymentDTO, invoice, session):
    """
    Handles PAYMENT (order payments) with full payment validation.

    Validates payment amount and handles:
    - Exact payments
    - Overpayments (minor = forfeit, significant = wallet credit)
    - Underpayments (1st = retry, 2nd = cancel with penalty)
    - Late payments (wallet credit with penalty)
    - Currency mismatches
    """
    import logging
    from repositories.order import OrderRepository
    from enums.order_status import OrderStatus
    from services.payment_validator import PaymentValidator
    from enums.payment_validation import PaymentValidationResult

    logging.info(f"🛒 Processing ORDER PAYMENT (Invoice: {invoice.invoice_number}, Payment ID: {payment_dto.id})")

    # Get order from invoice
    order = await OrderRepository.get_by_id(invoice.order_id, session)

    if not order:
        logging.error(f"❌ ERROR: No order found for invoice {invoice.id}")
        return

    logging.info(f"Order ID: {order.id} | Status: {order.status.value} | Total: {order.total_price} {order.currency.value}")

    # Only process if payment is confirmed
    if payment_dto.isPaid is False:
        logging.warning(f"❌ PAYMENT FAILED/EXPIRED: Order {order.id} (Invoice: {invoice.invoice_number})")
        return

    # Handle late payment (order timed out but payment received)
    if order.status == OrderStatus.TIMEOUT:
        logging.warning(f"⏰ LATE PAYMENT DETECTED: Order {order.id} already timed out")
        # Use late payment handler which applies penalty and credits wallet
        from processing.payment_handlers import _handle_late_payment
        await _handle_late_payment(payment_dto, invoice, order, session)
        return

    # Handle double payment (order already completed successfully)
    if order.status not in [OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING_PAYMENT_PARTIAL]:
        logging.warning(f"⚠️ DUPLICATE PAYMENT DETECTED: Order {order.id} already in status {order.status.value}")

        # Calculate fiat amount from crypto (using invoice exchange rate)
        from processing.payment_handlers import calculate_fiat_from_crypto
        paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)

        # Credit entire payment to wallet
        from repositories.user import UserRepository
        user = await UserRepository.get_by_id(order.user_id, session)
        user.top_up_amount += paid_fiat
        await UserRepository.update(user, session)
        await session_commit(session)

        logging.info(f"💳 DOUBLE PAYMENT: Credited {paid_fiat} {payment_dto.fiatCurrency} to user {user.id} wallet")

        # Notify user
        from services.notification import NotificationService
        await NotificationService.notify_double_payment(user, paid_fiat, invoice.invoice_number)

        return

    # Validate payment amount
    validation_result = PaymentValidator.validate_payment(
        paid=payment_dto.cryptoAmount,
        required=invoice.payment_amount_crypto,
        currency_paid=payment_dto.cryptoCurrency,
        currency_required=invoice.payment_crypto_currency,
        deadline=order.expires_at
    )

    logging.info(f"💳 Payment Validation: {validation_result.value}")
    logging.info(f"   Paid: {format_crypto_amount(payment_dto.cryptoAmount)} {payment_dto.cryptoCurrency.value}")
    logging.info(f"   Required: {format_crypto_amount(invoice.payment_amount_crypto)} {invoice.payment_crypto_currency.value}")
    logging.info(f"   Deadline: {order.expires_at}")

    # Handle validation result
    from processing.payment_handlers import (
        _handle_exact_payment,
        _handle_minor_overpayment,
        _handle_significant_overpayment,
        _handle_underpayment,
        _handle_late_payment,
        _handle_currency_mismatch
    )

    if validation_result == PaymentValidationResult.EXACT_MATCH:
        await _handle_exact_payment(payment_dto, invoice, order, session)

    elif validation_result == PaymentValidationResult.MINOR_OVERPAYMENT:
        await _handle_minor_overpayment(payment_dto, invoice, order, session)

    elif validation_result == PaymentValidationResult.OVERPAYMENT:
        await _handle_significant_overpayment(payment_dto, invoice, order, session)

    elif validation_result == PaymentValidationResult.UNDERPAYMENT:
        await _handle_underpayment(payment_dto, invoice, order, session)

    elif validation_result == PaymentValidationResult.LATE_PAYMENT:
        await _handle_late_payment(payment_dto, invoice, order, session)

    elif validation_result == PaymentValidationResult.CURRENCY_MISMATCH:
        await _handle_currency_mismatch(payment_dto, invoice, order, session)
