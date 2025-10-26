"""
Payment Handler Functions

Individual handlers for each payment validation result:
- Exact payment
- Minor overpayment (forfeits to shop)
- Significant overpayment (wallet credit)
- Underpayment (1st = retry, 2nd = cancel with penalty)
- Late payment (wallet credit with penalty)
- Currency mismatch
"""

import logging
from datetime import datetime, timedelta

import config
from db import session_commit
from enums.order_status import OrderStatus
from models.payment_transaction import PaymentTransactionDTO
from repositories.order import OrderRepository
from repositories.payment_transaction import PaymentTransactionRepository
from repositories.user import UserRepository
from services.cart import format_crypto_amount
from services.order import OrderService
from services.payment_validator import PaymentValidator
from services.notification import NotificationService


def calculate_fiat_from_crypto(crypto_amount: float, invoice) -> float:
    """
    Calculate fiat amount from crypto amount using invoice exchange rate.

    This ensures consistency with the original invoice exchange rate,
    preventing divergence due to market fluctuations.

    Args:
        crypto_amount: Actual crypto amount paid
        invoice: Invoice with original exchange rate

    Returns:
        Calculated fiat amount based on invoice rate
    """
    exchange_rate = invoice.fiat_amount / invoice.payment_amount_crypto
    return crypto_amount * exchange_rate


async def _handle_exact_payment(payment_dto, invoice, order, session):
    """
    Handle exact payment (including minor overpayment ≤0.1% tolerance).

    Action:
    - Complete order normally
    - Mark items as sold
    - Update order status to PAID
    - Create PaymentTransaction record
    - Notify user
    """
    logging.info(f"✅ EXACT PAYMENT: Completing order {order.id}")

    # Calculate fiat amount from crypto (using invoice exchange rate)
    paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)

    # Create PaymentTransaction record
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_amount=paid_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=False,
        is_underpayment=False,
        is_late_payment=False,
        penalty_applied=False,
        penalty_percent=0.0,
        wallet_credit_amount=None
    )
    await PaymentTransactionRepository.create(transaction, session)

    # Complete order
    await OrderService.complete_order_payment(order.id, session)
    await session_commit(session)

    logging.info(f"🎉 SUCCESS: Order {order.id} marked as PAID")

    # Send notification to user
    user = await UserRepository.get_by_id(order.user_id, session)
    await NotificationService.payment_success(user, invoice.invoice_number)


async def _handle_minor_overpayment(payment_dto, invoice, order, session):
    """
    Handle minor overpayment (≤0.1% above required).

    Action:
    - Complete order normally
    - Excess amount forfeits to shop (no wallet credit)
    - Create PaymentTransaction record noting it was overpayment
    - Notify user (same as exact payment)
    """
    excess = payment_dto.cryptoAmount - invoice.payment_amount_crypto
    logging.info(f"💰 MINOR OVERPAYMENT: {format_crypto_amount(excess)} {payment_dto.cryptoCurrency.value} forfeits to shop")

    # Calculate fiat amount from crypto (using invoice exchange rate)
    paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)

    # Create PaymentTransaction record
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_amount=paid_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=True,  # Mark as overpayment
        is_underpayment=False,
        is_late_payment=False,
        penalty_applied=False,
        penalty_percent=0.0,
        wallet_credit_amount=None  # NO wallet credit (forfeits)
    )
    await PaymentTransactionRepository.create(transaction, session)

    # Complete order
    await OrderService.complete_order_payment(order.id, session)
    await session_commit(session)

    logging.info(f"🎉 SUCCESS: Order {order.id} marked as PAID (minor overpayment forfeited)")

    # Send notification to user (same as exact payment)
    user = await UserRepository.get_by_id(order.user_id, session)
    await NotificationService.payment_success(user, invoice.invoice_number)


