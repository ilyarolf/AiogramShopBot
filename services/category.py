from sqlalchemy import select

from db import async_session_maker
from models.category import Category
from models.item import Item


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

    @staticmethod
    async def get_by_primary_key(primary_key: int) -> Category:
        async with async_session_maker() as session:
            stmt = select(Category).where(Category.id == primary_key)
            category = await session.execute(stmt)
            return category.scalar()

    @staticmethod
    async def get_all_categories():
        async with async_session_maker() as session:
            stmt = select(Category).distinct()
            categories = await session.execute(stmt)
            return categories.scalars().all()

    @staticmethod
    async def get_unsold() -> list[Category]:
        async with async_session_maker() as session:
            stmt = select(Category).join(Item, Item.category_id == Category.id).where(Item.is_sold == 0).distinct()
            category_names = await session.execute(stmt)
            return category_names.scalars().all()

    @staticmethod
    async def delete_if_not_used(category_id: int):
        # TODO("Automaticaly delete subcategories if category not used")
        async with async_session_maker() as session:
            stmt = select(Category).join(Item, Item.category_id == category_id).where(
                Category.id == category_id)
            result = await session.execute(stmt)
            if result.scalar() is None:
                get_stmt = select(Category).where(Category.id == category_id)
                category = await session.execute(get_stmt)
                category = category.scalar()
                await session.delete(category)

                await session.commit()
