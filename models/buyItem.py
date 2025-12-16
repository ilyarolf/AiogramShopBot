from pydantic import BaseModel
from sqlalchemy import Column, Integer, ForeignKey, JSON

from models.base import Base


class BuyItem(Base):
    __tablename__ = "buyItem"

    id = Column(Integer, primary_key=True, unique=True, nullable=False)
    buy_id = Column(Integer, ForeignKey("buys.id", ondelete="CASCADE"), nullable=False)
    # ARRAY CRUTCH FOR SQLALCHEMY+SQLITE 🩼
    # item_ids = Column(ARRAY, nullable=False)
    item_ids = Column(JSON, nullable=False)


class BuyItemDTO(BaseModel):
    id: int | None = None
    buy_id: int | None = None
    item_ids: list[int] | None = None
