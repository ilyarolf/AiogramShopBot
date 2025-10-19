from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func, CheckConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship

from enums.currency import Currency
from enums.order_status import OrderStatus
from models.base import Base


class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING_PAYMENT)
    total_price = Column(Float, nullable=False)
    currency = Column(SQLEnum(Currency), nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    # Relations
    user = relationship('User', backref='orders')
    items = relationship('Item', backref='order')
    invoice = relationship('Invoice', back_populates='order', uselist=False, cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint('total_price > 0', name='check_order_total_price_positive'),
    )


class OrderDTO(BaseModel):
    id: int | None = None
    user_id: int | None = None
    status: OrderStatus | None = None
    total_price: float | None = None
    currency: Currency | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    paid_at: datetime | None = None
    cancelled_at: datetime | None = None