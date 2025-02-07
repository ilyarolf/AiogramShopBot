from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float, func, CheckConstraint

from models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, unique=True)
    telegram_id = Column(Integer, nullable=False, unique=True)
    btc_address = Column(String, nullable=False, unique=True)
    ltc_address = Column(String, nullable=False, unique=True)
    trx_address = Column(String, nullable=False, unique=True)
    eth_address = Column(String, nullable=False, unique=True)
    sol_address = Column(String, nullable=False, unique=True)
    last_balance_refresh = Column(DateTime)
    top_up_amount = Column(Float, default=0.0)
    consume_records = Column(Float, default=0.0)
    btc_balance = Column(Float, nullable=False, default=0.0)
    ltc_balance = Column(Float, nullable=False, default=0.0)
    sol_balance = Column(Float, nullable=False, default=0.0)
    usdt_trc20_balance = Column(Float, nullable=False, default=0.0)
    usdt_erc20_balance = Column(Float, nullable=False, default=0.0)
    usdc_erc20_balance = Column(Float, nullable=False, default=0.0)
    registered_at = Column(DateTime, default=func.now())
    seed = Column(String, nullable=False, unique=True)
    can_receive_messages = Column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint('top_up_amount >= 0', name='check_top_up_amount_positive'),
        CheckConstraint('consume_records >= 0', name='check_consume_records_positive'),
        CheckConstraint('btc_balance >= 0', name='check_btc_balance_positive'),
        CheckConstraint('ltc_balance >= 0', name='check_ltc_balance_positive'),
        CheckConstraint('sol_balance >= 0', name='check_sol_balance_positive'),
        CheckConstraint('usdt_trc20_balance >= 0', name='check_usdt_trc20_balance_positive'),
        CheckConstraint('usdt_erc20_balance >= 0', name='check_usdt_erc20_balance_positive'),
        CheckConstraint('usdc_erc20_balance >= 0', name='check_usdc_erc20_balance_positive'),
    )


class UserDTO(BaseModel):
    id: int | None = None
    telegram_username: str | None = None
    telegram_id: int | None = None
    btc_address: str | None = None
    ltc_address: str | None = None
    trx_address: str | None = None
    eth_address: str | None = None
    sol_address: str | None = None
    last_balance_refresh: datetime | None = None
    top_up_amount: float | None = None
    consume_records: float | None = None
    btc_balance: float | None = None
    ltc_balance: float | None = None
    sol_balance: float | None = None
    usdt_trc20_balance: float | None = None
    usdt_erc20_balance: float | None = None
    usdc_erc20_balance: float | None = None
    registered_at: datetime | None = None
    seed: str | None = None
    can_receive_messages: bool | None = None
