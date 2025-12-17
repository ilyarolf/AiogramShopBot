from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float, func, CheckConstraint, Enum

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

    __table_args__ = (
        CheckConstraint('top_up_amount >= 0', name='check_top_up_amount_positive'),
        CheckConstraint('consume_records >= 0', name='check_consume_records_positive'),
    )


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

    @staticmethod
    def get_chart_text(language: Language) -> tuple[str, str]:
        return (get_text(language, BotEntity.ADMIN, "users_ylabel"),
                get_text(language, BotEntity.ADMIN, "users_chart_title"))
