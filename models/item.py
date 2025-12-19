from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

from models.base import Base


class Item(Base):
    """
    Simplified Item model - represents a single purchasable unit.

    Items belong to a product-level Category (is_product=True).
    Price and description are stored on the Category, not the Item.
    Only private_data (unique per item) is stored here.
    """
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, unique=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    category = relationship(
        "Category",
        backref=backref("items", cascade="all"),
        passive_deletes="all",
        lazy="joined"
    )
    private_data = Column(String, nullable=False)
    is_sold = Column(Boolean, nullable=False, default=False)
    is_new = Column(Boolean, nullable=False, default=True)


class ItemDTO(BaseModel):
    id: int | None = None
    category_id: int | None = None
    private_data: str | None = None
    is_sold: bool | None = None
    is_new: bool | None = None
