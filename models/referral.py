from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Integer, Column, ForeignKey, Float, CheckConstraint
from sqlalchemy.orm import relationship

from models.base import Base
from models.user import UserDTO


class ReferralBonus(Base):
    __tablename__ = "referral_bonus"

    id = Column(Integer, primary_key=True)
    referral_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referrer_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payment_amount = Column(Float, nullable=False)
    applied_referral_bonus = Column(Float, nullable=False)
    applied_referrer_bonus = Column(Float, nullable=False)
    referral_user_dto = relationship(
        "User",
        foreign_keys=[referral_user_id],
        back_populates="received_referral_bonuses"
    )
    referrer_user_dto = relationship(
        "User",
        foreign_keys=[referrer_user_id],
        back_populates="earned_referral_bonuses"
    )

    __table_args__ = (
        CheckConstraint(
            'referral_user_id != referrer_user_id',
            name='check_no_self_referral'
        ),
    )

    def __repr__(self):
        return f"ReferralBonus ID:{self.id}"


class ReferralBonusDTO(BaseModel):
    id: int | None = None
    referral_user_id: int | None = None
    referral_user_dto: UserDTO | None = None
    referrer_user_id: int | None = None
    referrer_user_dto: UserDTO | None = None
    payment_amount: float = 0.0
    applied_referral_bonus: float = 0.0
    applied_referrer_bonus: float = 0.0


class ReferralBonusAdmin(ModelView, model=ReferralBonus):
    column_exclude_list = [ReferralBonus.referrer_user_id,
                           ReferralBonus.referral_user_id]
    column_sortable_list = [ReferralBonus.id,
                            ReferralBonus.payment_amount,
                            ReferralBonus.applied_referrer_bonus,
                            ReferralBonus.applied_referral_bonus]
    name = "Referral Bonus"
    name_plural = "Referral Bonuses"
    can_delete = False
    can_edit = False
    can_create = False
    can_export = False
