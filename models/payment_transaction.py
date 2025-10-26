from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import relationship

from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from models.base import Base


class PaymentTransaction(Base):
    """
    Tracks individual payment transactions for an order.

    Provides audit trail for:
    - Partial payments
    - Overpayments
    - Underpayments
    - Late payments
    - Penalty fee application
    - Wallet credits

    Data Retention: Deleted after 30 days (no long-term audit trail).
    """
    __tablename__ = 'payment_transactions'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)

    # Transaction details
    crypto_amount = Column(Float, nullable=False)
    crypto_currency = Column(SQLEnum(Cryptocurrency), nullable=False)
    fiat_amount = Column(Float, nullable=False)
    fiat_currency = Column(SQLEnum(Currency), nullable=False)

    # Payment source (from KryptoExpress webhook)
    transaction_hash = Column(String, nullable=True)  # payment_dto.hash - Blockchain TX hash
    payment_address = Column(String, nullable=False)  # payment_dto.address
    payment_processing_id = Column(Integer, nullable=False)  # payment_dto.id - KryptoExpress ID

    # Classification
    is_overpayment = Column(Boolean, nullable=False, default=False)
    is_underpayment = Column(Boolean, nullable=False, default=False)
    is_late_payment = Column(Boolean, nullable=False, default=False)

    # Penalty tracking
    penalty_applied = Column(Boolean, nullable=False, default=False)
    penalty_percent = Column(Float, nullable=False, default=0.0)

    # Wallet credit (if applicable)
    wallet_credit_amount = Column(Float, nullable=True)

    # Metadata
    received_at = Column(DateTime, default=func.now())

    # Relations
    order = relationship('Order', back_populates='payment_transactions')
    invoice = relationship('Invoice', back_populates='payment_transactions')


class PaymentTransactionDTO(BaseModel):
    id: int | None = None
    order_id: int | None = None
    invoice_id: int | None = None
    crypto_amount: float | None = None
    crypto_currency: Cryptocurrency | None = None
    fiat_amount: float | None = None
    fiat_currency: Currency | None = None
    transaction_hash: str | None = None
    payment_address: str | None = None
    payment_processing_id: int | None = None
    is_overpayment: bool | None = None
    is_underpayment: bool | None = None
    is_late_payment: bool | None = None
    penalty_applied: bool | None = None
    penalty_percent: float | None = None
    wallet_credit_amount: float | None = None
    received_at: datetime | None = None