from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Integer, Column, String
from sqlalchemy.orm import relationship

from models.base import Base


class Subcategory(Base):
    __tablename__ = 'subcategories'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    media_id = Column(String, nullable=False)
    items = relationship("Item", back_populates="subcategory")

    def __repr__(self):
        return self.name


class SubcategoryDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    media_id: str | None = None


class SubcategoryAdmin(ModelView, model=Subcategory):
    column_exclude_list = [Subcategory.items, Subcategory.media_id]
