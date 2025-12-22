from datetime import datetime, timezone, timedelta

from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Column, DateTime, Enum, Boolean, String, Integer, Numeric
from sqlalchemy.orm import relationship

from enums.coupon_type import CouponType
from models.base import Base


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=True)
    code = Column(String(12), unique=True, nullable=False, index=True)
    type = Column(Enum(CouponType), nullable=False)
    value = Column(Numeric(10, 2), nullable=False)
    create_datetime = Column(DateTime(timezone=True), nullable=False)
    expire_datetime = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    usage_limit = Column(Integer, default=1)
    usage_count = Column(Integer, default=0)
    buys = relationship("Buy", back_populates="coupon")


class CouponDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    code: str | None = None
    type: CouponType | None = None
    value: float | None = None
    create_datetime: datetime = datetime.now(tz=timezone.utc)
    expire_datetime: datetime = datetime.now(tz=timezone.utc) + timedelta(days=30)
    is_active: bool = True
    usage_limit: int = 1
    usage_count: int = 0


class CouponAdmin(ModelView, model=Coupon):
    column_exclude_list = [Coupon.buys]
