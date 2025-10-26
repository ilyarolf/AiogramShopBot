from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, ForeignKey, func

from models.base import Base


class ReferralDiscount(Base):
    """
    Tracks referral discount credits for users who referred others.

    Lifecycle:
    - Created when referred user completes first order
    - Used automatically on referrer's next order
    - Expires after 90 days (as per T&Cs)

    Data Retention: Deleted after 90 days expiry
    """
    __tablename__ = 'referral_discounts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Discount configuration
    discount_percentage = Column(Float, nullable=False, default=10.0)  # 10%
    max_discount_amount = Column(Float, nullable=False, default=50.0)  # Cap at €50
    reason = Column(String, nullable=False)  # "Referred user @username"

    # Usage tracking
    used = Column(Boolean, nullable=False, default=False)
    used_at = Column(DateTime, nullable=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)  # Order where discount was applied

    # Lifecycle
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)  # 90 days from creation


class ReferralDiscountDTO(BaseModel):
    id: int | None = None
    user_id: int | None = None
    discount_percentage: float | None = None
    max_discount_amount: float | None = None
    reason: str | None = None
    used: bool | None = None
    used_at: datetime | None = None
    order_id: int | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
