from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref

from models.base import Base


class BuyItem(Base):
    __tablename__ = "buyItem"

    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    buy_id = Column(Integer, ForeignKey("buys.id", ondelete="CASCADE"), nullable=False)
    buy = relationship("Buy", backref=backref("buys", cascade="all"), passive_deletes="all")
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    item = relationship("Item", backref=backref("items", cascade="all"), passive_deletes="all")
