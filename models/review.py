from datetime import datetime, timezone

from pydantic import BaseModel
from sqladmin import ModelView
from sqlalchemy import Integer, Column, String, SmallInteger, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    buyItem_id = Column(Integer, ForeignKey("buyItem.id", ondelete="CASCADE"), nullable=False, unique=True)
    buy_item = relationship(
        "BuyItem",
        back_populates="review"
    )
    text = Column(String, nullable=True)
    image_id = Column(String, nullable=True)
    rating = Column(SmallInteger, nullable=False)
    create_datetime = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint('rating >= 1 and review_rating <= 5', name='check_review_rating_value'),
        CheckConstraint('length(text) <= 512', name='check_review_text_length'),
    )

    def __repr__(self):
        return self.rating * "⭐️"


class ReviewDTO(BaseModel):
    id: int | None = None
    buyItem_id: int | None = None
    text: str | None = None
    image_id: str | None = None
    rating: int
    create_datetime: datetime | None = datetime.now(tz=timezone.utc)


class ReviewAdmin(ModelView, model=Review):
    column_exclude_list = [Review.buyItem_id,
                           Review.image_id]
    name = "Review"
    name_plural = "Reviews"
    can_delete = True
    can_edit = True
    can_create = False
    can_export = False
    column_sortable_list = [Review.id,
                            Review.rating,
                            Review.create_datetime,
                            Review.text]
