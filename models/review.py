from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import Integer, Column, String, SmallInteger, DateTime, CheckConstraint, ForeignKey

from models.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    buyItem_id = Column(Integer, ForeignKey("buyItem.id", ondelete="CASCADE"), nullable=False, unique=True)
    text = Column(String, nullable=True)
    image_id = Column(String, nullable=True)
    rating = Column(SmallInteger, nullable=False)
    create_datetime = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint('rating >= 1 and review_rating <= 5', name='check_review_rating_value'),
        CheckConstraint('length(text) <= 512', name='check_review_text_length'),
    )


class ReviewDTO(BaseModel):
    id: int | None = None
    buyItem_id: int | None = None
    text: str | None = None
    image_id: str | None = None
    rating: int
    create_datetime: datetime | None = datetime.now(tz=timezone.utc)
