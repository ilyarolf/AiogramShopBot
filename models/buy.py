from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, func, CheckConstraint, Enum, String
from sqlalchemy.orm import relationship

import config
from enums.bot_entity import BotEntity
from enums.buy_status import BuyStatus
from enums.language import Language
from models.base import Base
from utils.utils import get_text


class Buy(Base):
    __tablename__ = 'buys'

    id = Column(Integer, primary_key=True, unique=True)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    buyer = relationship('User', backref='buys')
    total_price = Column(Float, nullable=False)
    buy_datetime = Column(DateTime, default=func.now())
    status = Column(Enum(BuyStatus), nullable=False)
    coupon_id = Column(Integer, ForeignKey('coupons.id'), nullable=True)
    discount = Column(Float, nullable=False, default=0.0)
    shipping_address = Column(String, nullable=True)
    track_number = Column(String, nullable=True)
    shipping_option_id = Column(Integer, ForeignKey('shipping_options.id'), nullable=True)

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint('total_price > 0', name='check_total_price_positive'),
    )


class BuyDTO(BaseModel):
    id: int | None = None
    buyer_id: int | None = None
    total_price: float | None = None
    buy_datetime: datetime | None = None
    status: BuyStatus = BuyStatus.PAID
    coupon_id: int | None = None
    discount: float = 0.0
    shipping_address: str | None = None
    track_number: str | None = None
    shipping_option_id: int | None

    @staticmethod
    def get_chart_text(language: Language) -> tuple[str, str]:
        return (get_text(language, BotEntity.ADMIN, "sales_ylabel")
                .format(currency_sym=config.CURRENCY.get_localized_symbol()),
                get_text(language, BotEntity.ADMIN, "sales_chart_title"))


class RefundDTO(BaseModel):
    telegram_username: str | None = None
    telegram_id: int | None = None
    subcategory_name: str | None = None
    total_price: float | None = None
    item_ids: list[int] | None = None
    buy_id: int | None = None
    language: Language
