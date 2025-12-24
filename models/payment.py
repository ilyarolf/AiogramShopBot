from pydantic import BaseModel
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean

import config
from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from enums.payment import PaymentType
from models.base import Base


class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    processing_payment_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    is_paid = Column(Boolean, nullable=False, default=False)
    expire_datetime = Column(DateTime)


class ProcessingPaymentDTO(BaseModel):
    id: int | None = None
    paymentType: PaymentType = PaymentType.DEPOSIT
    fiatCurrency: Currency
    fiatAmount: float | None = None
    cryptoAmount: float | None = None
    userId: str | None = None
    cryptoCurrency: Cryptocurrency
    expireDatetime: int | None = None
    createDatetime: int | None = None
    address: str | None = None
    isPaid: bool | None = None
    isWithdrawn: bool | None = None
    hash: str | None = None
    callbackUrl: str = f'{config.WEBHOOK_URL}cryptoprocessing/event'
    callbackSecret: str | None = config.KRYPTO_EXPRESS_API_SECRET if len(config.KRYPTO_EXPRESS_API_SECRET) > 0 else None


class TablePaymentDTO(BaseModel):
    id: int
    user_id: int
    processing_payment_id: int
    message_id: int
    is_paid: bool
