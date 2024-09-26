from models.base import Base
from sqlalchemy import Column, Integer, String, Float


class EthAccount(Base):
    __tablename__ = 'eth_accounts'

    id = Column(Integer, primary_key=True)
    address = Column(String, nullable=False, unique=True)
    eth_balance = Column(Float, default=0.0)
    usdt_balance = Column(Float, default=0.0)
    usdc_balance = Column(Float, default=0.0)
