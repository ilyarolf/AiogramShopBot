from sqlalchemy import Column, Integer, Float, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship

from models.base import Base


class Buy(Base):
    __tablename__ = 'buys'

    id = Column(Integer, primary_key=True, unique=True)
    buyer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    buyer = relationship('User', backref='buys')
    quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    buy_datetime = Column(DateTime, default=func.now())
    is_refunded = Column(Boolean, default=False)
