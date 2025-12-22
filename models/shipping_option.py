from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Column, String, Float, Boolean, Integer
from sqlalchemy.orm import relationship

from models.base import Base


class ShippingOption(Base):
    __tablename__ = "shipping_options"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Float, nullable=False)
    is_disabled = Column(Boolean, default=False)
    buys = relationship("Buy", back_populates="shipping_option")


class ShippingOptionDTO(BaseModel):
    id: int | None = None
    name: str | None = None
    price: float | None = None
    is_disabled: bool = False


class ShippingOptionAdmin(ModelView, model=ShippingOption):
    column_exclude_list = [ShippingOption.buys]
