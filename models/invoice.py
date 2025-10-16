from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from models.base import Base


class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True, unique=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, unique=True)
    invoice_number = Column(String, nullable=False, unique=True)

    # Crypto-Payment-Details (für Payment-Prozess)
    payment_address = Column(String, nullable=True)
    payment_amount_crypto = Column(Float, nullable=True)
    payment_crypto_currency = Column(SQLEnum(Cryptocurrency), nullable=True)
    payment_processing_id = Column(Integer, nullable=True)

    # Fiat-Referenz (zur Anzeige auf Invoice)
    fiat_amount = Column(Float, nullable=False)
    fiat_currency = Column(SQLEnum(Currency), nullable=False)

    # Relations
    order = relationship('Order', back_populates='invoice')


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