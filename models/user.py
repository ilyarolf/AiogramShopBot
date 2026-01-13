from datetime import datetime
from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float, func, CheckConstraint, Enum, ForeignKey
from sqlalchemy.orm import relationship

from enums.bot_entity import BotEntity
from enums.language import Language
from models.base import Base
from utils.utils import get_text


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, unique=True, index=True)
    telegram_id = Column(Integer, nullable=False, unique=True, index=True)
    top_up_amount = Column(Float, default=0.0)
    consume_records = Column(Float, default=0.0)
    registered_at = Column(DateTime, default=func.now())
    can_receive_messages = Column(Boolean, default=True)
    language = Column(Enum(Language), default=Language.EN, nullable=False)
    is_banned = Column(Boolean, default=False)
    referral_code = Column(String(8), nullable=True, unique=True, index=True)
    referred_by_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referred_at = Column(DateTime, nullable=True)
    received_referral_bonuses = relationship(
        "ReferralBonus",
        foreign_keys="ReferralBonus.referral_user_id",
        back_populates="referral_user_dto",
        cascade="all, delete-orphan"
    )
    earned_referral_bonuses = relationship(
        "ReferralBonus",
        foreign_keys="ReferralBonus.referrer_user_id",
        back_populates="referrer_user_dto",
        cascade="all, delete-orphan"
    )
    buys = relationship(
        "Buy",
        back_populates="buyer",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint('top_up_amount >= 0', name='check_top_up_amount_positive'),
        CheckConstraint('consume_records >= 0', name='check_consume_records_positive'),
        CheckConstraint('referred_by_user_id != id', name='check_no_self_referral'),
    )

    def __repr__(self):
        return self.telegram_username or self.telegram_id


class UserDTO(BaseModel):
    id: int | None = None
    telegram_username: str | None = None
    telegram_id: int | None = None
    top_up_amount: float | None = None
    consume_records: float | None = None
    registered_at: datetime | None = None
    can_receive_messages: bool | None = None
    language: Language = Language.EN
    is_banned: bool = False
    referral_code: str | None = None
    referred_by_user_id: int | None = None
    referred_at: datetime | None = None

    @staticmethod
    def get_chart_text(language: Language) -> tuple[str, str]:
        return (get_text(language, BotEntity.ADMIN, "users_ylabel"),
                get_text(language, BotEntity.ADMIN, "users_chart_title"))


class UserAdmin(ModelView, model=User):
    column_exclude_list = [User.buys]
