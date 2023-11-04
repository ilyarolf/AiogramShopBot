from sqlalchemy import select

from db import async_session_maker
from models.subcategory import Subcategory


class SubcategoryService:
    @staticmethod
    async def get_or_create_one(subcategory_name: str) -> Subcategory:
        async with async_session_maker() as session:
            stmt = select(Subcategory).where(Subcategory.name == subcategory_name)
            subcategory = await session.execute(stmt)
            subcategory = subcategory.scalar()
            if subcategory is None:
                new_category_obj = Subcategory(name=subcategory_name)
                session.add(new_category_obj)
                await session.commit()
                await session.refresh(new_category_obj)
                return new_category_obj
            else:
                return subcategory