async def _handle_significant_overpayment(payment_dto, invoice, order, session):
    """
    Handle significant overpayment (>0.1% above required).

    Action:
    - Complete order normally
    - Credit excess amount to user wallet
    - Create PaymentTransaction record
    - Notify user about wallet credit
    """
    # Calculate fiat amounts using invoice exchange rate
    paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)
    excess_crypto = payment_dto.cryptoAmount - invoice.payment_amount_crypto
    excess_fiat = calculate_fiat_from_crypto(excess_crypto, invoice)

    logging.info(f"💰 SIGNIFICANT OVERPAYMENT: {excess_fiat:.2f} EUR credited to wallet")

    # Create PaymentTransaction record
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_amount=paid_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=True,
        is_underpayment=False,
        is_late_payment=False,
        penalty_applied=False,
        penalty_percent=0.0,
        wallet_credit_amount=excess_fiat  # Credit to wallet
    )
    await PaymentTransactionRepository.create(transaction, session)

    # Credit wallet
    user = await UserRepository.get_by_id(order.user_id, session)
    user.top_up_amount += excess_fiat
    await UserRepository.update(user, session)

    # Complete order
    await OrderService.complete_order_payment(order.id, session)
    await session_commit(session)

    logging.info(f"🎉 SUCCESS: Order {order.id} marked as PAID (€{excess_fiat:.2f} credited to wallet)")

    # Send notification to user about wallet credit
    from utils.localizator import Localizator
    await NotificationService.payment_overpayment_wallet_credit(
        user, invoice.invoice_number, excess_fiat, Localizator.get_currency_symbol()
    )


async def _handle_underpayment(payment_dto, invoice, order, session):
    """
    Handle underpayment (paid less than required).

    Action depends on retry_count:
    - First underpayment (retry_count = 0):
      * Extend deadline by 30 minutes
      * Create new invoice for remaining amount
      * Set status to PENDING_PAYMENT_PARTIAL
      * Notify user with new payment details

    - Second underpayment (retry_count = 1):
      * Cancel order (status = TIMEOUT)
      * Apply 5% penalty to all payments received
      * Credit net amount to wallet
      * Release reserved stock
      * Notify user
    """
    shortfall = invoice.payment_amount_crypto - payment_dto.cryptoAmount
    logging.info(f"⚠️ UNDERPAYMENT: Missing {format_crypto_amount(shortfall)} {payment_dto.cryptoCurrency.value}")

    if order.retry_count == 0:
        # FIRST UNDERPAYMENT - Allow retry
        await _handle_first_underpayment(payment_dto, invoice, order, session)
    else:
        # SECOND UNDERPAYMENT - Cancel with penalty
        await _handle_second_underpayment(payment_dto, invoice, order, session)


