from pydantic import BaseModel
from sqlalchemy import Column, String, Float, Boolean, Integer

from models.base import Base


class ShippingOption(Base):
    __tablename__ = "shipping_options"

    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Float, nullable=False)
    is_disabled = Column(Boolean, default=False)


class ShippingOptionDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    price: float | None = None
    is_disabled: bool = False
