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
    logging.info(f"Crypto: {payment_dto.cryptoCurrency} | Amount: {payment_dto.cryptoAmount}")
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
    """Handles PAYMENT (order payments) - new logic for invoice-based system"""
    import logging
    from repositories.order import OrderRepository
    from enums.order_status import OrderStatus

    logging.info(f"🛒 Processing ORDER PAYMENT (Invoice: {invoice.invoice_number}, Payment ID: {payment_dto.id})")

    # Get order from invoice
    order = await OrderRepository.get_by_id(invoice.order_id, session)

    if not order:
        logging.error(f"❌ ERROR: No order found for invoice {invoice.id}")
        return

    logging.info(f"Order ID: {order.id} | Status: {order.status.value} | Total: {order.total_price} {order.currency.value}")

    # Only process if payment is confirmed and order is still pending
    if payment_dto.isPaid is True and order.status == OrderStatus.PENDING_PAYMENT:
        logging.info(f"✅ PAYMENT CONFIRMED: Completing order {order.id}")

        # Complete order payment (marks items as sold, updates order status to PAID)
        await OrderService.complete_order_payment(invoice.order_id, session)

        logging.info(f"🎉 SUCCESS: Order {order.id} marked as PAID (Invoice: {invoice.invoice_number})")
        # TODO: Send notification to user about successful payment

    elif payment_dto.isPaid is True and order.status != OrderStatus.PENDING_PAYMENT:
        logging.warning(f"⚠️ DUPLICATE/LATE PAYMENT: Order {order.id} already in status {order.status.value}")

    elif payment_dto.isPaid is False:
        # Payment expired or failed - order will be cancelled by timeout job
        logging.warning(f"❌ PAYMENT FAILED/EXPIRED: Order {order.id} (Invoice: {invoice.invoice_number})")
