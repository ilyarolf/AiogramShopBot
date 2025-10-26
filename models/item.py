from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, backref

from models.base import Base


# Item is a unique good which can only be sold once
class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, unique=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    category = relationship("Category", backref=backref("categories", cascade="all"), passive_deletes="all",
                            lazy="joined")
    subcategory_id = Column(Integer, ForeignKey("subcategories.id", ondelete="CASCADE"), nullable=False)
    subcategory = relationship("Subcategory", backref=backref("subcategories", cascade="all"), passive_deletes="all",
                               lazy="joined")
    private_data = Column(String, nullable=False, unique=False)
    price = Column(Float, nullable=False)
    is_sold = Column(Boolean, nullable=False, default=False)
    is_new = Column(Boolean, nullable=False, default=True)
    description = Column(String, nullable=False)

    # Shipping-related fields
    is_physical = Column(Boolean, nullable=False, default=False)
    shipping_cost = Column(Float, nullable=False, default=0.0)
    allows_packstation = Column(Boolean, nullable=False, default=False)

    # Order-Zuordnung (Reservierung + Verkauf)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    reserved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
        CheckConstraint('shipping_cost >= 0', name='check_shipping_cost_non_negative'),
    )


class ItemDTO(BaseModel):
    id: int | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    private_data: str | None = None
    price: float | None = None
    is_sold: bool | None = None
    is_new: bool | None = None
    description: str | None = None
    is_physical: bool | None = None
    shipping_cost: float | None = None
    allows_packstation: bool | None = None
    order_id: int | None = None
    reserved_at: datetime | None = None
