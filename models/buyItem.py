from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class BuyItem(Base):
    __tablename__ = "buyItem"

    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    buy_id = Column(Integer, ForeignKey("buys.id"), nullable=False)
    buy = relationship("Buy", backref="buys")
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)
    item = relationship("Item", backref="items")
