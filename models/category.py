from pydantic import BaseModel
from sqlalchemy import Integer, Column, String

from models.base import Base


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    media_id = Column(String, nullable=False)


class CategoryDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    media_id: str | None = None
