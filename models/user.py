from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float, func, CheckConstraint

from models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, unique=True)
    telegram_id = Column(Integer, nullable=False, unique=True)
    registered_at = Column(DateTime, default=func.now())
    can_receive_messages = Column(Boolean, default=True)

    # Strike-System
    strike_count = Column(Integer, nullable=False, default=0)
    is_blocked = Column(Boolean, nullable=False, default=False)
    blocked_at = Column(DateTime, nullable=True)
    blocked_reason = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint('strike_count >= 0', name='check_strike_count_positive'),
    )


class UserDTO(BaseModel):
    id: int | None = None
    telegram_username: str | None = None
    telegram_id: int | None = None
    registered_at: datetime | None = None
    can_receive_messages: bool | None = None
    strike_count: int | None = None
    is_blocked: bool | None = None
    blocked_at: datetime | None = None
    blocked_reason: str | None = None
