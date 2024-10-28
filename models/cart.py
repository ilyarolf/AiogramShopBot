# cart is a container for unsold items to collect items from different (sub-)categories
# to be able to checkout this cart at once together with a shipment fee. Only the
# quantity, category, subcategory is stored because the unique item is not yet sold
#
# note that the item is NOT reserved or blocked so that the availability of the item
# needs to be checked again during checkout
from typing import List

from sqlalchemy import Column, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    is_closed: Mapped[bool] = mapped_column(default=False)

    shipment: Mapped[int] = mapped_column(default=0, nullable=False)
    cart_items: Mapped[List["CartItem"]] = relationship(back_populates="cart")


class CartItem(Base):

    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    cart: Mapped["Cart"] = relationship(back_populates="cart_items")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category_name: Mapped[str] = mapped_column(default=None, nullable=True)
    subcategory_id: Mapped[int] = mapped_column(ForeignKey("subcategories.id"), passive_deletes="all")
    subcategory_name: Mapped[str] = mapped_column(default=None, nullable=True)
    quantity = Column(Integer, default=0)
    a_piece_price = Column(Float, default=0.0)