async def _handle_first_underpayment(payment_dto, invoice, order, session):
    """Handle first underpayment - extend deadline and create new invoice."""
    from repositories.invoice import InvoiceRepository
    from models.invoice import InvoiceDTO
    from services.invoice import InvoiceService

    logging.info(f"🔄 FIRST UNDERPAYMENT: Extending deadline for order {order.id}")

    # Calculate fiat amount from crypto (using invoice exchange rate)
    paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)

    # Create PaymentTransaction for first payment
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_amount=paid_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=False,
        is_underpayment=True,
        is_late_payment=False,
        penalty_applied=False,
        penalty_percent=0.0,
        wallet_credit_amount=None
    )
    await PaymentTransactionRepository.create(transaction, session)

    # Update order fields
    from sqlalchemy import update as sqlalchemy_update
    from models.order import Order

    new_expires_at = datetime.now() + timedelta(minutes=config.PAYMENT_UNDERPAYMENT_RETRY_TIMEOUT_MINUTES)

    stmt = sqlalchemy_update(Order).where(Order.id == order.id).values(
        total_paid_crypto=order.total_paid_crypto + payment_dto.cryptoAmount,
        retry_count=1,
        original_expires_at=order.expires_at,
        expires_at=new_expires_at,
        status=OrderStatus.PENDING_PAYMENT_PARTIAL
    )
    from db import session_execute
    await session_execute(stmt, session)

    # Update in-memory order object for later use
    order.expires_at = new_expires_at

    # Calculate remaining amount using invoice exchange rate
    remaining_crypto = invoice.payment_amount_crypto - payment_dto.cryptoAmount
    remaining_fiat = calculate_fiat_from_crypto(remaining_crypto, invoice)

    # Create new invoice for remaining amount with KryptoExpress
    new_invoice = await InvoiceService.create_partial_payment_invoice(
        order_id=order.id,
        parent_invoice_id=invoice.id,
        remaining_crypto_amount=remaining_crypto,
        remaining_fiat_amount=remaining_fiat,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_currency=payment_dto.fiatCurrency,
        payment_attempt=2,  # Second attempt
        session=session
    )

    await session_commit(session)

    logging.info(f"⏰ Order {order.id} extended until {order.expires_at}")
    logging.info(f"📋 New invoice created: {new_invoice.invoice_number}")
    logging.info(f"   Payment address: {new_invoice.payment_address}")
    logging.info(f"   Remaining amount: {format_crypto_amount(remaining_crypto)} {payment_dto.cryptoCurrency.value} (€{remaining_fiat:.2f})")

    # Send notification to user with new deadline and invoice
    user = await UserRepository.get_by_id(order.user_id, session)
    await NotificationService.payment_underpayment_retry(
        user=user,
        invoice_number=invoice.invoice_number,
        paid_crypto=format_crypto_amount(payment_dto.cryptoAmount),
        required_crypto=format_crypto_amount(invoice.payment_amount_crypto),
        remaining_crypto=format_crypto_amount(remaining_crypto),
        crypto_currency=payment_dto.cryptoCurrency,
        new_invoice_number=new_invoice.invoice_number,
        new_payment_address=new_invoice.payment_address,
        new_expires_at=order.expires_at
    )


async def _handle_second_underpayment(payment_dto, invoice, order, session):
    """Handle second underpayment - cancel order with penalty and credit wallet."""
    logging.info(f"❌ SECOND UNDERPAYMENT: Cancelling order {order.id} with penalty")

    # Calculate total paid (first payment + this payment) using invoice exchange rate
    first_payment_fiat = calculate_fiat_from_crypto(order.total_paid_crypto, invoice)
    second_payment_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)
    total_paid_fiat = first_payment_fiat + second_payment_fiat

    # Apply penalty
    penalty_amount, net_amount = PaymentValidator.calculate_penalty(
        total_paid_fiat,
        config.PAYMENT_UNDERPAYMENT_PENALTY_PERCENT
    )

    logging.info(f"💸 Penalty: €{penalty_amount:.2f} (5%) | Net to wallet: €{net_amount:.2f}")

    # Create PaymentTransaction for second payment
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_amount=second_payment_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=False,
        is_underpayment=True,
        is_late_payment=False,
        penalty_applied=True,  # Penalty applied!
        penalty_percent=config.PAYMENT_UNDERPAYMENT_PENALTY_PERCENT,
        wallet_credit_amount=net_amount  # Net amount after penalty
    )
    await PaymentTransactionRepository.create(transaction, session)

    # Credit wallet (after penalty)
    user = await UserRepository.get_by_id(order.user_id, session)
    user.top_up_amount += net_amount
    await UserRepository.update(user, session)

    # Cancel order and release stock (don't refund wallet - already credited above with penalty)
    from enums.order_cancel_reason import OrderCancelReason
    await OrderService.cancel_order(order.id, OrderCancelReason.TIMEOUT, session, refund_wallet=False)
    await session_commit(session)

    logging.info(f"❌ Order {order.id} cancelled (2nd underpayment) | €{net_amount:.2f} credited to wallet")

    # Send notification to user about cancellation and wallet credit
    from utils.localizator import Localizator
    await NotificationService.payment_cancelled_underpayment(
        user=user,
        invoice_number=invoice.invoice_number,
        total_paid_fiat=total_paid_fiat,
        penalty_amount=penalty_amount,
        net_wallet_credit=net_amount,
        currency_sym=Localizator.get_currency_symbol()
    )


