from sqlalchemy import select

from db import async_session_maker
from models.item import Item
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

    @staticmethod
    async def get_all() -> list[Subcategory]:
        async with async_session_maker() as session:
            stmt = select(Subcategory).distinct()
            subcategories = await session.execute(stmt)
            subcategories = subcategories.scalars().all()
            return subcategories

    @staticmethod
    async def get_by_primary_key(subcategory_id) -> Subcategory:
        async with async_session_maker() as session:
            stmt = select(Subcategory).where(Subcategory.id == subcategory_id)
            subcategory = await session.execute(stmt)
            return subcategory.scalar()

    @staticmethod
    async def delete_if_not_used(subcategory_id: int):
        # TODO("Need testing")
        async with async_session_maker() as session:
            stmt = select(Subcategory).join(Item, Item.subcategory_id == subcategory_id).where(
                Subcategory.id == subcategory_id)
            result = await session.execute(stmt)
            if result.scalar() is None:
                get_stmt = select(Subcategory).where(Subcategory.id == subcategory_id)
                subcategory = await session.execute(get_stmt)
                subcategory = subcategory.scalar()
                await session.delete(subcategory)
                await session.commit()
