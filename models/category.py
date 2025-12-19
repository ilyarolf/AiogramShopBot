from pydantic import BaseModel
from sqlalchemy import Integer, Column, String, Boolean, Float, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, backref

from models.base import Base


class Category(Base):
    """
    Unified category model supporting unlimited hierarchy depth.

    - parent_id: NULL means root category
    - is_product: True means this is a sellable product (leaf node)
    - Product-specific fields (price, description, image) only used when is_product=True
    """
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, unique=True)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    name = Column(String, nullable=False)
    is_product = Column(Boolean, nullable=False, default=False)

    # Product-specific fields (only used when is_product=True)
    image_file_id = Column(String, nullable=True)  # Telegram file_id for product photo
    description = Column(String, nullable=True)
    price = Column(Float, nullable=True)

    # Self-referential relationship for tree structure
    parent = relationship(
        "Category",
        remote_side=[id],
        backref=backref("children", cascade="all, delete-orphan", passive_deletes=True)
    )

    __table_args__ = (
        CheckConstraint(
            '(is_product = 0) OR (is_product = 1 AND price > 0)',
            name='check_product_has_price'
        ),
    )


class CategoryDTO(BaseModel):
    id: int | None = None
    parent_id: int | None = None
    name: str | None = None
    is_product: bool = False
    image_file_id: str | None = None
    description: str | None = None
    price: float | None = None
