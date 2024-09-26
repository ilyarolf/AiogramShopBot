from sqlalchemy import Column, Integer, DateTime, String, Boolean, Float, func, ForeignKey
from sqlalchemy.orm import relationship, backref

from models.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_username = Column(String, unique=True)
    telegram_id = Column(Integer, nullable=False)
    btc_address = Column(String, nullable=False, unique=True)
    ltc_address = Column(String, nullable=False, unique=True)
    last_balance_refresh = Column(DateTime)
    top_up_amount = Column(Float, default=0.0)
    consume_records = Column(Float, default=0.0)
    btc_balance = Column(Float, nullable=False, default=0.0)
    ltc_balance = Column(Float, nullable=False, default=0.0)
    eth_account_id = Column(Integer, ForeignKey('eth_accounts.id'), nullable=False)
    eth_account = relationship("EthAccount", backref=backref("eth_accounts", cascade="all"),
                               passive_deletes="all",
                               lazy="joined")
    trx_account_id = Column(Integer, ForeignKey('trx_accounts.id'), nullable=False)
    trx_account = relationship("TrxAccount", backref=backref("trx_accounts", cascade="all"),
                               passive_deletes="all",
                               lazy="joined")
    registered_at = Column(DateTime, default=func.now())
    seed = Column(String, nullable=False, unique=True)
    can_receive_messages = Column(Boolean, default=True)
