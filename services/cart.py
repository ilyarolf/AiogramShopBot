from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import AllCategoriesCallback, CartCallback, OrderCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.order_status import OrderStatus
from handlers.common.common import add_pagination_buttons
from models.buy import BuyDTO
from models.buyItem import BuyItemDTO
from models.cartItem import CartItemDTO
from models.item import ItemDTO
from models.order import OrderDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.cartItem import CartItemRepository
from repositories.item import ItemRepository
from repositories.order import OrderRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from services.order import OrderService
from utils.localizator import Localizator


def format_crypto_amount(amount: float) -> str:
    """
    Formats crypto amount to avoid scientific notation.

    Examples:
        9e-06 BTC → 0.000009 BTC
        0.00042156 BTC → 0.00042156 BTC
        1.5 BTC → 1.5 BTC
    """
    # Format with enough decimal places for smallest crypto units
    # BTC has 8 decimals (satoshi), so we use 8 decimal places
    formatted = f"{amount:.8f}"
    # Remove trailing zeros after decimal point
    formatted = formatted.rstrip('0').rstrip('.')
    return formatted


class CartService:

    @staticmethod
    async def add_to_cart(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[bool, str, dict]:
        """
        Adds item to cart with stock validation.

        Returns:
            (success, message_key, format_args)
            - success: Whether item was added (False if out of stock)
            - message_key: Localization key for the message
            - format_args: Dict with format arguments for the message
        """
        from repositories.subcategory import SubcategoryRepository

        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart = await CartRepository.get_or_create(user.id, session)

        # Check available stock
        item_dto = ItemDTO(
            category_id=unpacked_cb.category_id,
            subcategory_id=unpacked_cb.subcategory_id
        )
        available = await ItemRepository.get_available_qty(item_dto, session)
        requested = unpacked_cb.quantity

        # Adjust quantity if needed
        actual_quantity = min(requested, available)

        if actual_quantity == 0:
            # Out of stock
            subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.subcategory_id, session)
            return False, "add_to_cart_out_of_stock", {"subcategory_name": subcategory.name}

        # Add to cart with actual quantity
        cart_item = CartItemDTO(
            category_id=unpacked_cb.category_id,
            subcategory_id=unpacked_cb.subcategory_id,
            quantity=actual_quantity,
            cart_id=cart.id
        )
        await CartRepository.add_to_cart(cart_item, cart, session)
        await session_commit(session)

        # Return appropriate message
        if actual_quantity < requested:
            return True, "add_to_cart_stock_reduced", {
                "actual_qty": actual_quantity,
                "requested_qty": requested
            }

        return True, "item_added_to_cart", {}

    @staticmethod
    async def create_buttons(message: Message | CallbackQuery, session: AsyncSession | Session):
        user = await UserRepository.get_by_tgid(message.from_user.id, session)

        # Check: Does user have a pending order? Show order instead of cart
        from enums.order_status import OrderStatus
        pending_order = await OrderRepository.get_pending_order_by_user(user.id, session)
        if pending_order:
            return await CartService.show_pending_order(pending_order, session)

        # Normal cart flow
        page = 0 if isinstance(message, Message) else CartCallback.unpack(message.data).page
        cart_items = await CartItemRepository.get_by_user_id(user.id, 0, session)
        kb_builder = InlineKeyboardBuilder()
        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                subcategory_name=subcategory.name,
                qty=cart_item.quantity,
                total_price=cart_item.quantity * price,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=CartCallback.create(1, page, cart_item_id=cart_item.id))
        if len(kb_builder.as_markup().inline_keyboard) > 0:
            cart = await CartRepository.get_or_create(user.id, session)
            unpacked_cb = CartCallback.create(0) if isinstance(message, Message) else CartCallback.unpack(message.data)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "checkout"),
                              callback_data=CartCallback.create(2, page, cart.id))
            kb_builder.adjust(1)
            kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                      CartItemRepository.get_maximum_page(user.id, session),
                                                      None)
            return Localizator.get_text(BotEntity.USER, "cart"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "no_cart_items"), kb_builder

    @staticmethod
    async def show_pending_order(order, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        """
        Displays a pending order with payment details and cancel option.
        Shows "expired" message if order has expired.
        """
        from repositories.invoice import InvoiceRepository
        from datetime import datetime, timedelta

        # Get invoice details
        invoice = await InvoiceRepository.get_by_order_id(order.id, session)

        # Calculate remaining time
        time_elapsed = (datetime.utcnow() - order.created_at).total_seconds() / 60  # Minutes
        time_remaining = config.ORDER_TIMEOUT_MINUTES - time_elapsed
        can_cancel_free = time_elapsed <= config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
        is_expired = time_remaining <= 0

        # Format expiry time (HH:MM format)
        expires_at_time = order.expires_at.strftime("%H:%M")

        # Handle orders without invoice yet (between order creation and payment processing)
        if not invoice:
            from repositories.item import ItemRepository
            from repositories.subcategory import SubcategoryRepository
            from collections import Counter

            kb_builder = InlineKeyboardBuilder()

            # Get order items to show detailed breakdown
            order_items = await ItemRepository.get_by_order_id(order.id, session)

            # Build items list with quantities
            items_by_subcategory = Counter()
            subcategory_prices = {}
            for item in order_items:
                items_by_subcategory[item.subcategory_id] += 1
                if item.subcategory_id not in subcategory_prices:
                    subcategory_prices[item.subcategory_id] = item.price

            # Format items list
            items_list = ""
            subtotal = 0.0
            for subcategory_id, qty in items_by_subcategory.items():
                subcategory = await SubcategoryRepository.get_by_id(subcategory_id, session)
                price = subcategory_prices[subcategory_id]
                line_total = price * qty
                subtotal += line_total

                # Format: "2x Product Name @ €5.00  €10.00"
                name_with_qty = f"{qty}x {subcategory.name}"
                spacing = " " * max(1, 30 - len(name_with_qty))
                items_list += f"{name_with_qty}\n  {Localizator.get_currency_symbol()}{price:.2f} × {qty}{spacing}{Localizator.get_currency_symbol()}{line_total:.2f}\n"

            # Calculate grace period remaining time
            grace_remaining = config.ORDER_CANCEL_GRACE_PERIOD_MINUTES - time_elapsed
            grace_expires_time = (order.created_at + timedelta(minutes=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES)).strftime("%H:%M")

            # Format grace period info
            if can_cancel_free:
                grace_period_info = Localizator.get_text(BotEntity.USER, "grace_period_active").format(
                    grace_remaining=int(grace_remaining),
                    grace_expires_time=grace_expires_time
                )
            else:
                grace_period_info = Localizator.get_text(BotEntity.USER, "grace_period_expired")

            # Show detailed pending order message based on status
            if order.status == OrderStatus.PENDING_PAYMENT_AND_ADDRESS:
                # Order created but waiting for shipping address
                message_text = Localizator.get_text(BotEntity.USER, "pending_order_awaiting_address").format(
                    items_list=items_list,
                    subtotal=subtotal,
                    shipping_cost=order.shipping_cost,
                    total_price=order.total_price,
                    currency_sym=Localizator.get_currency_symbol(),
                    expires_at=expires_at_time,
                    time_remaining=int(time_remaining),
                    grace_period_info=grace_period_info
                )

                # Button: Enter shipping address (redirect back to checkout which will trigger address input)
                kb_builder.button(
                    text=Localizator.get_text(BotEntity.USER, "enter_shipping_address"),
                    callback_data=CartCallback.create(level=2, order_id=order.id)  # Level 2 = Checkout (will detect pending order and set FSM state)
                )
            else:
                # Order created, address entered, waiting for payment
                message_text = Localizator.get_text(BotEntity.USER, "pending_order_awaiting_payment").format(
                    items_list=items_list,
                    subtotal=subtotal,
                    shipping_cost=order.shipping_cost,
                    total_price=order.total_price,
                    currency_sym=Localizator.get_currency_symbol(),
                    expires_at=expires_at_time,
                    time_remaining=int(time_remaining),
                    grace_period_info=grace_period_info
                )

                # Button: Continue to payment
                kb_builder.button(
                    text=Localizator.get_text(BotEntity.USER, "continue_to_payment"),
                    callback_data=OrderCallback.create(level=3, order_id=order.id)  # Level 3 = Payment Processing
                )

            # Add cancel button
            if can_cancel_free:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_free")
            else:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_strike")

            kb_builder.button(
                text=cancel_text,
                callback_data=OrderCallback.create(level=4, order_id=order.id)  # Level 4 = Cancel Order
            )

            return message_text, kb_builder

        # Check if order is expired
        if is_expired:
            # Cancel the expired order
            from enums.order_cancel_reason import OrderCancelReason
            import logging

            try:
                await OrderService.cancel_order(
                    order_id=order.id,
                    reason=OrderCancelReason.TIMEOUT,
                    session=session,
                    refund_wallet=True
                )
                await session_commit(session)
                logging.info(f"Auto-cancelled expired order {order.id} for user")
            except Exception as e:
                logging.warning(f"Could not auto-cancel expired order {order.id}: {e}")

            # Return empty cart message instead of expired order details
            kb_builder = InlineKeyboardBuilder()
            message_text = Localizator.get_text(BotEntity.USER, "order_expired").format(
                invoice_number=invoice.invoice_number,
                total_price=order.total_price,
                currency_sym=Localizator.get_currency_symbol(),
                crypto_amount=format_crypto_amount(invoice.payment_amount_crypto),
                crypto_currency=invoice.payment_crypto_currency.value,
                payment_address=invoice.payment_address,
                expires_at=expires_at_time,
                expires_minutes=0
            )
            message_text += f"\n\n{Localizator.get_text(BotEntity.USER, 'no_cart_items')}"
            return message_text, kb_builder

        # Order is still active - show payment details with new invoice format
        from services.order import OrderService
        message_text = await OrderService._format_payment_screen(
            invoice=invoice,
            order=order,
            session=session
        )

        # Add grace period warning if expired
        if not can_cancel_free:
            # Choose warning based on whether wallet was used (processing fee only applies if wallet was used)
            if order.wallet_used > 0:
                # Wallet was used -> Strike + Processing Fee
                grace_period_warning = Localizator.get_text(BotEntity.USER, "grace_period_expired_warning_with_fee").format(
                    grace_period=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
                )
            else:
                # No wallet used -> Strike only (no fee since nothing to refund)
                grace_period_warning = Localizator.get_text(BotEntity.USER, "grace_period_expired_warning_no_fee").format(
                    grace_period=config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
                )
            message_text += f"\n\n{grace_period_warning}"

        # Buttons
        kb_builder = InlineKeyboardBuilder()

        # Show cancel button
        if True:
            # Cancel button with warning if grace period expired
            if can_cancel_free:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_free")
            else:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_strike")

            kb_builder.button(
                text=cancel_text,
                callback_data=OrderCallback.create(level=4, order_id=order.id)  # Level 4 = Cancel Order
            )

        return message_text, kb_builder

    @staticmethod
    async def delete_cart_item(callback: CallbackQuery, session: AsyncSession | Session):
        """
        Delete cart item and directly show updated cart.
        No confirmation needed - better UX.
        """
        unpacked_cb = CartCallback.unpack(callback.data)
        cart_item_id = unpacked_cb.cart_item_id

        # Delete item
        await CartItemRepository.remove_from_cart(cart_item_id, session)
        await session_commit(session)

        # Show updated cart directly
        return await CartService.create_buttons(callback, session)

    @staticmethod
    async def __create_checkout_msg(cart_items: list[CartItemDTO], session: AsyncSession | Session) -> str:
        message_text = Localizator.get_text(BotEntity.USER, "cart_confirm_checkout_process")
        message_text += "<b>\n\n"
        items_total = 0.0
        max_shipping_cost = 0.0
        has_physical_items = False

        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            line_item_total = price * cart_item.quantity
            cart_line_item = Localizator.get_text(BotEntity.USER, "cart_line_item_checkout").format(
                qty=cart_item.quantity,
                subcategory_name=subcategory.name,
                price=price,
                total=line_item_total,
                currency_sym=Localizator.get_currency_symbol()
            )
            items_total += line_item_total
            message_text += cart_line_item

            # Calculate shipping cost for physical items
            try:
                sample_item = await ItemRepository.get_single(
                    cart_item.category_id, cart_item.subcategory_id, session
                )
                if sample_item and sample_item.is_physical:
                    has_physical_items = True
                    if sample_item.shipping_cost > max_shipping_cost:
                        max_shipping_cost = sample_item.shipping_cost
            except:
                # If no items available, skip shipping calculation
                pass

        # Show breakdown with shipping
        message_text += "\n"
        message_text += Localizator.get_text(BotEntity.USER, "cart_separator") + "\n"
        message_text += Localizator.get_text(BotEntity.USER, "cart_items_total").format(
            items_total=items_total, currency_sym=Localizator.get_currency_symbol()
        ) + "\n"

        if has_physical_items and max_shipping_cost > 0:
            message_text += Localizator.get_text(BotEntity.USER, "cart_shipping_cost").format(
                shipping_cost=max_shipping_cost, currency_sym=Localizator.get_currency_symbol()
            ) + "\n"

        message_text += Localizator.get_text(BotEntity.USER, "cart_separator") + "\n"
        cart_grand_total = items_total + max_shipping_cost
        message_text += Localizator.get_text(BotEntity.USER, "cart_total_with_shipping").format(
            total=cart_grand_total, currency_sym=Localizator.get_currency_symbol()
        )
        message_text += "</b>"
        return message_text

    @staticmethod
    async def checkout_processing(callback: CallbackQuery, session: AsyncSession | Session, state=None) -> tuple[str, InlineKeyboardBuilder]:
        """
        Checkout processing - shows order summary with pricing breakdown.
        Always shows checkout confirmation first, then proceeds based on item types.
        """
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

        # Show checkout confirmation with price breakdown
        message_text = await CartService.__create_checkout_msg(cart_items, session)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=CartCallback.create(3,
                                                            confirmation=True))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=CartCallback.create(0))
        return message_text, kb_builder




    @staticmethod
    async def _show_crypto_selection(order_id: int) -> tuple[str, InlineKeyboardBuilder]:
        """
        Shows crypto selection buttons for payment.

        Args:
            order_id: Order ID

        Returns:
            Tuple of (message, keyboard)
        """
        kb_builder = InlineKeyboardBuilder()

        # Crypto buttons - use OrderCallback for order domain
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "btc_button"),
            callback_data=OrderCallback.create(level=3, cryptocurrency=Cryptocurrency.BTC, order_id=order_id)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "ltc_button"),
            callback_data=OrderCallback.create(level=3, cryptocurrency=Cryptocurrency.LTC, order_id=order_id)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "sol_button"),
            callback_data=OrderCallback.create(level=3, cryptocurrency=Cryptocurrency.SOL, order_id=order_id)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "eth_button"),
            callback_data=OrderCallback.create(level=3, cryptocurrency=Cryptocurrency.ETH, order_id=order_id)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "bnb_button"),
            callback_data=OrderCallback.create(level=3, cryptocurrency=Cryptocurrency.BNB, order_id=order_id)
        )

        kb_builder.adjust(1)  # One button per row

        # Cancel button
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "cancel_order"),
            callback_data=OrderCallback.create(level=4, order_id=order_id)  # Cancel = Level 4
        )

        message_text = Localizator.get_text(BotEntity.USER, "choose_payment_crypto")

        return message_text, kb_builder

    @staticmethod
    async def buy_processing(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = CartCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        cart_total = 0.0
        out_of_stock = []
        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            cart_total += price * cart_item.quantity
            is_in_stock = await ItemRepository.get_available_qty(item_dto, session) >= cart_item.quantity
            if is_in_stock is False:
                out_of_stock.append(cart_item)
        # Round for comparison to avoid floating-point errors
        is_enough_money = round(user.top_up_amount, 2) >= round(cart_total, 2)
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation and len(out_of_stock) == 0 and is_enough_money:
            sold_items = []
            msg = ""
            for cart_item in cart_items:
                price = await ItemRepository.get_price(ItemDTO(category_id=cart_item.category_id,
                                                               subcategory_id=cart_item.subcategory_id), session)
                purchased_items = await ItemRepository.get_purchased_items(cart_item.category_id,
                                                                           cart_item.subcategory_id, cart_item.quantity, session)
                buy_dto = BuyDTO(buyer_id=user.id, quantity=cart_item.quantity, total_price=cart_item.quantity * price)
                buy_id = await BuyRepository.create(buy_dto, session)
                buy_item_dto_list = [BuyItemDTO(item_id=item.id, buy_id=buy_id) for item in purchased_items]
                await BuyItemRepository.create_many(buy_item_dto_list, session)
                for item in purchased_items:
                    item.is_sold = True
                await ItemRepository.update(purchased_items, session)
                await CartItemRepository.remove_from_cart(cart_item.id, session)
                sold_items.append(cart_item)
                msg += MessageService.create_message_with_bought_items(purchased_items)
            # Deduct from wallet (rounded to 2 decimals)
            user.top_up_amount = round(user.top_up_amount - cart_total, 2)
            await UserRepository.update(user, session)
            await session_commit(session)
            await NotificationService.new_buy(sold_items, user, session)
            return msg, kb_builder
        elif unpacked_cb.confirmation is False:
            kb_builder.row(unpacked_cb.get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "purchase_confirmation_declined"), kb_builder
        elif is_enough_money is False:
            kb_builder.row(unpacked_cb.get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "insufficient_funds"), kb_builder
        elif len(out_of_stock) > 0:
            kb_builder.row(unpacked_cb.get_back_button(0))
            msg = Localizator.get_text(BotEntity.USER, "out_of_stock")
            for item in out_of_stock:
                subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
                msg += subcategory.name + "\n"
            return msg, kb_builder

    # ========================================
    # NEW INVOICE-BASED CHECKOUT METHODS
    # ========================================

    @staticmethod
    async def _check_shipping_address_required(
        cart_items: list[CartItemDTO],
        session: AsyncSession | Session,
        state
    ) -> tuple[str, InlineKeyboardBuilder] | None:
        """
        Checks if cart has physical items and triggers address collection if needed.

        Returns:
            Tuple of (message, keyboard) if address collection needed, None otherwise
        """
        from services.shipping import ShippingService
        from handlers.user.shipping_states import ShippingAddressStates

        # Check: Does cart have physical items requiring shipping address?
        has_physical_items = await ShippingService.check_cart_has_physical_items(cart_items, session)

        # Check if FSM state has shipping address already
        has_shipping_address = False
        if state:
            state_data = await state.get_data()
            has_shipping_address = state_data.get("shipping_address") is not None

        if has_physical_items and not has_shipping_address and state is not None:
            # Physical items detected, no address yet → Start shipping address collection FSM
            await state.set_state(ShippingAddressStates.waiting_for_address)

            # Show address request message with retention period
            message_text = Localizator.get_text(BotEntity.USER, "shipping_address_request").format(
                retention_days=config.DATA_RETENTION_DAYS
            )
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                callback_data=CartCallback.create(0)
            )
            return message_text, kb_builder

        return None

    @staticmethod
    async def _check_pending_order_exists(
        user_id: int,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder] | None:
        """
        Checks if user already has a pending order.

        Returns:
            Tuple of (message, keyboard) if pending order exists, None otherwise
        """
        pending_order = await OrderRepository.get_pending_order_by_user(user_id, session)
        if pending_order:
            # Show full pending order details instead of simple message
            return await CartService.show_pending_order(pending_order, session)
        return None

    @staticmethod
    async def _handle_wallet_only_payment(
        user_id: int,
        cart_items: list[CartItemDTO],
        callback: CallbackQuery,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder] | None:
        """
        Handles wallet-only payment when wallet balance is sufficient.
        Creates order, handles stock adjustments, clears cart, sends notifications.

        Returns:
            Tuple of (message, keyboard) if wallet payment handled, None if wallet insufficient
        """
        from services.notification import NotificationService

        # Calculate cart total
        cart_total = 0.0
        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            cart_total += price * cart_item.quantity

        # Check if wallet balance is sufficient
        user = await UserRepository.get_by_id(user_id, session)
        wallet_balance = user.top_up_amount
        if wallet_balance < cart_total:
            return None  # Wallet insufficient → caller should show crypto selection

        # Wallet is sufficient → Create order directly
        try:
            order, stock_adjustments = await OrderService.create_order_from_cart(
                user_id=user_id,
                cart_items=cart_items,
                crypto_currency=Cryptocurrency.BTC,  # Dummy value (not used when wallet covers all)
                session=session
            )
        except ValueError as e:
            # All items out of stock - clear cart
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)

            await session_commit(session)

            # Check if wallet was refunded (from error message)
            wallet_refunded = "wallet_refunded=True" in str(e)
            desc_key = "all_items_out_of_stock_desc_with_wallet" if wallet_refunded else "all_items_out_of_stock_desc"

            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "back_to_cart"),
                callback_data=CartCallback.create(0)
            )
            message_text = (
                f"❌ <b>{Localizator.get_text(BotEntity.USER, 'all_items_out_of_stock')}</b>\n\n"
                f"{Localizator.get_text(BotEntity.USER, desc_key)}"
            )
            return message_text, kb_builder

        # Check if stock adjustments occurred
        if stock_adjustments:
            # Commit order before showing adjustment screen (user might click Cancel button)
            await session_commit(session)

            # Show stock adjustment confirmation screen
            return await CartService.show_stock_adjustment_confirmation(
                callback, order, stock_adjustments, session
            )

        # Clear cart
        for cart_item in cart_items:
            await CartItemRepository.remove_from_cart(cart_item.id, session)

        await session_commit(session)

        # Show success message
        kb_builder = InlineKeyboardBuilder()
        message_text = (
            f"✅ <b>Order Paid Successfully (Wallet)</b>\n\n"
            f"💰 <b>Total price:</b> {order.total_price:.2f} {Localizator.get_currency_symbol()}\n"
            f"💳 <b>Paid from wallet:</b> {order.wallet_used:.2f} {Localizator.get_currency_symbol()}\n\n"
            f"Your order is being processed!"
        )

        # Send notification to admin about new purchase
        await NotificationService.new_buy(cart_items, user, session)

        return message_text, kb_builder

    @staticmethod
    def _show_crypto_selection_screen() -> tuple[str, InlineKeyboardBuilder]:
        """
        Creates crypto selection screen with payment buttons.

        Returns:
            Tuple of (message, keyboard) with crypto payment options
        """
        message_text = Localizator.get_text(BotEntity.USER, "choose_payment_crypto")
        kb_builder = InlineKeyboardBuilder()

        # Crypto buttons (uses existing localization)
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.BTC)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "eth_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.ETH)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.LTC)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.SOL)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "bnb_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.BNB)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "usdt_trc20_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.USDT_TRC20)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "usdt_erc20_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.USDT_ERC20)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "usdc_erc20_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.USDC_ERC20)
        )

        kb_builder.adjust(2)
        kb_builder.row(CartCallback.create(0).get_back_button(0))

        return message_text, kb_builder

    @staticmethod
    async def create_order_and_reserve_items(
        user_id: int,
        cart_items: list[CartItemDTO],
        session: AsyncSession | Session
    ) -> tuple[OrderDTO | None, list[dict], bool]:
        """
        Creates order and reserves items atomically.
        Called at the beginning of checkout (Level 3) to reserve stock early.

        Returns:
            Tuple of (order, stock_adjustments, all_sold_out)
            - order: Created OrderDTO or None if all sold out
            - stock_adjustments: List of adjustments or empty list
            - all_sold_out: True if all items sold out
        """
        # Create order with PENDING_SELECTION (will be updated when user selects crypto)
        try:
            order, stock_adjustments = await OrderService.create_order_from_cart(
                user_id=user_id,
                cart_items=cart_items,
                crypto_currency=Cryptocurrency.PENDING_SELECTION,  # Updated when user selects crypto
                session=session
            )
            return order, stock_adjustments, False

        except ValueError as e:
            # All items out of stock
            return None, [], True

    @staticmethod
    async def get_crypto_selection_for_checkout(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        NEW FLOW (Option B): Creates order BEFORE crypto selection.

        Flow:
        1. Check shipping address requirement
        2. Check for existing pending orders
        3. Create order with PENDING_SELECTION (reserves stock atomically)
        4. If stock adjustments: Show adjustment screen
        5. If wallet sufficient: Complete order immediately
        6. Otherwise: Show crypto selection

        This ensures user sees stock adjustments BEFORE selecting crypto.
        """
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

        # Check: Shipping address required?
        shipping_check = await CartService._check_shipping_address_required(cart_items, session, state)
        if shipping_check:
            return shipping_check

        # Check: Does user already have a pending order?
        pending_check = await CartService._check_pending_order_exists(user.id, session)
        if pending_check:
            return pending_check

        # Create order with PENDING_SELECTION (stock check happens here!)
        order, stock_adjustments, all_sold_out = await CartService.create_order_and_reserve_items(
            user_id=user.id,
            cart_items=cart_items,
            session=session
        )

        # Case 1: All items sold out
        if all_sold_out:
            # Cart already cleared by create_order_and_reserve_items
            kb_builder = InlineKeyboardBuilder()
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "back_to_cart"),
                callback_data=CartCallback.create(0)
            )

            # Check if wallet was refunded (from error message)
            # Note: all_sold_out means ValueError was raised, we need to check cart history
            # For now, show generic message (wallet refund handled in OrderService)
            message_text = (
                f"❌ <b>{Localizator.get_text(BotEntity.USER, 'all_items_out_of_stock')}</b>\n\n"
                f"{Localizator.get_text(BotEntity.USER, 'all_items_out_of_stock_desc')}"
            )
            return message_text, kb_builder

        # Case 2: Stock adjustments occurred
        if stock_adjustments:
            # Save order_id to FSM for later (Level 9 or crypto selection)
            if state:
                await state.update_data(order_id=order.id)

            # Commit order before showing adjustment screen
            await session_commit(session)

            # Show adjustment screen
            return await CartService.show_stock_adjustment_confirmation(
                callback, order, stock_adjustments, session
            )

        # Case 3: No adjustments - check if wallet sufficient
        user = await UserRepository.get_by_id(user.id, session)  # Reload for wallet balance
        if order.status == OrderStatus.PAID:
            # Wallet covered full amount - complete order
            await OrderService.complete_order_payment(order.id, session)

            # Clear cart
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)

            await session_commit(session)

            # NOTE: NotificationService.new_buy() is NOT needed here
            # complete_order_payment() already handles:
            # - Creating Buy records for purchase history
            # - Sending items to user via DM
            # - Sending admin notification (if physical items)

            kb_builder = InlineKeyboardBuilder()
            message_text = (
                f"✅ <b>Order Paid Successfully (Wallet)</b>\n\n"
                f"💰 <b>Total price:</b> {order.total_price:.2f} {Localizator.get_currency_symbol()}\n"
                f"💳 <b>Paid from wallet:</b> {order.wallet_used:.2f} {Localizator.get_currency_symbol()}\n\n"
                f"Your order is being processed!"
            )
            return message_text, kb_builder

        # Case 4: Wallet insufficient - show crypto selection
        # Save order_id to FSM for Level 4
        if state:
            await state.update_data(order_id=order.id)

        # Commit order and FSM state before showing crypto selection
        await session_commit(session)

        # Show crypto selection
        return CartService._show_crypto_selection_screen()

    @staticmethod
    async def show_crypto_selection_without_physical_check(
        callback: CallbackQuery,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Shows crypto selection without checking for physical items.
        Used after shipping address has been confirmed.
        Similar to get_crypto_selection_for_checkout but skips physical item detection.
        """
        message_text = Localizator.get_text(BotEntity.USER, "choose_payment_crypto")
        kb_builder = InlineKeyboardBuilder()

        # Crypto buttons (uses existing localization)
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.BTC)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "eth_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.ETH)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.LTC)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.SOL)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "bnb_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.BNB)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "usdt_trc20_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.USDT_TRC20)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "usdt_erc20_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.USDT_ERC20)
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "usdc_erc20_top_up"),
            callback_data=CartCallback.create(4, cryptocurrency=Cryptocurrency.USDC_ERC20)
        )

        kb_builder.adjust(2)
        kb_builder.row(CartCallback.create(0).get_back_button(0))

        return message_text, kb_builder

    @staticmethod
    async def create_order_with_selected_crypto(
        callback: CallbackQuery,
        session: AsyncSession | Session,
        state=None
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Creates order + invoice after crypto selection.
        Automatically uses wallet balance.
        Saves shipping address from FSM state if present.

        Flow:
        1. Get cart items
        2. Extract shipping address from FSM state (if present)
        3. Create order (incl. wallet usage + item reservation + invoice)
        4. Save shipping address (if present)
        5. Clear cart and FSM state
        6. Show payment instructions (or success if fully paid by wallet)
        """
        from services.shipping import ShippingService

        unpacked_cb = CartCallback.unpack(callback.data)
        crypto_currency = unpacked_cb.cryptocurrency

        if not crypto_currency:
            raise ValueError("No cryptocurrency selected")

        # NEW FLOW (Option B - Step 2): Order already exists from Level 3
        # Just create invoice with selected crypto

        kb_builder = InlineKeyboardBuilder()

        # 1. Get order_id from FSM (saved in Level 3)
        if not state:
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return "❌ <b>Session expired.</b> Please checkout again.", kb_builder

        data = await state.get_data()
        order_id = data.get("order_id")
        shipping_address = data.get("shipping_address")

        if not order_id:
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return "❌ <b>Order not found.</b> Please checkout again.", kb_builder

        # 2. Load existing order
        order = await OrderRepository.get_by_id(order_id, session)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)

        # 3. Calculate remaining amount (wallet already deducted in Level 3)
        remaining_amount = order.total_price - order.wallet_used

        if remaining_amount <= 0:
            # Should not happen (wallet-only handled in Level 3)
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return "❌ <b>Error:</b> Order already paid.", kb_builder

        try:
            # 4. Create invoice for remaining amount
            await InvoiceService.create_invoice_with_kryptoexpress(
                order_id=order.id,
                fiat_amount=remaining_amount,
                fiat_currency=config.CURRENCY,
                crypto_currency=crypto_currency,
                session=session
            )

            # 5. Save shipping address if provided
            if shipping_address:
                from services.shipping import ShippingService
                await ShippingService.save_shipping_address(order.id, shipping_address, session)

            # 6. Clear cart (items already reserved in Level 3)
            cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)

            # 7. Clear FSM state
            if state:
                await state.clear()

            await session_commit(session)

            # 8. Get invoice and show payment screen
            from repositories.invoice import InvoiceRepository
            from datetime import datetime

            invoice = await InvoiceRepository.get_by_order_id(order.id, session)

            # Calculate remaining time for cancel button logic
            time_elapsed = (datetime.utcnow() - order.created_at).total_seconds() / 60  # Minutes
            can_cancel_free = time_elapsed <= config.ORDER_CANCEL_GRACE_PERIOD_MINUTES

            # Format expiry time (HH:MM format)
            expires_at_time = order.expires_at.strftime("%H:%M")

            # Build message with wallet usage info (if any)
            if order.wallet_used > 0:
                wallet_info = (
                    f"\n💳 <b>Wallet balance used:</b> {order.wallet_used:.2f} {Localizator.get_currency_symbol()}\n"
                    f"💰 <b>Remaining to pay:</b> {invoice.fiat_amount:.2f} {Localizator.get_currency_symbol()}\n"
                )
            else:
                wallet_info = ""

            # Success message with payment instructions
            message_text = (
                f"✅ <b>Order created successfully!</b>\n\n"
                f"📋 <b>Order ID:</b> <code>{invoice.invoice_number}</code>\n"
                f"💰 <b>Total price:</b> {order.total_price:.2f} {Localizator.get_currency_symbol()}"
                f"{wallet_info}\n"
                f"💳 <b>Payment details:</b>\n\n"
                f"🪙 <b>Amount to pay:</b>\n"
                f"<code>{format_crypto_amount(invoice.payment_amount_crypto)}</code> {invoice.payment_crypto_currency.value}\n\n"
                f"📬 <b>Payment address:</b>\n"
                f"<code>{invoice.payment_address}</code>\n\n"
                f"⏰ <b>Expires at:</b> {expires_at_time} ({config.ORDER_TIMEOUT_MINUTES} minutes)\n\n"
                f"<i>Please send the exact amount to the provided address. The order will be completed automatically after payment confirmation.</i>"
            )

            # Add cancel button with appropriate text
            if can_cancel_free:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_free")
            else:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_strike")

            kb_builder.button(
                text=cancel_text,
                callback_data=CartCallback.create(5, order_id=order.id)  # Level 5 = Cancel Order
            )

            return message_text, kb_builder

        except Exception as e:
            # Invoice creation failed or other error
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return f"❌ <b>Error:</b> {str(e)}", kb_builder



