from pydantic import BaseModel
from sqlalchemy import Integer, Column, String, Enum

from enums.keyboard_button import KeyboardButton
from models.base import Base


class ButtonMedia(Base):
    __tablename__ = "buttons_media"

    id = Column(Integer, primary_key=True)
    media_id = Column(String, nullable=False)
    button = Column(Enum(KeyboardButton), unique=True)


class ButtonMediaDTO(BaseModel):
    id: int | None = None
    media_id: str | None = None
    button: KeyboardButton | None = None