async def _handle_late_payment(payment_dto, invoice, order, session):
    """
    Handle late payment (received after deadline).

    Action:
    - Cancel order (status = TIMEOUT)
    - Apply 5% penalty
    - Credit net amount to wallet
    - Release reserved stock
    - Notify user
    """
    logging.info(f"⏰ LATE PAYMENT: Payment for order {order.id} received after deadline")

    # Calculate fiat amount from crypto (using invoice exchange rate)
    paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)

    # Apply penalty
    penalty_amount, net_amount = PaymentValidator.calculate_penalty(
        paid_fiat,
        config.PAYMENT_LATE_PENALTY_PERCENT
    )

    logging.info(f"💸 Penalty: €{penalty_amount:.2f} (5%) | Net to wallet: €{net_amount:.2f}")

    # Create PaymentTransaction
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,
        fiat_amount=paid_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=False,
        is_underpayment=False,
        is_late_payment=True,  # Late payment!
        penalty_applied=True,
        penalty_percent=config.PAYMENT_LATE_PENALTY_PERCENT,
        wallet_credit_amount=net_amount
    )
    await PaymentTransactionRepository.create(transaction, session)

    # Credit wallet (after penalty)
    user = await UserRepository.get_by_id(order.user_id, session)
    user.top_up_amount += net_amount
    await UserRepository.update(user, session)

    # Cancel order if not already cancelled (don't refund wallet - already credited above with penalty)
    if order.status not in [OrderStatus.TIMEOUT, OrderStatus.CANCELLED_BY_USER, OrderStatus.CANCELLED_BY_ADMIN]:
        from enums.order_cancel_reason import OrderCancelReason
        await OrderService.cancel_order(order.id, OrderCancelReason.TIMEOUT, session, refund_wallet=False)

    await session_commit(session)

    logging.info(f"⏰ Late payment processed: €{net_amount:.2f} credited to wallet")

    # Send notification to user about late payment and wallet credit
    from utils.localizator import Localizator
    await NotificationService.payment_late(
        user=user,
        invoice_number=invoice.invoice_number,
        paid_fiat=paid_fiat,
        penalty_amount=penalty_amount,
        net_wallet_credit=net_amount,
        currency_sym=Localizator.get_currency_symbol()
    )


async def _handle_currency_mismatch(payment_dto, invoice, order, session):
    """
    Handle currency mismatch (paid with wrong cryptocurrency).

    Action:
    - Log error
    - Do NOT process payment
    - Notify admin for manual intervention
    - Notify user that payment cannot be processed automatically
    """
    logging.error(f"❌ CURRENCY MISMATCH: Order {order.id}")
    logging.error(f"   Expected: {invoice.payment_crypto_currency.value}")
    logging.error(f"   Received: {payment_dto.cryptoCurrency.value}")
    logging.error(f"   Payment ID: {payment_dto.id}")
    logging.error(f"   TX Hash: {payment_dto.hash}")

    # Note: We still calculate fiat using invoice rate for audit purposes
    # even though the currency is wrong
    paid_fiat = calculate_fiat_from_crypto(payment_dto.cryptoAmount, invoice)

    # Create PaymentTransaction for audit trail
    transaction = PaymentTransactionDTO(
        order_id=order.id,
        invoice_id=invoice.id,
        crypto_amount=payment_dto.cryptoAmount,
        crypto_currency=payment_dto.cryptoCurrency,  # Wrong currency!
        fiat_amount=paid_fiat,
        fiat_currency=payment_dto.fiatCurrency,
        transaction_hash=payment_dto.hash,
        payment_address=payment_dto.address,
        payment_processing_id=payment_dto.id,
        is_overpayment=False,
        is_underpayment=False,
        is_late_payment=False,
        penalty_applied=False,
        penalty_percent=0.0,
        wallet_credit_amount=None
    )
    await PaymentTransactionRepository.create(transaction, session)
    await session_commit(session)

    # TODO: Send notification to admin for manual intervention
    # TODO: Send notification to user that payment cannot be processed
    logging.error(f"⚠️ MANUAL INTERVENTION REQUIRED for order {order.id}")
