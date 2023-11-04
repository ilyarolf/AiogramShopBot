from sqlalchemy import select

from db import async_session_maker
from models.category import Category


class CategoryService:
    @staticmethod
    async def get_or_create_one(category_name: str) -> Category:
        async with async_session_maker() as session:
            stmt = select(Category).where(Category.name == category_name)
            category = await session.execute(stmt)
            category = category.scalar()
            if category is None:
                new_category_obj = Category(name=category_name)
                session.add(new_category_obj)
                await session.commit()
                await session.refresh(new_category_obj)
                return new_category_obj
            else:
                return category

