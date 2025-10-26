from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from models.base import Base


class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True, unique=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)  # Removed unique=True to allow multiple invoices per order (partial payments)
    invoice_number = Column(String, nullable=False, unique=True)

    # Crypto-Payment-Details (für Payment-Prozess)
    payment_address = Column(String, nullable=True)
    payment_amount_crypto = Column(Float, nullable=True)
    payment_crypto_currency = Column(SQLEnum(Cryptocurrency), nullable=True)
    payment_processing_id = Column(Integer, nullable=True)

    # Fiat-Referenz (zur Anzeige auf Invoice)
    fiat_amount = Column(Float, nullable=False)
    fiat_currency = Column(SQLEnum(Currency), nullable=False)

    # Payment Validation Fields
    is_partial_payment = Column(Integer, nullable=False, default=0)  # 0=full, 1=first partial, 2=second partial
    parent_invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True)  # Links to original invoice
    actual_paid_amount_crypto = Column(Float, nullable=True)  # Actual amount received (for tracking)
    payment_attempt = Column(Integer, nullable=False, default=1)  # 1st or 2nd payment attempt

    # Relations
    order = relationship('Order', back_populates='invoices')  # Changed from 'invoice' to 'invoices' to match Order model
    payment_transactions = relationship('PaymentTransaction', back_populates='invoice', cascade='all, delete-orphan')


class InvoiceDTO(BaseModel):
    id: int | None = None
    order_id: int | None = None
    invoice_number: str | None = None
    payment_address: str | None = None
    payment_amount_crypto: float | None = None
    payment_crypto_currency: Cryptocurrency | None = None
    payment_processing_id: int | None = None
    fiat_amount: float | None = None
    fiat_currency: Currency | None = None
    is_partial_payment: int | None = None
    parent_invoice_id: int | None = None
    actual_paid_amount_crypto: float | None = None
    payment_attempt: int | None = None