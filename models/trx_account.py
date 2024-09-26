from sqlalchemy import Column, Integer, Float, String

from models.base import Base


class TrxAccount(Base):
    __tablename__ = 'trx_accounts'

    id = Column(Integer, primary_key=True)
    address = Column(String, nullable=False, unique=True)
    eth_balance = Column(Float, default=0.0)
    usdt_balance = Column(Float, default=0.0)
    usdd_balance = Column(Float, default=0.0)
