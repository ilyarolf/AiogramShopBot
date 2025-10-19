from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import AllCategoriesCallback, CartCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from handlers.common.common import add_pagination_buttons
from models.buy import BuyDTO
from models.buyItem import BuyItemDTO
from models.cartItem import CartItemDTO
from models.item import ItemDTO
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


class CartService:

    @staticmethod
    async def add_to_cart(callback: CallbackQuery, session: AsyncSession | Session):
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart = await CartRepository.get_or_create(user.id, session)
        cart_item = CartItemDTO(
            category_id=unpacked_cb.category_id,
            subcategory_id=unpacked_cb.subcategory_id,
            quantity=unpacked_cb.quantity,
            cart_id=cart.id
        )
        await CartRepository.add_to_cart(cart_item, cart, session)
        await session_commit(session)

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
        from datetime import datetime

        # Get invoice details
        invoice = await InvoiceRepository.get_by_order_id(order.id, session)

        # Calculate remaining time
        time_elapsed = (datetime.utcnow() - order.created_at).total_seconds() / 60  # Minutes
        time_remaining = config.ORDER_TIMEOUT_MINUTES - time_elapsed
        can_cancel_free = time_elapsed <= config.ORDER_CANCEL_GRACE_PERIOD_MINUTES
        is_expired = time_remaining <= 0

        # Format expiry time (HH:MM format)
        expires_at_time = order.expires_at.strftime("%H:%M")

        # Choose appropriate message based on expiry status
        if is_expired:
            localization_key = "order_expired"
        else:
            localization_key = "order_pending"

        # Create message with payment details
        message_text = Localizator.get_text(BotEntity.USER, localization_key).format(
            invoice_number=invoice.invoice_number,
            total_price=order.total_price,
            currency_sym=Localizator.get_currency_symbol(),
            crypto_amount=invoice.payment_amount_crypto,
            crypto_currency=invoice.payment_crypto_currency.value,
            payment_address=invoice.payment_address,
            expires_at=expires_at_time,
            expires_minutes=int(time_remaining) if time_remaining > 0 else 0
        )

        # Buttons
        kb_builder = InlineKeyboardBuilder()

        # Only show cancel button if not expired
        if not is_expired:
            # Cancel button with warning if grace period expired
            if can_cancel_free:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_free")
            else:
                cancel_text = Localizator.get_text(BotEntity.USER, "cancel_order_strike")

            kb_builder.button(
                text=cancel_text,
                callback_data=CartCallback.create(5, order_id=order.id)  # Level 5 = Cancel Order
            )

        return message_text, kb_builder

    @staticmethod
    async def delete_cart_item(callback: CallbackQuery, session: AsyncSession | Session):
        unpacked_cb = CartCallback.unpack(callback.data)
        cart_item_id = unpacked_cb.cart_item_id
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation:
            await CartItemRepository.remove_from_cart(cart_item_id, session)
            await session_commit(session)
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation_text"), kb_builder
        else:
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                              callback_data=CartCallback.create(1, cart_item_id=cart_item_id,
                                                                confirmation=True))
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                              callback_data=CartCallback.create(0))
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation"), kb_builder

    @staticmethod
    async def __create_checkout_msg(cart_items: list[CartItemDTO], session: AsyncSession | Session) -> str:
        message_text = Localizator.get_text(BotEntity.USER, "cart_confirm_checkout_process")
        message_text += "<b>\n\n"
        cart_grand_total = 0.0

        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            line_item_total = price * cart_item.quantity
            cart_line_item = Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                subcategory_name=subcategory.name, qty=cart_item.quantity,
                total_price=line_item_total, currency_sym=Localizator.get_currency_symbol()
            )
            cart_grand_total += line_item_total
            message_text += cart_line_item
        message_text += Localizator.get_text(BotEntity.USER, "cart_grand_total_string").format(
            cart_grand_total=cart_grand_total, currency_sym=Localizator.get_currency_symbol())
        message_text += "</b>"
        return message_text

    @staticmethod
    async def checkout_processing(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        message_text = await CartService.__create_checkout_msg(cart_items, session)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=CartCallback.create(3,
                                                            confirmation=True))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=CartCallback.create(0))
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
        is_enough_money = (user.top_up_amount - user.consume_records) >= cart_total
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
            user.consume_records = user.consume_records + cart_total
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
    async def get_crypto_selection_for_checkout(
        callback: CallbackQuery,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Shows crypto selection after checkout confirmation.
        Uses existing localization keys from wallet (btc_top_up, etc.)
        """
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

        # Check: Does user already have a pending order?
        pending_order = await OrderRepository.get_pending_order_by_user(user.id, session)
        if pending_order:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "pending_order_exists"), kb_builder

        # Check: Stock available?
        out_of_stock = []
        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            available = await ItemRepository.get_available_qty(item_dto, session)
            if available < cart_item.quantity:
                out_of_stock.append(cart_item)

        if out_of_stock:
            kb_builder = InlineKeyboardBuilder()
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            msg = Localizator.get_text(BotEntity.USER, "out_of_stock")
            for item in out_of_stock:
                subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
                msg += subcategory.name + "\n"
            return msg, kb_builder

        # Show crypto buttons
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
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Creates order + invoice after crypto selection.

        Flow:
        1. Get cart items
        2. Create order (incl. item reservation + invoice via KryptoExpress)
        3. Clear cart
        4. Show payment instructions
        """
        unpacked_cb = CartCallback.unpack(callback.data)
        crypto_currency = unpacked_cb.cryptocurrency

        if not crypto_currency:
            raise ValueError("No cryptocurrency selected")

        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)

        if not cart_items:
            kb_builder = InlineKeyboardBuilder()
            return Localizator.get_text(BotEntity.USER, "no_cart_items"), kb_builder

        kb_builder = InlineKeyboardBuilder()

        try:
            # Create order (incl. reservation + invoice)
            order = await OrderService.create_order_from_cart(
                user_id=user.id,
                cart_items=cart_items,
                crypto_currency=crypto_currency,
                session=session
            )

            # Clear cart
            for cart_item in cart_items:
                await CartItemRepository.remove_from_cart(cart_item.id, session)

            await session_commit(session)

            # Get invoice details for payment instructions
            from repositories.invoice import InvoiceRepository
            from datetime import datetime
            invoice = await InvoiceRepository.get_by_order_id(order.id, session)

            # Calculate remaining time for cancel button logic
            time_elapsed = (datetime.utcnow() - order.created_at).total_seconds() / 60  # Minutes
            can_cancel_free = time_elapsed <= config.ORDER_CANCEL_GRACE_PERIOD_MINUTES

            # Format expiry time (HH:MM format)
            expires_at_time = order.expires_at.strftime("%H:%M")

            # Success message with payment instructions
            message_text = Localizator.get_text(BotEntity.USER, "order_created_success").format(
                invoice_number=invoice.invoice_number,
                total_price=order.total_price,
                currency_sym=Localizator.get_currency_symbol(),
                crypto_amount=invoice.payment_amount_crypto,
                crypto_currency=invoice.payment_crypto_currency.value,
                payment_address=invoice.payment_address,
                expires_at=expires_at_time,
                expires_minutes=config.ORDER_TIMEOUT_MINUTES
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

        except ValueError as e:
            # Insufficient stock (despite previous check → race condition!)
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return str(e), kb_builder

    @staticmethod
    async def cancel_order(
        callback: CallbackQuery,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder]:
        """
        Cancels an order by the user.
        Checks grace period and displays appropriate message.
        """
        unpacked_cb = CartCallback.unpack(callback.data)
        order_id = unpacked_cb.order_id

        kb_builder = InlineKeyboardBuilder()

        # Defensive check: Order ID must be set
        if order_id == -1:
            kb_builder.row(CartCallback.create(0).get_back_button(0))
            return "❌ <b>Fehler: Ungültige Order-ID</b>", kb_builder

        try:
            # Cancel order
            from services.order import OrderService
            within_grace_period, msg = await OrderService.cancel_order_by_user(
                order_id=order_id,
                session=session
            )

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
            return f"❌ <b>Fehler:</b> {str(e)}", kb_builder
