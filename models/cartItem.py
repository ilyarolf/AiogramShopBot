from pydantic import BaseModel
from sqlalchemy import Column, Integer, ForeignKey, CheckConstraint

from models.base import Base


class CartItem(Base):
    """
    Cart item model - links a cart to a product category with quantity.

    category_id must reference a Category where is_product=True.
    """
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    quantity = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
    )


class CartItemDTO(BaseModel):
    id: int | None = None
    cart_id: int | None = None
    category_id: int | None = None
    quantity: int | None = None
