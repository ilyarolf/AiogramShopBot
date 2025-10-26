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
    shipped_at = Column(DateTime, nullable=True)

    # Shipping Fields
    shipping_cost = Column(Float, nullable=False, default=0.0)

    # Payment Validation Fields
    total_paid_crypto = Column(Float, nullable=False, default=0.0)  # Sum of all partial payments
    retry_count = Column(Integer, nullable=False, default=0)  # Underpayment retry counter (0 or 1)
    original_expires_at = Column(DateTime, nullable=True)  # Original deadline (before extension)
    wallet_used = Column(Float, nullable=False, default=0.0)  # Wallet balance used for this order

    # Relations
    user = relationship('User', backref='orders')
    items = relationship('Item', backref='order')
    invoices = relationship('Invoice', back_populates='order', cascade='all, delete-orphan')  # Changed to plural, removed uselist=False to allow multiple invoices (partial payments)
    payment_transactions = relationship('PaymentTransaction', back_populates='order', cascade='all, delete-orphan')
    shipping_address = relationship('ShippingAddress', back_populates='order', uselist=False, cascade='all, delete-orphan')

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
    shipped_at: datetime | None = None
    shipping_cost: float | None = 0.0
    total_paid_crypto: float | None = None
    retry_count: int | None = None
    original_expires_at: datetime | None = None
    wallet_used: float | None = None