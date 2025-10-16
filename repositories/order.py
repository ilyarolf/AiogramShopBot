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
        """Erstellt eine neue Order und gibt die ID zurück"""
        order = Order(**order_dto.model_dump(exclude_none=True))
        session.add(order)
        await session_flush(session)
        return order.id

    @staticmethod
    async def get_by_id(order_id: int, session: Session | AsyncSession) -> OrderDTO:
        """Holt Order by ID"""
        stmt = select(Order).where(Order.id == order_id)
        order = await session_execute(stmt, session)
        return OrderDTO.model_validate(order.scalar_one(), from_attributes=True)

    @staticmethod
    async def get_by_id_with_items(order_id: int, session: Session | AsyncSession) -> Order:
        """Holt Order mit allen Items (für Anzeige)"""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items))
        )
        result = await session_execute(stmt, session)
        return result.scalar_one()

    @staticmethod
    async def get_pending_order_by_user(user_id: int, session: Session | AsyncSession) -> OrderDTO | None:
        """Holt offene Order eines Users (falls vorhanden)"""
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
    async def update_status(order_id: int, status: OrderStatus, session: Session | AsyncSession):
        """Aktualisiert den Status einer Order"""
        timestamp_field = None

        if status == OrderStatus.PAID:
            timestamp_field = Order.paid_at
        elif status in [OrderStatus.CANCELLED, OrderStatus.TIMEOUT]:
            timestamp_field = Order.cancelled_at

        values = {"status": status}
        if timestamp_field is not None:
            values[timestamp_field.key] = datetime.now()

        stmt = update(Order).where(Order.id == order_id).values(**values)
        await session_execute(stmt, session)

    @staticmethod
    async def get_expired_orders(session: Session | AsyncSession) -> list[OrderDTO]:
        """Holt alle abgelaufenen Orders (für Timeout-Job)"""
        stmt = (
            select(Order)
            .where(Order.status == OrderStatus.PENDING_PAYMENT)
            .where(Order.expires_at < datetime.now())
        )
        result = await session_execute(stmt, session)
        return [OrderDTO.model_validate(order, from_attributes=True) for order in result.scalars().all()]

    @staticmethod
    async def get_by_user_id(user_id: int, session: Session | AsyncSession) -> list[OrderDTO]:
        """Holt alle Orders eines Users (für Historie)"""
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
        """Berechnet Gesamtausgaben gruppiert nach Währung"""
        stmt = (
            select(Order.currency, func.sum(Order.total_price))
            .where(Order.user_id == user_id)
            .where(Order.status == OrderStatus.PAID)
            .group_by(Order.currency)
        )
        result = await session_execute(stmt, session)
        return result.all()