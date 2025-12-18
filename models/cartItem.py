from pydantic import BaseModel
from sqlalchemy import Column, Integer, ForeignKey, CheckConstraint, Enum

from enums.item_type import ItemType
from models.base import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    item_type = Column(Enum(ItemType), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'), nullable=False)
    quantity = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
    )


class CartItemDTO(BaseModel):
    id: int | None = None
    cart_id: int | None = None
    item_type: ItemType | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    quantity: int | None = None
