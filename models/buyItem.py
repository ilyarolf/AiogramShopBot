from typing import List

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref, mapped_column, Mapped

from models.base import Base


# buyItem is a sold good of a unique item which connects the sold Item to an
# also unique transfer process, the "buy"
class BuyItem(Base):
    __tablename__ = "buyItem"

    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    buy_id = Column(Integer, ForeignKey("buys.id", ondelete="CASCADE"), nullable=False)
    buy = relationship("Buy", backref=backref("buys", cascade="all"), passive_deletes="all")
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    item = relationship("Item", backref=backref("items", cascade="all"), passive_deletes="all")

    basket_id: Mapped[int] = mapped_column(ForeignKey("basket.id"))
    basket: Mapped["Basket"] = relationship(back_populates="buy_items")

class Basket(Base):
    __tablename__ = "basket"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    is_closed: Mapped[bool] = mapped_column(default=False)
    shipment: Mapped[int] = mapped_column(default=0, nullable=False)
    buy_items: Mapped[List["BuyItem"]] = relationship(back_populates="basket")

