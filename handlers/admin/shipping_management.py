from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import ShippingManagementCallback, AdminMenuCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.order_status import OrderStatus
from repositories.invoice import InvoiceRepository
from repositories.order import OrderRepository
from repositories.user import UserRepository
from services.notification import NotificationService
from services.shipping import ShippingService
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator

shipping_management_router = Router()


async def show_awaiting_shipment_orders(**kwargs):
    """Level 0: Shows list of orders awaiting shipment"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")

    # Get all orders with PAID_AWAITING_SHIPMENT status
    orders = await OrderRepository.get_orders_awaiting_shipment(session)

    if not orders:
        # No orders awaiting shipment
        message_text = Localizator.get_text(BotEntity.ADMIN, "no_orders_awaiting_shipment")
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=Localizator.get_text(BotEntity.ADMIN, "back_to_menu"),
            callback_data=AdminMenuCallback.create(level=0).pack()
        )
    else:
        # Show list of orders
        message_text = Localizator.get_text(BotEntity.ADMIN, "awaiting_shipment_orders") + "\n\n"

        kb_builder = InlineKeyboardBuilder()

        for order in orders:
            # Get invoice number for display
            invoice = await InvoiceRepository.get_by_order_id(order.id, session)
            user = await UserRepository.get_by_id(order.user_id, session)

            # Always show both username and ID
            if user.telegram_username:
                user_display = f"@{user.telegram_username} (ID:{user.telegram_id})"
            else:
                user_display = f"ID:{user.telegram_id}"

            # Handle orders without invoice (e.g., PENDING_SELECTION status after stock adjustment)
            if invoice:
                invoice_display = invoice.invoice_number
            else:
                from datetime import datetime
                invoice_display = f"ORDER-{datetime.now().year}-{order.id:06d}"

            # Format creation timestamp
            created_time = order.created_at.strftime("%d.%m %H:%M") if order.created_at else "N/A"

            button_text = f"📦 {created_time} | {invoice_display} | {user_display} | {order.total_price:.2f}{Localizator.get_currency_symbol()}"
            kb_builder.button(
                text=button_text,
                callback_data=ShippingManagementCallback.create(level=1, order_id=order.id).pack()
            )

        kb_builder.adjust(1)  # One button per row
        kb_builder.button(
            text=Localizator.get_text(BotEntity.ADMIN, "back_to_menu"),
            callback_data=AdminMenuCallback.create(level=0).pack()
        )

    if isinstance(callback, CallbackQuery):
        await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())


async def show_order_details(**kwargs):
    """Level 1: Shows order details with shipping address"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    callback_data = kwargs.get("callback_data")

    order_id = callback_data.order_id

    # Get order details
    order = await OrderRepository.get_by_id_with_items(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)
    user = await UserRepository.get_by_id(order.user_id, session)
    shipping_address = await ShippingService.get_shipping_address(order_id, session)

    username = f"@{user.telegram_username}" if user.telegram_username else str(user.telegram_id)

    # Get invoice number with fallback
    if invoice:
        invoice_number = invoice.invoice_number
    else:
        from datetime import datetime
        invoice_number = f"ORDER-{datetime.now().year}-{order_id:06d}"

    # Build message header with invoice number and user info
    message_text = Localizator.get_text(BotEntity.ADMIN, "order_details_header").format(
        invoice_number=invoice_number,
        username=username,
        user_id=user.telegram_id
    )

    message_text += "\n\n"

    # Digital items (delivered)
    digital_items = [item for item in order.items if not item.is_physical]
    digital_total = 0.0
    if digital_items:
        message_text += "<b>Digital:</b>\n"
        # Group by (description, price) and count quantities
        digital_grouped = {}
        for item in digital_items:
            key = (item.description, item.price)
            if key not in digital_grouped:
                digital_grouped[key] = 0
            digital_grouped[key] += 1

        for (description, price), qty in digital_grouped.items():
            line_total = qty * price
            digital_total += line_total
            if qty == 1:
                message_text += f"{qty} Stk. {description} {price:.2f}\n"
            else:
                message_text += f"{qty} Stk. {description} {price:.2f} = {line_total:.2f}\n"
        message_text += "\n"

    # Physical items (to be shipped)
    physical_items = [item for item in order.items if item.is_physical]
    physical_total = 0.0
    if physical_items:
        message_text += "<b>Versandartikel:</b>\n"
        # Group by (description, price) and count quantities
        physical_grouped = {}
        for item in physical_items:
            key = (item.description, item.price)
            if key not in physical_grouped:
                physical_grouped[key] = 0
            physical_grouped[key] += 1

        for (description, price), qty in physical_grouped.items():
            line_total = qty * price
            physical_total += line_total
            if qty == 1:
                message_text += f"{qty} Stk. {description} {price:.2f}\n"
            else:
                message_text += f"{qty} Stk. {description} {price:.2f} = {line_total:.2f}\n"
        message_text += "\n"

    # Price breakdown
    message_text += "═══════════════════════\n"
    if order.shipping_cost > 0:
        message_text += f"Versand {order.shipping_cost:.2f}\n\n"
    message_text += f"<b>Total: {order.total_price:.2f} {Localizator.get_currency_symbol()}</b>\n"
    message_text += "═══════════════════════\n"

    # Shipping address
    if shipping_address:
        message_text += "\n<b>Adressdaten:</b>\n"
        message_text += f"{shipping_address}"

    # Buttons
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text=Localizator.get_text(BotEntity.ADMIN, "mark_as_shipped"),
        callback_data=ShippingManagementCallback.create(level=2, order_id=order_id).pack()
    )
    kb_builder.button(
        text=Localizator.get_text(BotEntity.ADMIN, "cancel_order_admin"),
        callback_data=ShippingManagementCallback.create(level=4, order_id=order_id).pack()
    )
    kb_builder.adjust(1)
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "back_button"),
        callback_data=ShippingManagementCallback.create(level=0).pack()
    )

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())


