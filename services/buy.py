from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from models.buy import BuyDTO
from repositories.buy import BuyRepository
from repositories.item import ItemRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from utils.localizator import Localizator


class BuyService:

    @staticmethod
    async def refund(buy_dto: BuyDTO, session: AsyncSession | Session) -> str:
        refund_data = await BuyRepository.get_refund_data_single(buy_dto.id, session)
        buy = await BuyRepository.get_by_id(buy_dto.id, session)
        buy.is_refunded = True
        await BuyRepository.update(buy, session)
        user = await UserRepository.get_by_tgid(refund_data.telegram_id, session)
        # Refund: Add money back to wallet (rounded to 2 decimals)
        user.top_up_amount = round(user.top_up_amount + refund_data.total_price, 2)
        await UserRepository.update(user, session)
        await session_commit(session)
        await NotificationService.refund(refund_data)
        if refund_data.telegram_username:
            return Localizator.get_text(BotEntity.ADMIN, "successfully_refunded_with_username").format(
                total_price=refund_data.total_price,
                telegram_username=refund_data.telegram_username,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                currency_sym=Localizator.get_currency_symbol())
        else:
            return Localizator.get_text(BotEntity.ADMIN, "successfully_refunded_with_tgid").format(
                total_price=refund_data.total_price,
                telegram_id=refund_data.telegram_id,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                currency_sym=Localizator.get_currency_symbol())

    @staticmethod
    async def get_purchase(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        from repositories.order import OrderRepository
        from repositories.invoice import InvoiceRepository
        from enums.order_status import OrderStatus

        unpacked_cb = MyProfileCallback.unpack(callback.data)
        items = await ItemRepository.get_by_buy_id(unpacked_cb.args_for_action, session)

        # Get order information via first item's order_id
        order = None
        invoice_numbers = []
        if items and items[0].order_id:
            order = await OrderRepository.get_by_id(items[0].order_id, session)

            # Get ALL invoices for this order (multiple invoices in case of underpayment)
            invoices = await InvoiceRepository.get_all_by_order_id(order.id, session)
            if invoices:
                invoice_numbers = [inv.invoice_number for inv in invoices]
            else:
                # Fallback for orders without invoice (should not happen in normal flow)
                from datetime import datetime
                fallback_ref = f"ORDER-{datetime.now().year}-{order.id:06d}"
                invoice_numbers = [fallback_ref]

        # Build detailed message if order exists
        if order:
            # Format status
            if order.status == OrderStatus.SHIPPED:
                status = Localizator.get_text(BotEntity.USER, "order_status_shipped")
            elif order.status == OrderStatus.PAID_AWAITING_SHIPMENT:
                status = Localizator.get_text(BotEntity.USER, "order_status_awaiting_shipment")
            else:
                status = Localizator.get_text(BotEntity.USER, "order_status_paid")

            # Format created_at (order placement time)
            created_at_str = order.created_at.strftime("%d.%m.%Y %H:%M") if order.created_at else "N/A"

            # Format paid_at_info - only show if payment timestamp exists
            paid_at_info = ""
            if order.paid_at:
                paid_at_str = order.paid_at.strftime("%d.%m.%Y %H:%M")
                paid_at_info = Localizator.get_text(BotEntity.USER, "order_paid_on").format(
                    paid_at=paid_at_str
                )

            # Format shipped_info
            shipped_info = ""
            if order.shipped_at:
                shipped_at_str = order.shipped_at.strftime("%d.%m.%Y %H:%M")
                shipped_info = Localizator.get_text(BotEntity.USER, "order_shipped_on").format(
                    shipped_at=shipped_at_str
                )

            # Build items list with descriptions and optionally private_data
            items_list = ""
            for idx, item in enumerate(items, 1):
                items_list += f"{idx}. {item.description}\n"
                # Add private_data if available (for payment confirmation)
                if item.private_data:
                    items_list += f"   <code>{item.private_data}</code>\n"

            # Calculate subtotal (total - shipping)
            subtotal = order.total_price - order.shipping_cost

            # Build shipping line
            shipping_line = ""
            if order.shipping_cost > 0:
                shipping_line = f"<b>Versandkosten:</b> {Localizator.get_currency_symbol()}{order.shipping_cost:.2f}\n"

            # Format invoice numbers (one per line for multiple invoices)
            invoice_numbers_formatted = "\n".join(invoice_numbers)

            msg = Localizator.get_text(BotEntity.USER, "order_details").format(
                invoice_number=invoice_numbers_formatted,
                created_at=created_at_str,
                status=status,
                paid_at_info=paid_at_info,
                shipped_info=shipped_info,
                items_list=items_list,
                currency_sym=Localizator.get_currency_symbol(),
                subtotal=subtotal,
                shipping_line=shipping_line,
                total=order.total_price
            )

            # Add retention notice if private_data is included
            if any(item.private_data for item in items):
                msg += Localizator.get_text(BotEntity.USER, "purchased_items_retention_notice").format(
                    retention_days=config.DATA_RETENTION_DAYS
                )
        else:
            # Fallback to old message format if no order found
            msg = MessageService.create_message_with_bought_items(items)

        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(unpacked_cb.get_back_button())
        return msg, kb_builder
