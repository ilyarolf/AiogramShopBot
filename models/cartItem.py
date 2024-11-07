from sqlalchemy import Column, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, relationship, mapped_column

from models.base import Base

class CartItem(Base):

    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    cart: Mapped["Cart"] = relationship(back_populates="cart_items")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category_name: Mapped[str] = mapped_column(default=None, nullable=True)
    subcategory_id: Mapped[int] = mapped_column(ForeignKey("subcategories.id"), passive_deletes="all")
    subcategory_name: Mapped[str] = mapped_column(default=None, nullable=True)
    quantity = Column(Integer, default=0)
    a_piece_price = Column(Float, default=0.0)
