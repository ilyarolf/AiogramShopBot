from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, backref

from models.base import Base


# Item is a unique good which can only be sold once
class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, unique=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id", ondelete="CASCADE"), nullable=False)
    private_data = Column(String, nullable=False, unique=False)
    price = Column(Float, nullable=False)
    is_sold = Column(Boolean, nullable=False, default=False)
    is_new = Column(Boolean, nullable=False, default=True)
    description = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint('price > 0', name='check_price_positive'),
    )


class ItemDTO(BaseModel):
    id: int | None = None
    category_id: int | None = None
    category_name: str | None = None
    subcategory_id: int | None = None
    subcategory_name: str | None = None
    private_data: str | None = None
    price: float | None = None
    is_sold: bool | None = None
    is_new: bool | None = None
    description: str | None = None
