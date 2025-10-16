from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_commit
from enums.cryptocurrency import Cryptocurrency
from enums.order_status import OrderStatus
from models.cartItem import CartItemDTO
from models.item import ItemDTO
from models.order import OrderDTO
from repositories.item import ItemRepository
from repositories.order import OrderRepository
from services.invoice import InvoiceService


class OrderService:

    @staticmethod
    async def create_order_from_cart(
        user_id: int,
        cart_items: list[CartItemDTO],
        crypto_currency: Cryptocurrency,
        session: AsyncSession | Session
    ) -> OrderDTO:
        """
        Erstellt Order aus Cart-Items mit Reservierung und Invoice.

        Args:
            user_id: User ID
            cart_items: Cart-Items
            crypto_currency: Gewählte Crypto-Währung für Payment
            session: DB Session

        Returns:
            OrderDTO

        Raises:
            ValueError: Bei insufficient stock
        """

        # 1. Berechne Total und prüfe Stock
        total_price = 0.0
        reserved_items = []

        for cart_item in cart_items:
            # Hole Preis
            item_dto = ItemDTO(
                category_id=cart_item.category_id,
                subcategory_id=cart_item.subcategory_id
            )
            price = await ItemRepository.get_price(item_dto, session)
            total_price += price * cart_item.quantity

        # 2. Erstelle Order
        expires_at = datetime.now() + timedelta(minutes=config.ORDER_TIMEOUT_MINUTES)

        order_dto = OrderDTO(
            user_id=user_id,
            status=OrderStatus.PENDING_PAYMENT,
            total_price=total_price,
            currency=config.CURRENCY,
            expires_at=expires_at
        )

        order_id = await OrderRepository.create(order_dto, session)
        order_dto.id = order_id

        # 3. Reserviere Items (mit SELECT FOR UPDATE in Repository!)
        try:
            for cart_item in cart_items:
                items = await ItemRepository.reserve_items_for_order(
                    cart_item.subcategory_id,
                    cart_item.quantity,
                    order_id,
                    session
                )
                reserved_items.extend(items)
        except ValueError as e:
            # Stock nicht ausreichend → Exception durchreichen
            raise e

        # 4. Erstelle Invoice
        await InvoiceService.create_invoice_with_kryptoexpress(
            order_id=order_id,
            fiat_amount=total_price,
            fiat_currency=config.CURRENCY,
            crypto_currency=crypto_currency,
            session=session
        )

        return order_dto

    @staticmethod
    async def complete_order_payment(
        order_id: int,
        session: AsyncSession | Session
    ):
        """
        Schließt Order ab nach erfolgreichem Payment.
        - Markiert Items als verkauft
        - Setzt Order-Status auf PAID
        """

        # Hole Items der Order
        items = await ItemRepository.get_by_order_id(order_id, session)

        # Markiere als verkauft
        for item in items:
            item.is_sold = True

        await ItemRepository.update(items, session)

        # Update Order Status
        await OrderRepository.update_status(order_id, OrderStatus.PAID, session)
        await session_commit(session)