from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Enum as SQLEnum
from sqlalchemy.orm import relationship

from enums.strike_type import StrikeType
from models.base import Base


class UserStrike(Base):
    __tablename__ = 'user_strikes'

    id = Column(Integer, primary_key=True, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    strike_type = Column(SQLEnum(StrikeType), nullable=False, default=StrikeType.TIMEOUT)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    created_at = Column(DateTime, default=func.now())
    reason = Column(String, nullable=True)

    # Relations
    user = relationship('User', backref='strikes')
    order = relationship('Order')


class UserStrikeDTO(BaseModel):
    id: int | None = None
    user_id: int | None = None
    strike_type: StrikeType | None = None
    order_id: int | None = None
    created_at: datetime | None = None
    reason: str | None = None