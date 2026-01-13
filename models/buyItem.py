from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Column, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from models.base import Base


class BuyItem(Base):
    __tablename__ = "buyItem"

    id = Column(Integer, primary_key=True)
    buy_id = Column(Integer, ForeignKey("buys.id", ondelete="CASCADE"), nullable=False)
    buy = relationship(
        "Buy",
        back_populates="buy_items"
    )
    # ARRAY CRUTCH FOR SQLALCHEMY+SQLITE 🩼
    # item_ids = Column(ARRAY, nullable=False)
    item_ids = Column(JSON, nullable=False)
    review = relationship(
        "Review",
        back_populates="buy_item",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"BuyItem ID:{self.id}"


class BuyItemDTO(BaseModel):
    id: int | None = None
    buy_id: int | None = None
    item_ids: list[int] | None = None


class BuyItemAdmin(ModelView, model=BuyItem):
    can_create = False
    column_exclude_list = [BuyItem.buy_id]
