from sqlalchemy import Column, Integer, String, Float, Boolean

from models.base import Base


class Item(Base):
    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, unique=True)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=False)
    private_data = Column(String, nullable=False, unique=False)
    price = Column(Float, nullable=False)
    is_sold = Column(Boolean, nullable=False, default=False)
    is_new = Column(Boolean, nullable=False, default=True)
    description = Column(String, nullable=False)
