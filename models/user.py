import datetime

from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float

from models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, unique=True)
    telegram_id = Column(Integer, nullable=False)
    btc_address = Column(String, nullable=False, unique=True)
    ltc_address = Column(String, nullable=False, unique=True)
    trx_address = Column(String, nullable=False, unique=True)
    last_balance_refresh = Column(DateTime)
    top_up_amount = Column(Float, default=0.0)
    consume_records = Column(Float, default=0.0)
    btc_balance = Column(Float, nullable=False, default=0.0)
    ltc_balance = Column(Float, nullable=False, default=0.0)
    usdt_balance = Column(Float, nullable=False, default=0.0)
    is_new = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow())
    seed = Column(String, nullable=False, unique=True)
