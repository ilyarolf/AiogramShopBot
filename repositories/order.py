from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from db import session_execute, session_flush
from enums.order_status import OrderStatus
from models.order import Order, OrderDTO


class OrderRepository:

    @staticmethod
    async def create(order_dto: OrderDTO, session: Session | AsyncSession) -> int:
        """Creates a new order and returns the ID"""
        order = Order(**order_dto.model_dump(exclude_none=True))
        session.add(order)
        await session_flush(session)
        return order.id

    @staticmethod
    async def get_by_id(order_id: int, session: Session | AsyncSession) -> OrderDTO:
        """Gets order by ID"""
        stmt = select(Order).where(Order.id == order_id)
        order = await session_execute(stmt, session)
        return OrderDTO.model_validate(order.scalar_one(), from_attributes=True)

    @staticmethod
    async def get_by_id_with_items(order_id: int, session: Session | AsyncSession) -> Order:
        """Gets order with all items (for display)"""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        result = await session_execute(stmt, session)
        return result.scalar_one()

    @staticmethod
    async def get_pending_order_by_user(user_id: int, session: Session | AsyncSession) -> OrderDTO | None:
        """Gets pending order of a user (if exists)"""
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .where(Order.status == OrderStatus.PENDING_PAYMENT)
        )
        result = await session_execute(stmt, session)
        order = result.scalar_one_or_none()

        if order:
            return OrderDTO.model_validate(order, from_attributes=True)
        return None

    @staticmethod
    async def update(order_dto: OrderDTO, session: Session | AsyncSession) -> None:
        """Updates an order with all fields from the DTO"""
        order_dto_dict = order_dto.model_dump()
        none_keys = [k for k, v in order_dto_dict.items() if v is None]
        for k in none_keys:
            order_dto_dict.pop(k)

        stmt = update(Order).where(Order.id == order_dto.id).values(**order_dto_dict)
        await session.execute(stmt)

    @staticmethod
    async def update_status(order_id: int, status: OrderStatus, session: Session | AsyncSession):
        """Updates the status of an order"""
        timestamp_field = None

        if status == OrderStatus.PAID:
            timestamp_field = Order.paid_at
        elif status in [OrderStatus.CANCELLED_BY_USER, OrderStatus.CANCELLED_BY_ADMIN, OrderStatus.TIMEOUT]:
            timestamp_field = Order.cancelled_at
        elif status == OrderStatus.SHIPPED:
            timestamp_field = Order.shipped_at

        values = {"status": status}
        if timestamp_field is not None:
            values[timestamp_field.key] = datetime.now()

        stmt = update(Order).where(Order.id == order_id).values(**values)
        await session_execute(stmt, session)

    @staticmethod
    async def get_expired_orders(session: Session | AsyncSession) -> list[OrderDTO]:
        """Gets all expired orders (for timeout job)"""
        stmt = (
            select(Order)
            .where(Order.status == OrderStatus.PENDING_PAYMENT)
            .where(Order.expires_at < datetime.now())
        )
        result = await session_execute(stmt, session)
        return [OrderDTO.model_validate(order, from_attributes=True) for order in result.scalars().all()]

    @staticmethod
    async def get_by_user_id(user_id: int, session: Session | AsyncSession) -> list[OrderDTO]:
        """Gets all orders of a user (for history)"""
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .where(Order.status == OrderStatus.PAID)
            .order_by(Order.paid_at.desc())
        )
        result = await session_execute(stmt, session)
        return [OrderDTO.model_validate(order, from_attributes=True) for order in result.scalars().all()]

    @staticmethod
    async def get_total_spent_by_currency(user_id: int, session: Session | AsyncSession):
        """Calculates total spending grouped by currency"""
        stmt = (
            select(Order.currency, func.sum(Order.total_price))
            .where(Order.user_id == user_id)
            .where(Order.status == OrderStatus.PAID)
            .group_by(Order.currency)
        )
        result = await session_execute(stmt, session)
        return result.all()

    @staticmethod
    async def get_orders_awaiting_shipment(session: Session | AsyncSession) -> list[Order]:
        """Gets all orders awaiting shipment (for admin shipping management)"""
        stmt = (
            select(Order)
            .where(Order.status == OrderStatus.PAID_AWAITING_SHIPMENT)
            .order_by(Order.paid_at.desc())
            .options(selectinload(Order.items))
        )
        result = await session_execute(stmt, session)
        return result.scalars().all()

    @staticmethod
    async def get_by_id_with_items(order_id: int, session: Session | AsyncSession) -> Order:
        """Gets order with all items (for display)"""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        result = await session_execute(stmt, session)
        return result.scalar_one()