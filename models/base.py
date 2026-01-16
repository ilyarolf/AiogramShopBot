from typing import Type

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    pass

    @staticmethod
    def get_model_filtered_dict(
            dto: BaseModel,
            model_class: Type['Base']
    ) -> BaseModel:
        model_columns = {column.name for column in model_class.__table__.columns}
        dto_dict = dto.model_dump()
        return dto.model_validate({
            key: value for key, value in dto_dict.items()
            if key in model_columns
        })
