from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Integer, Column, String
from sqlalchemy.orm import relationship

from models.base import Base


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    media_id = Column(String, nullable=False)
    items = relationship("Item", back_populates="category")
    cart_items = relationship("CartItem", back_populates="category")

    def __repr__(self):
        return self.name


class CategoryDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    media_id: str | None = None


class CategoryAdmin(ModelView, model=Category):
    name = "Category"
    name_plural = "Categories"
    column_searchable_list = [Category.name]
    column_sortable_list = [Category.id, Category.name]
    column_exclude_list = [Category.items,
                           Category.media_id,
                           Category.cart_items]
    can_delete = False
    can_edit = True
    can_create = True
    can_export = False
