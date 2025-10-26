from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship

from models.base import Base


class ReferralUsage(Base):
    """
    Tracks referral code usage with hashed user IDs for privacy.

    Security Design:
    - User IDs are hashed with SHA256 + salt (not stored directly)
    - Enables abuse detection without storing personal data long-term
    - Data retention: 365 days (longer than orders for abuse pattern analysis)

    Use Cases:
    - Prevent same user from being referred multiple times by same referrer
    - Detect abuse patterns (e.g., 50+ referrals from same hashed ID)
    - Track referral success rate
    """
    __tablename__ = 'referral_usages'

    id = Column(Integer, primary_key=True)
    referral_code = Column(String(8), nullable=False)  # Format: U_A3F9K

    # Hashed User IDs (SHA256 with salt) for privacy
    referrer_user_hash = Column(String(64), nullable=False)  # SHA256(user_id + SALT)
    referred_user_hash = Column(String(64), nullable=False)  # SHA256(user_id + SALT)

    # Order reference (for tracking discount application)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    discount_amount = Column(Float, nullable=False)  # Discount given to new customer

    # Metadata
    created_at = Column(DateTime, default=func.now())

    # Relations
    order = relationship('Order', backref='referral_usage')

    __table_args__ = (
        # Prevent same user-pair from using referral twice
        UniqueConstraint('referrer_user_hash', 'referred_user_hash', name='uq_referrer_referred'),
    )


class ReferralUsageDTO(BaseModel):
    id: int | None = None
    referral_code: str | None = None
    referrer_user_hash: str | None = None
    referred_user_hash: str | None = None
    order_id: int | None = None
    discount_amount: float | None = None
    created_at: datetime | None = None
