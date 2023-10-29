import datetime

from sqlalchemy import Column, Integer, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class Buy(Base):
    __tablename__ = 'buys'

    id = Column(Integer, primary_key=True, unique=True)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    buyer = relationship('User', backref='buys')
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    buy_datetime = Column(DateTime, default=datetime.datetime.utcnow())
    is_refunded = Column(Boolean, default=False)
