# cart is a container for unsold items to collect items from different (sub-)categories
# to be able to checkout this cart at once together with a shipment fee. Only the
# quantity, category, subcategory is stored because the unique item is not yet sold
#
# note that the item is NOT reserved or blocked so that the availability of the item
# needs to be checked again during checkout
from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="cart", uselist=False)
    cart_items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Cart ID:{self.id}"


class CartDTO(BaseModel):
    id: int | None = None
    user_id: int | None = None


class CartAdmin(ModelView, model=Cart):
    name = "Cart"
    name_plural = "Carts"
    column_sortable_list = [Cart.id]
    column_exclude_list = [Cart.user_id, Cart.cart_items]
    can_delete = False
    can_edit = False
    can_create = False
    can_export = False
