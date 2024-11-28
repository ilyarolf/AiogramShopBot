from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Integer, Column, String, ForeignKey, Boolean, BigInteger, DateTime, func

from models.base import Base


class Deposit(Base):
    __tablename__ = 'deposits'
    id = Column(Integer, primary_key=True)
    tx_id = Column(String, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    network = Column(String, nullable=False)
    token_name = Column(String, nullable=True)
    amount = Column(BigInteger, nullable=False)
    is_withdrawn = Column(Boolean, default=False)
    vout = Column(Integer, nullable=True)
    deposit_datetime = Column(DateTime, default=func.now())


class DepositDTO(BaseModel):
    id: int | None = None
    tx_id: str | None = None
    user_id: int | None = None
    network: str | None = None
    token_name: str | None = None
    amount: int | None = None
    is_withdrawn: bool | None = None
    vout: int | None = None
    deposit_datetime: datetime | None = None
