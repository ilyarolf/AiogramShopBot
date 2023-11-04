from sqlalchemy import select
from typing_extensions import Union

from db import session_maker
from models.category import Category


class CategoryService:
    @staticmethod
    def get_id_by_category_name(category_name: str) -> Union[int, None]:
        with session_maker() as session:
            stmt = select(Category.id).where(Category.name == category_name)
            category_id = session.execute(stmt).scalar()
            return category_id

    @staticmethod
    def add_new_category(category: Category) -> int:
        with session_maker() as session:
            session.add(category)
            session.flush()
            session.commit()
            return category.id