async def mark_as_shipped_confirm(**kwargs):
    """Level 2: Confirmation before marking as shipped"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    callback_data = kwargs.get("callback_data")

    order_id = callback_data.order_id

    # Get invoice number for display
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)
    if invoice:
        invoice_number = invoice.invoice_number
    else:
        from datetime import datetime
        invoice_number = f"ORDER-{datetime.now().year}-{order_id:06d}"

    message_text = Localizator.get_text(BotEntity.ADMIN, "confirm_mark_shipped").format(invoice_number=invoice_number)

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "confirm"),
        callback_data=ShippingManagementCallback.create(level=3, order_id=order_id, confirmation=True).pack()
    )
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "cancel"),
        callback_data=ShippingManagementCallback.create(level=1, order_id=order_id).pack()
    )

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())


async def mark_as_shipped_execute(**kwargs):
    """Level 3: Execute mark as shipped"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    callback_data = kwargs.get("callback_data")

    order_id = callback_data.order_id

    # Update order status to SHIPPED
    await OrderRepository.update_status(order_id, OrderStatus.SHIPPED, session)
    await session_commit(session)

    # Send notification to user
    order = await OrderRepository.get_by_id(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)
    if invoice:
        invoice_number = invoice.invoice_number
    else:
        from datetime import datetime
        invoice_number = f"ORDER-{datetime.now().year}-{order_id:06d}"

    await NotificationService.order_shipped(order.user_id, invoice_number, session)

    # Success message
    message_text = Localizator.get_text(BotEntity.ADMIN, "order_marked_shipped").format(invoice_number=invoice_number)

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text=Localizator.get_text(BotEntity.ADMIN, "back_to_menu"),
        callback_data=ShippingManagementCallback.create(level=0).pack()
    )

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())


async def cancel_order_admin_confirm(**kwargs):
    """Level 4: Confirmation before cancelling order (admin)"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    callback_data = kwargs.get("callback_data")

    order_id = callback_data.order_id

    # Get invoice number for display
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)
    if invoice:
        invoice_number = invoice.invoice_number
    else:
        from datetime import datetime
        invoice_number = f"ORDER-{datetime.now().year}-{order_id:06d}"

    message_text = Localizator.get_text(BotEntity.ADMIN, "confirm_cancel_order_admin").format(
        invoice_number=invoice_number
    )

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "confirm"),
        callback_data=ShippingManagementCallback.create(level=5, order_id=order_id, confirmation=True).pack()
    )
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "cancel"),
        callback_data=ShippingManagementCallback.create(level=1, order_id=order_id).pack()
    )

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())


async def cancel_order_admin_execute(**kwargs):
    """Level 5: Execute order cancellation (admin)"""
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    callback_data = kwargs.get("callback_data")

    order_id = callback_data.order_id

    # Get order and invoice
    order = await OrderRepository.get_by_id(order_id, session)
    invoice = await InvoiceRepository.get_by_order_id(order_id, session)

    if invoice:
        invoice_number = invoice.invoice_number
    else:
        from datetime import datetime
        invoice_number = f"ORDER-{datetime.now().year}-{order_id:06d}"

    # Cancel order using OrderService
    from services.order import OrderService
    from enums.order_cancel_reason import OrderCancelReason

    await OrderService.cancel_order(
        order_id=order_id,
        reason=OrderCancelReason.ADMIN,
        session=session,
        refund_wallet=True  # Full refund, no penalty for admin cancellation
    )
    await session_commit(session)

    # Success message
    message_text = Localizator.get_text(BotEntity.ADMIN, "order_cancelled_by_admin").format(
        invoice_number=invoice_number
    )

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text=Localizator.get_text(BotEntity.ADMIN, "back_to_menu"),
        callback_data=ShippingManagementCallback.create(level=0).pack()
    )

    await callback.message.edit_text(message_text, reply_markup=kb_builder.as_markup())


@shipping_management_router.callback_query(AdminIdFilter(), ShippingManagementCallback.filter())
async def shipping_management_navigation(callback: CallbackQuery, callback_data: ShippingManagementCallback, session: AsyncSession | Session):
    current_level = callback_data.level

    levels = {
        0: show_awaiting_shipment_orders,
        1: show_order_details,
        2: mark_as_shipped_confirm,
        3: mark_as_shipped_execute,
        4: cancel_order_admin_confirm,
        5: cancel_order_admin_execute,
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
        "callback_data": callback_data,
    }

    await current_level_function(**kwargs)
