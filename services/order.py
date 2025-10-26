from datetime import datetime, timedelta
import logging

from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import CartCallback, OrderCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.order_cancel_reason import OrderCancelReason
from enums.order_status import OrderStatus
from models.cart import CartDTO
from models.cartItem import CartItemDTO
from models.item import ItemDTO
from models.order import OrderDTO
from repositories.cartItem import CartItemRepository
from repositories.item import ItemRepository
from repositories.order import OrderRepository
from repositories.user import UserRepository
from utils.localizator import Localizator


class OrderService:

    @staticmethod
    async def orchestrate_order_creation(
        cart_dto: "CartDTO",
        session: AsyncSession | Session
    ) -> tuple[OrderDTO, list[dict], bool]:
        """
        Orchestrates order creation with stock reservation.

        This is called when user confirms checkout (after cart confirmation).
        Creates order record and reserves items. NO payment processing here!

        Flow:
        1. Calculate total price (items + MAX shipping cost)
        2. Create order record with timer
        3. Reserve items (with partial support)
        4. Handle stock adjustments if needed
        5. Determine item type (digital/physical)
        6. Set status: PENDING_PAYMENT or PENDING_PAYMENT_AND_ADDRESS

        Args:
            cart_dto: CartDTO with user_id and items
            session: Database session

        Returns:
            Tuple of (order, stock_adjustments, has_physical_items)
            - order: Created OrderDTO
            - stock_adjustments: List of items with changed quantities
              [{'subcategory_id', 'subcategory_name', 'requested', 'reserved'}, ...]
            - has_physical_items: True if order contains physical items

        Raises:
            ValueError: If all items are out of stock
        """
        from repositories.subcategory import SubcategoryRepository

        # Extract data from CartDTO
        user_id = cart_dto.user_id
        cart_items = cart_dto.items

        # 1. Calculate total price (items + MAX shipping cost)
        total_price_with_shipping, max_shipping_cost = await OrderService._calculate_order_totals(
            cart_items, session
        )

        # 2. Create order record with timer (NO wallet deduction yet!)
        expires_at = datetime.now() + timedelta(minutes=config.ORDER_TIMEOUT_MINUTES)

        order_dto = OrderDTO(
            user_id=user_id,
            status=OrderStatus.PENDING_PAYMENT,  # Will be updated based on item type
            total_price=total_price_with_shipping,
            shipping_cost=max_shipping_cost,
            currency=config.CURRENCY,
            expires_at=expires_at,
            wallet_used=0.0  # Will be set later by orchestrate_payment_processing
        )

        order_id = await OrderRepository.create(order_dto, session)
        logging.info(f"✅ Order {order_id} created (Status: PENDING_PAYMENT, Expires: {expires_at.strftime('%H:%M')})")

        # Reload order to get created_at (set by func.now() in DB)
        order_dto = await OrderRepository.get_by_id(order_id, session)

        # 3. Reserve items and track stock adjustments
        reserved_items, stock_adjustments = await OrderService._reserve_items_with_adjustments(
            cart_items, order_id, session
        )

        # 4. If stock adjustments: Recalculate price and update order
        if stock_adjustments:
            # Recalculate total with ACTUAL reserved quantities
            actual_total_price = 0.0
            actual_max_shipping_cost = 0.0

            for reserved_item in reserved_items:
                actual_total_price += reserved_item.price
                if reserved_item.is_physical:
                    actual_max_shipping_cost = max(actual_max_shipping_cost, reserved_item.shipping_cost)

            actual_total_with_shipping = actual_total_price + actual_max_shipping_cost

            # Update order with actual amounts
            order_dto.total_price = actual_total_with_shipping
            order_dto.shipping_cost = actual_max_shipping_cost
            await OrderRepository.update(order_dto, session)

            logging.info(
                f"📊 Updated order {order_id} with adjusted prices: "
                f"Total={actual_total_with_shipping:.2f} EUR (was {total_price_with_shipping:.2f} EUR)"
            )

        # 5. Determine item type and set correct status
        has_physical_items = OrderService._detect_physical_items(reserved_items)

        if has_physical_items:
            await OrderRepository.update_status(order_id, OrderStatus.PENDING_PAYMENT_AND_ADDRESS, session)
            logging.info(f"📦 Order {order_id} contains physical items → Status: PENDING_PAYMENT_AND_ADDRESS")
        else:
            # Status already PENDING_PAYMENT (set at creation)
            logging.info(f"💾 Order {order_id} contains only digital items → Status: PENDING_PAYMENT")

        # Reload order after status update
        order_dto = await OrderRepository.get_by_id(order_id, session)

        return order_dto, stock_adjustments, has_physical_items

    @staticmethod
    async def complete_order_payment(
        order_id: int,
        session: AsyncSession | Session
    ):
        """
        Completes order after successful payment.

        Order of operations (status FIRST for consistency):
        1. Set status to PAID (payment confirmed - source of truth)
        2. Mark items as sold (data integrity)
        3. Create Buy records (purchase history)
        4. Commit all changes
        5. Deliver items to user (send private_data via DM)

        Rationale: Status represents business truth (payment received).
        If item marking fails, status=PAID allows recovery jobs to detect
        and fix incomplete orders. Status should be set immediately after
        payment confirmation, not after data operations.
        """
        import logging
        from models.buy import BuyDTO
        from models.buyItem import BuyItemDTO
        from repositories.buy import BuyRepository
        from repositories.buyItem import BuyItemRepository
        from services.message import MessageService
        from services.notification import NotificationService

        # Get order details
        order = await OrderRepository.get_by_id(order_id, session)
        items = await ItemRepository.get_by_order_id(order_id, session)

        if not items:
            logging.warning(f"Order {order_id} has no items - cannot complete payment")
            return

        # 1. Update order status FIRST (payment confirmed = source of truth)
        # Check if order contains physical items requiring shipment
        has_physical_items = any(item.is_physical for item in items)

        if has_physical_items:
            # Physical items → Status: PAID_AWAITING_SHIPMENT
            await OrderRepository.update_status(order_id, OrderStatus.PAID_AWAITING_SHIPMENT, session)
            logging.info(f"✅ Order {order_id} status set to PAID_AWAITING_SHIPMENT (physical items)")
        else:
            # Digital items only → Status: PAID
            await OrderRepository.update_status(order_id, OrderStatus.PAID, session)
            logging.info(f"✅ Order {order_id} status set to PAID")

        # 2. Mark items as sold (data integrity)
        for item in items:
            item.is_sold = True
        await ItemRepository.update(items, session)

        # 3. Create Buy record for purchase history (same as old system)
        # Check if Buy record already exists (idempotency - prevent duplicates)
        existing_buy_items = await BuyItemRepository.get_by_item_ids([item.id for item in items], session)

        if not existing_buy_items:
            # No Buy record yet - create new one
            buy_dto = BuyDTO(
                buyer_id=order.user_id,
                quantity=len(items),
                total_price=order.total_price
            )
            buy_id = await BuyRepository.create(buy_dto, session)

            # Link items to buy record
            buy_item_dto_list = [BuyItemDTO(item_id=item.id, buy_id=buy_id) for item in items]
            await BuyItemRepository.create_many(buy_item_dto_list, session)
            logging.info(f"✅ Created Buy record {buy_id} for order {order_id}")
        else:
            logging.warning(f"⚠️ Buy record already exists for order {order_id} - skipping duplicate creation")

        # 4. Commit all changes
        await session_commit(session)
        logging.info(f"✅ Order {order_id} data committed (status=PAID, items sold, buy records created)")

        # 5. Deliver items to user
        user = await UserRepository.get_by_id(order.user_id, session)

        # Create message with bought items (same format as old system)
        items_message = MessageService.create_message_with_bought_items(items)

        # Send items to user via DM (user receives their purchased items)
        await NotificationService.send_to_user(items_message, user.telegram_id)

        logging.info(f"✅ Order {order_id} completed - {len(items)} items delivered to user {user.id}")

        # Send admin notification if order has physical items awaiting shipment
        if has_physical_items:
            from repositories.invoice import InvoiceRepository

            invoice = await InvoiceRepository.get_by_order_id(order_id, session)
            await NotificationService.order_awaiting_shipment(
                user_id=order.user_id,
                invoice_number=invoice.invoice_number,
                session=session
            )
            logging.info(f"📢 Admin notification sent: Order {order_id} awaiting shipment")

    @staticmethod
    async def cancel_order(
        order_id: int,
        reason: 'OrderCancelReason',
        session: AsyncSession | Session,
        refund_wallet: bool = True
    ) -> tuple[bool, str]:
        """
        Cancels an order with the specified reason.

        Args:
            order_id: Order ID to cancel
            reason: Reason for cancellation (USER, TIMEOUT, ADMIN)
            session: Database session
            refund_wallet: Whether to refund wallet balance (False if payment handler already credited)

        Returns:
            tuple[bool, str]: (within_grace_period, message)
                - within_grace_period: True if cancelled for free (no strike)
                - message: Confirmation message

        Raises:
            ValueError: If order not found or cannot be cancelled
        """
        from datetime import datetime
        from enums.order_cancel_reason import OrderCancelReason
        import logging

        # Get order
        order = await OrderRepository.get_by_id(order_id, session)

        if not order:
            raise ValueError("Order not found")

        # Only pending/paid (not yet delivered) orders can be cancelled
        # PAID status means wallet covered amount but items not yet delivered (awaiting user confirmation of adjustments)
        if order.status not in [OrderStatus.PENDING_PAYMENT, OrderStatus.PENDING_PAYMENT_AND_ADDRESS, OrderStatus.PENDING_PAYMENT_PARTIAL, OrderStatus.PAID]:
            raise ValueError("Order cannot be cancelled (Status: {})".format(order.status.value))

        # Check grace period (only relevant for USER cancellation)
        time_elapsed = (datetime.utcnow() - order.created_at).total_seconds() / 60  # Minutes
        within_grace_period = time_elapsed <= config.ORDER_CANCEL_GRACE_PERIOD_MINUTES

        # Release reserved items
        items = await ItemRepository.get_by_order_id(order_id, session)
        for item in items:
            item.order_id = None  # Remove reservation
        await ItemRepository.update(items, session)

        # Handle wallet refund/penalty logic
        # Three scenarios:
        # 1. order.wallet_used > 0: Refund wallet (with or without penalty)
        # 2. order.wallet_used = 0 BUT user has wallet balance AND penalty applies: Charge reservation fee
        # 3. order.wallet_used = 0 AND (no wallet OR no penalty): No fee
        wallet_refund_info = None
        user = await UserRepository.get_by_id(order.user_id, session)

        # Determine if penalty should be applied
        # NO penalty: Admin cancellation OR User within grace period
        # YES penalty: User after grace period OR Timeout
        apply_penalty = False
        if reason == OrderCancelReason.ADMIN:
            apply_penalty = False  # Admin cancels never have penalty
        elif reason == OrderCancelReason.USER:
            apply_penalty = not within_grace_period  # User penalty only outside grace period
        elif reason == OrderCancelReason.TIMEOUT:
            apply_penalty = True  # Timeout always has penalty (strike)

        # Case 1: Wallet was already used in order (refund with/without penalty)
        if refund_wallet and order.wallet_used > 0:
            if apply_penalty:
                # Apply penalty (configurable percentage)
                # Use calculate_penalty() to ensure correct rounding (penalty rounded DOWN)
                from services.payment_validator import PaymentValidator
                penalty_percent = config.PAYMENT_LATE_PENALTY_PERCENT
                penalty_amount, refund_amount = PaymentValidator.calculate_penalty(
                    order.wallet_used,
                    penalty_percent
                )

                user.top_up_amount = round(user.top_up_amount + refund_amount, 2)
                await UserRepository.update(user, session)

                logging.info(f"💰 Refunded {refund_amount} EUR to user {user.id} wallet ({reason.value} cancellation, {penalty_percent}% penalty applied)")

                wallet_refund_info = {
                    'original_amount': order.wallet_used,
                    'penalty_amount': penalty_amount,
                    'refund_amount': refund_amount,
                    'penalty_percent': penalty_percent,
                    'reason': reason.value
                }
                # TODO: Create strike for late cancellation/timeout
            else:
                # Full refund for: ADMIN or USER within grace period (rounded to 2 decimals)
                user.top_up_amount = round(user.top_up_amount + order.wallet_used, 2)
                await UserRepository.update(user, session)

                logging.info(f"💰 Refunded {order.wallet_used} EUR to user {user.id} wallet ({reason.value} cancellation, no penalty)")

                wallet_refund_info = {
                    'original_amount': order.wallet_used,
                    'penalty_amount': 0.0,
                    'refund_amount': order.wallet_used,
                    'penalty_percent': 0,
                    'reason': reason.value
                }

        # Case 2: Wallet NOT used in order BUT user has balance AND penalty applies
        # Charge "reservation fee" for blocking items without payment
        elif apply_penalty and user.top_up_amount > 0:
            from services.payment_validator import PaymentValidator
            penalty_percent = config.PAYMENT_LATE_PENALTY_PERCENT

            # Calculate fee based on order total (capped at wallet balance)
            base_amount = min(order.total_price, user.top_up_amount)
            penalty_amount, _ = PaymentValidator.calculate_penalty(base_amount, penalty_percent)

            # Deduct reservation fee from wallet
            user.top_up_amount = round(user.top_up_amount - penalty_amount, 2)
            await UserRepository.update(user, session)

            logging.info(f"💸 Charged {penalty_amount} EUR reservation fee from user {user.id} wallet ({reason.value} cancellation, no wallet used but penalty applies)")

            wallet_refund_info = {
                'original_amount': 0.0,
                'penalty_amount': penalty_amount,
                'refund_amount': 0.0,
                'penalty_percent': penalty_percent,
                'reason': f"{reason.value}_reservation_fee",
                'base_amount': base_amount
            }

        # Case 3: No wallet used AND (no wallet balance OR no penalty)
        # No financial consequence, just release items

        # Set order status based on cancel reason
        if reason == OrderCancelReason.USER:
            new_status = OrderStatus.CANCELLED_BY_USER
            message = "Order successfully cancelled"
            # TODO: If not within_grace_period → create strike!
        elif reason == OrderCancelReason.TIMEOUT:
            new_status = OrderStatus.TIMEOUT
            within_grace_period = False  # Timeouts never count as grace period
            message = "Order cancelled due to timeout"
        elif reason == OrderCancelReason.ADMIN:
            new_status = OrderStatus.CANCELLED_BY_ADMIN
            within_grace_period = True  # Admin cancels don't cause strikes
            message = "Order cancelled by admin"
        else:
            raise ValueError(f"Unknown cancel reason: {reason}")

        await OrderRepository.update_status(order_id, new_status, session)

        # Send notification to user about wallet refund if applicable
        if wallet_refund_info:
            from services.notification import NotificationService
            from utils.localizator import Localizator
            from repositories.invoice import InvoiceRepository

            # Get invoice number for notification
            invoice = await InvoiceRepository.get_by_order_id(order_id, session)
            invoice_number = invoice.invoice_number if invoice else str(order_id)

            await NotificationService.notify_order_cancelled_wallet_refund(
                user=user,
                invoice_number=invoice_number,
                refund_info=wallet_refund_info,
                currency_sym=Localizator.get_currency_symbol()
            )

        return within_grace_period, message

    @staticmethod
    async def cancel_order_by_user(
        order_id: int,
        session: AsyncSession | Session
    ) -> tuple[bool, str]:
        """
        Cancels an order by the user (convenience wrapper).

        Returns:
            tuple[bool, str]: (within_grace_period, message)
        """
        from enums.order_cancel_reason import OrderCancelReason
        return await OrderService.cancel_order(order_id, OrderCancelReason.USER, session)

    # ========================================
    # Handler Methods (moved from CartService)
    # ========================================

    @staticmethod
    async def create_order(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 0: Create Order from Cart

        Flow:
        1. Get cart items and create CartDTO
        2. Call orchestrator to create order with stock reservation
        3. Commit and clear cart
        4. UI Fork based on result:
           - Stock adjustments → Show confirmation screen
           - Physical items → Request shipping address
           - Digital items → Redirect to payment

        Returns:
            Tuple of (message, keyboard)
        """
        # 1. Get cart items
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

        if not cart_items:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=CartCallback.create(0)  # Back to Cart (cross-domain)
            )
            return Localizator.get_text(BotEntity.USER, "no_cart_items"), kb_builder

        try:
            # 2. Create order via orchestrator
            cart_dto = CartDTO(user_id=user.id, items=cart_items)
            order, stock_adjustments, has_physical_items = await OrderService.orchestrate_order_creation(
                cart_dto=cart_dto,
                session=session
            )

            # Save order_id to FSM for later use
            if state:
                await state.update_data(order_id=order.id)

            # Commit order
            await session_commit(session)

            # 3. UI Fork: Stock adjustments?
            if stock_adjustments:
                # Show confirmation screen - cart NOT cleared yet (user might cancel)
                # Store adjustments in FSM state for potential back navigation
                if state:
                    import json
                    await state.update_data(
                        stock_adjustments=json.dumps(stock_adjustments),
                        order_id=order.id
                    )
                return await OrderService.show_stock_adjustment_confirmation(
                    callback, order, stock_adjustments, session
                )

            # 4. Clear cart (order successfully created, no adjustments)
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)
            await session_commit(session)

            # 5. UI Fork: Physical items?
            if has_physical_items:
                # Request shipping address
                from handlers.user.shipping_states import ShippingAddressStates
                await state.set_state(ShippingAddressStates.waiting_for_address)

                message_text = Localizator.get_text(BotEntity.USER, "shipping_address_request").format(
                    retention_days=config.DATA_RETENTION_DAYS
                )
                kb_builder = InlineKeyboardBuilder()
                kb_builder.button(
                    text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                    callback_data=OrderCallback.create(level=4, order_id=order.id)  # Cancel Order
                )
                return message_text, kb_builder

            # 6. UI Fork: Digital items → Redirect directly to payment (no intermediate screen)
            return await OrderService.process_payment(callback, session, state)

        except ValueError as e:
            # All items out of stock - remove them from cart immediately to prevent loop
            logging.info(f"🧹 Removing all out-of-stock items from cart for user {user.id}")
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)
            await session_commit(session)

            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "back_to_cart"),
                callback_data=CartCallback.create(0)  # Back to Cart (cross-domain)
            )
            message_text = (
                f"❌ <b>{Localizator.get_text(BotEntity.USER, 'all_items_out_of_stock')}</b>\n\n"
                f"{Localizator.get_text(BotEntity.USER, 'all_items_out_of_stock_desc')}"
            )
            return message_text, kb_builder

    @staticmethod
    async def process_payment(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 4: Payment Processing Router

        Smart payment flow:
        1. First checks if wallet can cover everything
        2. If yes: processes payment immediately (no crypto selection needed)
        3. If no: shows crypto selection, then processes with crypto payment

        Three modes:
        A. First visit + wallet covers all: Direct wallet payment
        B. First visit + wallet insufficient: Show crypto selection
        C. Crypto selected: Process payment with crypto

        Returns:
            Tuple of (message, keyboard)
        """
        from services.payment import PaymentService
        from enums.cryptocurrency import Cryptocurrency
        from repositories.invoice import InvoiceRepository

        unpacked_cb = OrderCallback.unpack(callback.data)

        # Get order_id from callback or FSM
        order_id = unpacked_cb.order_id
        if order_id == -1 and state:
            state_data = await state.get_data()
            order_id = state_data.get("order_id")

        if not order_id or order_id == -1:
            # No order found - error
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=CartCallback.create(0)  # Back to Cart (cross-domain)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Check if invoice already exists for this order
        existing_invoice = await InvoiceRepository.get_by_order_id(order_id, session)

        if existing_invoice:
            # Invoice already exists - show existing payment screen (no new crypto selection!)
            order = await OrderRepository.get_by_id(order_id, session)

            # Format payment screen with existing invoice
            payment_message = await OrderService._format_payment_screen(
                invoice=existing_invoice,
                order=order,
                session=session
            )

            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "cancel_order"),
                callback_data=OrderCallback.create(level=4, order_id=order_id)
            )

            return payment_message, kb_builder

        # Check if crypto already selected
        crypto_selected = unpacked_cb.cryptocurrency and unpacked_cb.cryptocurrency != Cryptocurrency.PENDING_SELECTION

        # Mode A/B: First visit - Check wallet balance first
        if not crypto_selected:
            # Get order and user to check wallet balance
            order = await OrderRepository.get_by_id(order_id, session)
            user = await UserRepository.get_by_id(order.user_id, session)
            wallet_balance = user.top_up_amount
            order_total = order.total_price

            # If wallet covers everything, process payment immediately
            if wallet_balance >= order_total:
                # Mode A: Direct wallet payment (use BTC as dummy, won't be used)
                try:
                    invoice, needs_crypto_payment = await PaymentService.orchestrate_payment_processing(
                        order_id=order_id,
                        crypto_currency=Cryptocurrency.BTC,  # Dummy value, wallet covers all
                        session=session
                    )

                    # Clear FSM state
                    if state:
                        await state.clear()

                    # Show completion message with full invoice details
                    kb_builder = InlineKeyboardBuilder()
                    message_text = await OrderService._format_wallet_payment_invoice(
                        invoice=invoice,
                        order=order,
                        session=session
                    )
                    return message_text, kb_builder

                except ValueError as e:
                    # Error during payment processing
                    kb_builder = InlineKeyboardBuilder()
                    kb_builder.button(
                        text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                        callback_data=OrderCallback.create(0)
                    )
                    return Localizator.get_text(BotEntity.USER, "payment_processing_error").format(error=str(e)), kb_builder
            else:
                # Mode B: Wallet insufficient - Show crypto selection
                from services.cart import CartService
                return await CartService._show_crypto_selection(order_id)

        # Mode C: Crypto selected - Process payment
        try:
            invoice, needs_crypto_payment = await PaymentService.orchestrate_payment_processing(
                order_id=order_id,
                crypto_currency=unpacked_cb.cryptocurrency,
                session=session
            )

            # Clear FSM state (order processing done)
            if state:
                await state.clear()

            if not needs_crypto_payment:
                # Wallet covered everything - Order PAID and completed!
                order = await OrderRepository.get_by_id(order_id, session)
                kb_builder = InlineKeyboardBuilder()
                message_text = await OrderService._format_wallet_payment_invoice(
                    invoice=invoice,
                    order=order,
                    session=session
                )
                return message_text, kb_builder

            else:
                # Wallet insufficient - Show payment screen with QR code
                order = await OrderRepository.get_by_id(order_id, session)

                # Format payment details
                payment_message = await OrderService._format_payment_screen(
                    invoice=invoice,
                    order=order,
                    session=session
                )

                kb_builder = InlineKeyboardBuilder()
                kb_builder.button(
                    text=Localizator.get_text(BotEntity.USER, "cancel_order"),
                    callback_data=OrderCallback.create(level=4, order_id=order_id)  # Cancel Order = Level 4
                )

                return payment_message, kb_builder

        except ValueError as e:
            # Error during payment processing
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "payment_processing_error").format(error=str(e)), kb_builder

    @staticmethod
    async def reenter_shipping_address(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> str:
        """
        Level 2: Re-enter Shipping Address

        User clicked cancel on address confirmation screen.
        Restart address input process.

        Returns:
            Message prompting for address input
        """
        from handlers.user.shipping_states import ShippingAddressStates

        # Get order_id from FSM
        if state:
            state_data = await state.get_data()
            order_id = state_data.get("order_id")

            # Set FSM state to waiting for address
            await state.set_state(ShippingAddressStates.waiting_for_address)

        # Return prompt message
        return Localizator.get_text(BotEntity.USER, "shipping_address_request").format(
            retention_days=config.DATA_RETENTION_DAYS
        )

    @staticmethod
    async def confirm_shipping_address(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 6: Shipping Address Confirmation

        Saves shipping address and updates order status.
        Then redirects to Level 4 (Payment Processing).

        Flow:
        1. Get order_id from FSM
        2. Get shipping_address from FSM
        3. Save encrypted address
        4. Update status: PENDING_PAYMENT_AND_ADDRESS → PENDING_PAYMENT
        5. Clear FSM state (address collection done)
        6. Redirect to Level 4 with "Continue" button

        Args:
            callback: Callback query
            session: Database session
            state: FSM context

        Returns:
            Tuple of (message, keyboard)
        """
        from services.shipping import ShippingService

        # Get order_id and address from FSM
        if not state:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        state_data = await state.get_data()
        order_id = state_data.get("order_id")
        shipping_address = state_data.get("shipping_address")

        # Check: Order ID missing (technical error)?
        if not order_id:
            # FSM state lost - back to cart (no order to cancel)
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Check: Shipping address missing?
        if not shipping_address:
            # Restart address collection - user must enter text
            from handlers.user.shipping_states import ShippingAddressStates
            await state.set_state(ShippingAddressStates.waiting_for_address)

            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "cancel_order"),
                callback_data=OrderCallback.create(level=4, order_id=order_id)  # Level 4 = Cancel with strike logic
            )

            return Localizator.get_text(BotEntity.USER, "shipping_address_missing").format(
                retention_days=config.DATA_RETENTION_DAYS
            ), kb_builder

        # Get order
        order = await OrderRepository.get_by_id(order_id, session)
        if not order:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Save encrypted shipping address
        await ShippingService.save_shipping_address(order_id, shipping_address, session)

        # Update order status: PENDING_PAYMENT_AND_ADDRESS → PENDING_PAYMENT
        await OrderRepository.update_status(order_id, OrderStatus.PENDING_PAYMENT, session)
        await session_commit(session)

        # Keep order_id in state for payment processing
        # State will be cleared after successful payment

        # Directly proceed to payment processing (no intermediate screen)
        return await OrderService.process_payment(callback, session, state)

    @staticmethod
    async def show_stock_adjustment_confirmation(
        callback: CallbackQuery,
        order: OrderDTO,
        stock_adjustments: list[dict],
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Shows confirmation screen when stock was adjusted during order creation.
        Displays complete order overview with strike-through for adjusted items.
        """
        from repositories.item import ItemRepository
        from repositories.subcategory import SubcategoryRepository

        # Get order items to build complete overview
        order_items = await ItemRepository.get_by_order_id(order.id, session)

        # Build adjustment map for quick lookup
        adjustment_map = {}
        for adj in stock_adjustments:
            adjustment_map[adj['subcategory_id']] = {
                'requested': adj['requested'],
                'reserved': adj['reserved'],
                'name': adj['subcategory_name']
            }

        # Build items list with strike-through for adjustments
        items_dict = {}
        for item in order_items:
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            key = (item.subcategory_id, subcategory.name, item.price)
            items_dict[key] = items_dict.get(key, 0) + 1

        items_list = ""
        subtotal = 0.0
        displayed_subcategories = set()

        # First, show all items that were reserved (including partial)
        for (subcategory_id, name, price), qty in items_dict.items():
            line_total = price * qty
            displayed_subcategories.add(subcategory_id)

            if subcategory_id in adjustment_map:
                adj = adjustment_map[subcategory_id]
                # Partial stock - show original crossed out, then actual
                items_list += f"<s>{adj['requested']}x</s> → {qty}x {name} ⚠️\n"
                items_list += f"  {Localizator.get_currency_symbol()}{price:.2f} × {qty}{' ' * (20 - len(name))}{Localizator.get_currency_symbol()}{line_total:.2f}\n"
                subtotal += line_total
            else:
                # No adjustment - normal display
                items_list += f"{qty}x {name}\n"
                items_list += f"  {Localizator.get_currency_symbol()}{price:.2f} × {qty}{' ' * (20 - len(name))}{Localizator.get_currency_symbol()}{line_total:.2f}\n"
                subtotal += line_total

        # Now add completely sold out items (reserved=0) from adjustments
        for subcategory_id, adj in adjustment_map.items():
            if adj['reserved'] == 0 and subcategory_id not in displayed_subcategories:
                # Completely sold out - strike through
                items_list += f"<s>{adj['requested']}x {adj['name']}</s> ❌\n"
                items_list += f"  <i>Ausverkauft (entfernt)</i>\n"

        # Shipping line
        shipping_line = ""
        if order.shipping_cost > 0:
            shipping_line = f"Shipping{' ' * 18}{Localizator.get_currency_symbol()}{order.shipping_cost:.2f}\n"

        # Calculate spacing
        subtotal_spacing = " " * 18
        total_spacing = " " * 23

        # Build message
        message_text = f"⚠️ <b>STOCK ADJUSTMENT</b>\n\n"
        message_text += f"Some items are no longer available in the\nrequested quantity:\n\n"
        message_text += f"<b>ITEMS</b>\n"
        message_text += f"─────────────────────────────\n"
        message_text += items_list
        message_text += f"─────────────────────────────\n"
        message_text += f"Subtotal{subtotal_spacing}{Localizator.get_currency_symbol()}{subtotal:.2f}\n"
        message_text += shipping_line
        message_text += f"─────────────────────────────\n"
        message_text += f"<b>TOTAL{total_spacing}{Localizator.get_currency_symbol()}{order.total_price:.2f}</b>\n\n"
        message_text += f"<i>Continue with adjusted order?</i>"

        # Buttons
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text="✅ Continue Payment",
            callback_data=OrderCallback.create(9, order_id=order.id)  # Level 9 = Confirm adjusted order
        )
        kb_builder.button(
            text="❌ Cancel Order",
            callback_data=OrderCallback.create(level=4, order_id=order.id)  # Level 4 = Cancel order
        )

        return message_text, kb_builder

    @staticmethod
    async def reshow_stock_adjustment(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 6: Re-show Stock Adjustment Screen

        Called when user clicks Back from cancel confirmation dialog.
        Reloads stock adjustments from FSM state and displays adjustment screen again.
        """
        import json

        unpacked_cb = OrderCallback.unpack(callback.data)
        order_id = unpacked_cb.order_id

        if not order_id:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Get order
        order = await OrderRepository.get_by_id(order_id, session)
        if not order:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Get stock adjustments from FSM state
        stock_adjustments = []
        if state:
            state_data = await state.get_data()
            adjustments_json = state_data.get("stock_adjustments")
            if adjustments_json:
                stock_adjustments = json.loads(adjustments_json)

        # Show stock adjustment screen again
        return await OrderService.show_stock_adjustment_confirmation(
            callback, order, stock_adjustments, session
        )

    @staticmethod
    async def confirm_adjusted_order(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 9: Stock Adjustment Confirmation

        User confirms order with adjusted quantities.
        Clears cart and redirects to next step based on order status.

        Flow:
        1. Get order from callback
        2. Clear cart (remove sold-out items, keep rest for potential reorder)
        3. Check order status
        4. Fork based on status:
           - PENDING_PAYMENT_AND_ADDRESS → Level 6 (Shipping Address)
           - PENDING_PAYMENT → Level 4 (Payment Processing)

        Args:
            callback: Callback query
            session: Database session
            state: FSM context

        Returns:
            Tuple of (message, keyboard)
        """
        unpacked_cb = OrderCallback.unpack(callback.data)
        order_id = unpacked_cb.order_id

        if not order_id:
            # No order ID - back to cart
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Get order
        order = await OrderRepository.get_by_id(order_id, session)
        if not order:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        # Clear cart items that were processed in this order
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

        # Get order items to see what was actually reserved
        from repositories.item import ItemRepository
        order_items = await ItemRepository.get_by_order_id(order_id, session)

        # Build map of what was reserved per subcategory
        reserved_by_subcategory = {}
        for item in order_items:
            subcategory_id = item.subcategory_id
            reserved_by_subcategory[subcategory_id] = reserved_by_subcategory.get(subcategory_id, 0) + 1

        # Remove cart items that were fully processed or sold out
        for cart_item in cart_items:
            reserved = reserved_by_subcategory.get(cart_item.subcategory_id, 0)
            if reserved == 0:
                # Item was sold out - remove from cart
                await CartItemRepository.remove_from_cart(cart_item.id, session)
            elif reserved < cart_item.quantity:
                # Partial stock - remove from cart (user can re-add if desired)
                await CartItemRepository.remove_from_cart(cart_item.id, session)
            else:
                # Full quantity was reserved - remove from cart
                await CartItemRepository.remove_from_cart(cart_item.id, session)

        await session_commit(session)

        # Fork based on order status
        kb_builder = InlineKeyboardBuilder()

        if order.status == OrderStatus.PENDING_PAYMENT_AND_ADDRESS:
            # Physical items → Collect shipping address
            if state:
                from handlers.user.shipping_states import ShippingAddressStates
                await state.set_state(ShippingAddressStates.waiting_for_address)

            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "cancel_order"),
                callback_data=OrderCallback.create(level=4, order_id=order_id)  # Level 4 = Cancel
            )

            message_text = Localizator.get_text(BotEntity.USER, "shipping_address_request").format(
                retention_days=config.DATA_RETENTION_DAYS
            )

        elif order.status == OrderStatus.PENDING_PAYMENT:
            # Digital items → Proceed to payment
            # Directly call process_payment to show order details or crypto selection
            return await OrderService.process_payment(callback, session, state)

        else:
            # Unexpected status - error
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                callback_data=OrderCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

        return message_text, kb_builder

    @staticmethod
    async def cancel_order_handler(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 4: Show cancel confirmation dialog.
        Checks grace period and warns about penalties if applicable.
        Stores grace period status in FSM for 10 seconds to prevent race condition.
        """
        unpacked_cb = OrderCallback.unpack(callback.data)
        order_id = unpacked_cb.order_id

        kb_builder = InlineKeyboardBuilder()

        # Defensive check: Order ID must be set
        if order_id == -1:
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return "❌ <b>Error: Invalid Order ID</b>", kb_builder

        try:
            from datetime import datetime

            # Get order to check grace period
            order = await OrderRepository.get_by_id(order_id, session)

            if not order:
                kb_builder.row(CartCallback.create(0).get_back_button(0))
                return Localizator.get_text(BotEntity.USER, "order_not_found_error"), kb_builder

            # Check grace period
            time_elapsed = (datetime.utcnow() - order.created_at).total_seconds() / 60
            within_grace_period = time_elapsed <= config.ORDER_CANCEL_GRACE_PERIOD_MINUTES

            # Store grace period status and timestamp in FSM (valid for 10 seconds)
            if state:
                await state.update_data(
                    cancel_grace_status=within_grace_period,
                    cancel_grace_timestamp=datetime.utcnow().timestamp()
                )

            # Build confirmation message based on grace period and wallet usage
            if within_grace_period:
                message_text = Localizator.get_text(BotEntity.USER, "cancel_order_confirm_free").format(
                    grace_period=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
                )
            else:
                # Grace period expired - warn about penalty
                if order.wallet_used > 0:
                    # Wallet was used - warn about both strike and fee
                    message_text = Localizator.get_text(BotEntity.USER, "cancel_order_confirm_penalty_with_fee").format(
                        grace_period=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES,
                        penalty_percent=config.PAYMENT_LATE_PENALTY_PERCENT,
                        currency_sym=Localizator.get_currency_symbol()
                    )
                else:
                    # No wallet used - warn about strike only
                    message_text = Localizator.get_text(BotEntity.USER, "cancel_order_confirm_penalty_no_fee").format(
                        grace_period=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
                    )

            # Buttons: Confirm or Go Back
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                callback_data=OrderCallback.create(level=5, order_id=order_id)  # Level 5 = Execute cancellation
            )

            # Check if we came from stock adjustment screen
            has_stock_adjustment = False
            if state:
                state_data = await state.get_data()
                has_stock_adjustment = "stock_adjustments" in state_data

            if has_stock_adjustment:
                # Back to stock adjustment screen
                kb_builder.button(
                    text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                    callback_data=OrderCallback.create(level=6, order_id=order_id)  # Level 6 = Re-show stock adjustment
                )
            else:
                # Back to payment screen
                kb_builder.button(
                    text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                    callback_data=OrderCallback.create(level=3, order_id=order_id)  # Back to payment screen
                )

            return message_text, kb_builder

        except Exception as e:
            # Order not found or error checking status
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return f"❌ <b>Error:</b> {str(e)}", kb_builder

    @staticmethod
    async def execute_cancel_order(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Level 5: Execute order cancellation after user confirmation.
        Uses stored grace period status if < 10 seconds old, otherwise recalculates.
        """
        from datetime import datetime

        unpacked_cb = OrderCallback.unpack(callback.data)
        order_id = unpacked_cb.order_id

        kb_builder = InlineKeyboardBuilder()

        # Defensive check: Order ID must be set
        if order_id == -1:
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return "❌ <b>Error: Invalid Order ID</b>", kb_builder

        try:
            # Get user to clear cart
            user = await UserRepository.get_by_tgid(callback.from_user.id, session)

            # Check if we have stored grace period status (from Level 4)
            use_stored_status = False
            stored_grace_status = False

            if state:
                state_data = await state.get_data()
                stored_grace_status = state_data.get("cancel_grace_status", False)
                stored_timestamp = state_data.get("cancel_grace_timestamp")

                # If stored timestamp exists and is < 10 seconds old, use stored status
                if stored_timestamp:
                    time_since_stored = datetime.utcnow().timestamp() - stored_timestamp
                    if time_since_stored < 10:  # 10 seconds grace period for confirmation
                        use_stored_status = True

            # Cancel order (will calculate grace period internally)
            within_grace_period, msg = await OrderService.cancel_order_by_user(
                order_id=order_id,
                session=session
            )

            # Override with stored status if within 10 second window
            if use_stored_status:
                within_grace_period = stored_grace_status

            # Clear cart (order was cancelled, items are back in stock)
            cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)

            # Commit changes (wallet refund, order status update, item release, cart clearing)
            await session_commit(session)

            # Clear FSM state
            if state:
                await state.clear()

            # Display appropriate message
            if within_grace_period:
                message_text = Localizator.get_text(BotEntity.USER, "order_cancelled_free")
            else:
                message_text = Localizator.get_text(BotEntity.USER, "order_cancelled_with_strike").format(
                    grace_period=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
                )

            # Back to cart button
            kb_builder.row(CartCallback.create(0).get_back_button(0))

            return message_text, kb_builder

        except ValueError as e:
            # Order not found or cannot be cancelled
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return f"❌ <b>Error:</b> {str(e)}", kb_builder

    # ========================================
    # Private Helper Methods
    # ========================================

    @staticmethod
    async def _format_payment_screen(
        invoice,
        order,
        session: AsyncSession | Session
    ) -> str:
        """
        Formats payment screen with invoice details and wallet usage.

        Args:
            invoice: Invoice DTO
            order: Order DTO
            session: Database session

        Returns:
            Formatted message string
        """
        from datetime import datetime
        from repositories.item import ItemRepository
        from repositories.subcategory import SubcategoryRepository

        # Calculate time remaining
        time_remaining = (order.expires_at - datetime.now()).total_seconds() / 60

        # Get order items and build items list
        order_items = await ItemRepository.get_by_order_id(order.id, session)
        items_dict = {}
        for item in order_items:
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            key = (subcategory.name, item.price)
            items_dict[key] = items_dict.get(key, 0) + 1

        items_list = ""
        subtotal = 0.0
        for (name, price), qty in items_dict.items():
            line_total = price * qty
            items_list += f"{qty}x {name}\n  {Localizator.get_currency_symbol()}{price:.2f} × {qty}{' ' * (20 - len(name))}{Localizator.get_currency_symbol()}{line_total:.2f}\n"
            subtotal += line_total

        # Shipping line
        shipping_line = ""
        if order.shipping_cost > 0:
            shipping_line = f"Shipping{' ' * 18}{Localizator.get_currency_symbol()}{order.shipping_cost:.2f}\n"

        # Format wallet used (if any)
        wallet_line = ""
        wallet_spacing = ""
        if order.wallet_used > 0:
            wallet_spacing = " " * 11
            wallet_line = Localizator.get_text(BotEntity.USER, "payment_wallet_line").format(
                wallet_used=order.wallet_used,
                wallet_spacing=wallet_spacing,
                currency_sym=Localizator.get_currency_symbol()
            )

        # Calculate spacing for alignment
        subtotal_spacing = " " * 18
        total_spacing = " " * 23
        crypto_spacing = " " * 11

        # Format date and time
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        expires_time = order.expires_at.strftime("%H:%M")

        message_text = Localizator.get_text(BotEntity.USER, "payment_required_screen").format(
            invoice_number=invoice.invoice_number,
            date=date_str,
            items_list=items_list,
            subtotal=subtotal,
            subtotal_spacing=subtotal_spacing,
            shipping_line=shipping_line,
            total=order.total_price,
            total_spacing=total_spacing,
            currency_sym=Localizator.get_currency_symbol(),
            wallet_line=wallet_line,
            crypto_spacing=crypto_spacing,
            payment_address=invoice.payment_address,
            crypto_amount=invoice.payment_amount_crypto,
            crypto_currency=invoice.payment_crypto_currency.value,
            crypto_amount_fiat=invoice.fiat_amount,
            time_remaining=int(time_remaining),
            expires_time=expires_time
        )

        return message_text

    @staticmethod
    async def _calculate_order_totals(
        cart_items: list[CartItemDTO],
        session: AsyncSession | Session
    ) -> tuple[float, float]:
        """
        Calculate order totals: item prices + max shipping cost.

        Args:
            cart_items: List of cart items
            session: Database session

        Returns:
            Tuple of (total_price_with_shipping, max_shipping_cost)
        """
        total_price = 0.0
        max_shipping_cost = 0.0  # Use MAX shipping cost, not SUM!

        for cart_item in cart_items:
            # Get price
            item_dto = ItemDTO(
                category_id=cart_item.category_id,
                subcategory_id=cart_item.subcategory_id
            )
            price = await ItemRepository.get_price(item_dto, session)
            total_price += price * cart_item.quantity

            # Get shipping cost (only for physical items)
            # Note: We use MAX shipping cost across all items, not SUM
            repository_item = await ItemRepository.get_single(
                cart_item.category_id,
                cart_item.subcategory_id,
                session
            )
            if repository_item and repository_item.is_physical:
                max_shipping_cost = max(max_shipping_cost, repository_item.shipping_cost)

        # Add shipping cost to total
        total_price_with_shipping = total_price + max_shipping_cost

        logging.info(
            f"📦 Order totals: Items={total_price:.2f} EUR | "
            f"Shipping={max_shipping_cost:.2f} EUR (MAX) | "
            f"Total={total_price_with_shipping:.2f} EUR"
        )

        return total_price_with_shipping, max_shipping_cost

    @staticmethod
    async def _reserve_items_with_adjustments(
        cart_items: list[CartItemDTO],
        order_id: int,
        session: AsyncSession | Session
    ) -> tuple[list, list[dict]]:
        """
        Reserve items for order and track stock adjustments.

        Args:
            cart_items: List of cart items
            order_id: Order ID
            session: Database session

        Returns:
            Tuple of (reserved_items, stock_adjustments)
            - reserved_items: List of reserved Item objects
            - stock_adjustments: List of adjustment dicts with subcategory info

        Raises:
            ValueError: If all items are out of stock
        """
        from repositories.subcategory import SubcategoryRepository

        reserved_items = []
        stock_adjustments = []

        for cart_item in cart_items:
            reserved, requested = await ItemRepository.reserve_items_for_order(
                cart_item.subcategory_id,
                cart_item.quantity,
                order_id,
                session
            )

            # Track if quantity changed
            if len(reserved) != requested:
                subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
                stock_adjustments.append({
                    'subcategory_id': cart_item.subcategory_id,
                    'subcategory_name': subcategory.name,
                    'requested': requested,
                    'reserved': len(reserved)
                })
                logging.warning(
                    f"⚠️ Stock adjustment: {subcategory.name} - "
                    f"Requested: {requested}, Reserved: {len(reserved)}"
                )

            reserved_items.extend(reserved)

        # Check: All items out of stock?
        if not reserved_items:
            await OrderRepository.update_status(order_id, OrderStatus.CANCELLED_BY_SYSTEM, session)
            logging.error(f"❌ Order {order_id} cancelled - all items out of stock")
            raise ValueError("All items are out of stock")

        return reserved_items, stock_adjustments

    @staticmethod
    def _detect_physical_items(reserved_items: list) -> bool:
        """
        Detect if order contains physical items requiring shipment.

        Args:
            reserved_items: List of reserved Item objects

        Returns:
            True if any item is physical, False otherwise
        """
        return any(item.is_physical for item in reserved_items)

    @staticmethod
    async def _format_wallet_payment_invoice(
        invoice,
        order,
        session: AsyncSession | Session
    ) -> str:
        """
        Format invoice for wallet-only payment (order completed).
        Shows different delivery status for physical vs digital items.

        Returns:
            Formatted invoice message
        """
        from repositories.item import ItemRepository
        from repositories.subcategory import SubcategoryRepository
        from datetime import datetime

        # Get order items
        order_items = await ItemRepository.get_by_order_id(order.id, session)

        # Check if order contains physical items
        has_physical_items = any(item.is_physical for item in order_items)

        # Build items list
        items_dict = {}
        for item in order_items:
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            key = (subcategory.name, item.price)
            items_dict[key] = items_dict.get(key, 0) + 1

        items_list = ""
        subtotal = 0.0
        for (name, price), qty in items_dict.items():
            line_total = price * qty
            items_list += f"{qty}x {name}\n  {Localizator.get_currency_symbol()}{price:.2f} × {qty}{' ' * (20 - len(name))}{Localizator.get_currency_symbol()}{line_total:.2f}\n"
            subtotal += line_total

        # Shipping line
        shipping_line = ""
        if order.shipping_cost > 0:
            shipping_line = f"Shipping{' ' * 18}{Localizator.get_currency_symbol()}{order.shipping_cost:.2f}\n"

        # Calculate spacing for alignment
        subtotal_spacing = " " * 18
        total_spacing = " " * 23
        wallet_spacing = " " * 20

        # Format date
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Choose localization key based on item type
        if has_physical_items:
            localization_key = "order_completed_wallet_only_physical"
        else:
            localization_key = "order_completed_wallet_only_digital"

        return Localizator.get_text(BotEntity.USER, localization_key).format(
            invoice_number=invoice.invoice_number,
            date=date_str,
            items_list=items_list,
            subtotal=subtotal,
            subtotal_spacing=subtotal_spacing,
            shipping_line=shipping_line,
            total=order.total_price,
            total_spacing=total_spacing,
            wallet_used=invoice.fiat_amount,
            wallet_spacing=wallet_spacing,
            currency_sym=Localizator.get_currency_symbol()
        )