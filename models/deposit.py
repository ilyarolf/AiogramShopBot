from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Integer, Column, ForeignKey, BigInteger, DateTime, func, CheckConstraint, Enum

from enums.cryptocurrency import Cryptocurrency
from models.base import Base


class Deposit(Base):
    __tablename__ = 'deposits'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    blockchain = Column(Enum(Cryptocurrency), nullable=False)
    amount = Column(BigInteger, nullable=False)
    deposit_datetime = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint('amount > 0', name='check_amount_positive'),
    )


class DepositDTO(BaseModel):
    id: int | None = None
    user_id: int | None = None
    blockchain: Cryptocurrency | None = None
    amount: int | None = None
    deposit_datetime: datetime | None = None
