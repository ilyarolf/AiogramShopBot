from pydantic import BaseModel
from sqlalchemy import Integer, Column, String

from models.base import Base


class Subcategory(Base):
    __tablename__ = 'subcategories'

    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, nullable=False)


class SubcategoryDTO(BaseModel):
    id: int | None
    name: str | None
