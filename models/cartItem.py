from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Column, Integer, ForeignKey, CheckConstraint, Enum
from sqlalchemy.orm import relationship

from enums.item_type import ItemType
from models.base import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    cart = relationship("Cart", back_populates="cart_items")
    item_type = Column(Enum(ItemType), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    category = relationship("Category", back_populates="cart_items")
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'), nullable=False)
    subcategory = relationship("Subcategory", back_populates="cart_items")
    quantity = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
    )

    def __repr__(self):
        return f"CartItem ID: {self.id}"


class CartItemDTO(BaseModel):
    id: int | None = None
    cart_id: int | None = None
    item_type: ItemType | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    quantity: int | None = None


class CartItemAdmin(ModelView, model=CartItem):
    column_sortable_list = [CartItem.id,
                            CartItem.item_type,
                            CartItem.quantity,
                            CartItem.item_type]
    column_exclude_list = [CartItem.category_id,
                           CartItem.subcategory_id,
                           CartItem.cart_id]
    can_create = False
    can_delete = False
    can_edit = False
    can_export = False
