from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float, func, CheckConstraint

from models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, unique=True)
    telegram_id = Column(Integer, nullable=False, unique=True)
    top_up_amount = Column(Float, default=0.0)
    consume_records = Column(Float, default=0.0)
    registered_at = Column(DateTime, default=func.now())
    can_receive_messages = Column(Boolean, default=True)

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
