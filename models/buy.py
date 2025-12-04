from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, DateTime, Boolean, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import relationship

from enums.language import Language
from models.base import Base


class Buy(Base):
    __tablename__ = 'buys'

    id = Column(Integer, primary_key=True, unique=True)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    buyer = relationship('User', backref='buys')
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    buy_datetime = Column(DateTime, default=func.now())
    is_refunded = Column(Boolean, default=False)
    coupon_id = Column(Integer, ForeignKey('coupons.id'), nullable=True)

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('total_price > 0', name='check_total_price_positive'),
    )


class BuyDTO(BaseModel):
    id: int | None = None
    buyer_id: int | None = None
    quantity: int | None = None
    total_price: float | None = None
    buy_datetime: datetime | None = None
    is_refunded: bool | None = None
    coupon_id: int | None = None


class RefundDTO(BaseModel):
    telegram_username: str | None = None
    telegram_id: int | None = None
    subcategory_name: str | None = None
    total_price: float | None = None
    quantity: int | None = None
    buy_id: int | None = None
    language: Language
