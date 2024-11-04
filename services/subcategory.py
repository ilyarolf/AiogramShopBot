import math
from typing import Union

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_commit, session_execute, session_refresh
from models.item import Item
from models.subcategory import Subcategory


class SubcategoryService:
    items_per_page = config.PAGE_ENTRIES

    @staticmethod
    async def get_or_create_one(subcategory_name: str, session: Union[AsyncSession, Session]) -> Subcategory:
        stmt = select(Subcategory).where(Subcategory.name == subcategory_name)
        subcategory = await session_execute(stmt, session)
        subcategory = subcategory.scalar()
        if subcategory is None:
            new_category_obj = Subcategory(name=subcategory_name)
            session.add(new_category_obj)
            await session_commit(session)
            await session_refresh(session, new_category_obj)
            return new_category_obj
        else:
            return subcategory

    @staticmethod
    async def get_all(session: Union[AsyncSession, Session], page: int = 0) -> list[Subcategory]:
        stmt = select(Subcategory).distinct().limit(SubcategoryService.items_per_page).offset(
            page * SubcategoryService.items_per_page).group_by(Subcategory.name)
        subcategories = await session_execute(stmt, session=session)
        subcategories = subcategories.scalars().all()
        return subcategories

    @staticmethod
    async def get_maximum_page(session: Union[AsyncSession, Session]):
        stmt = select(func.count(Subcategory.id)).distinct()
        subcategories = await session_execute(stmt, session)
        subcategories_count = subcategories.scalar_one()
        if subcategories_count % SubcategoryService.items_per_page == 0:
            return subcategories_count / SubcategoryService.items_per_page - 1
        else:
            return math.trunc(subcategories_count / SubcategoryService.items_per_page)

    @staticmethod
    async def get_by_primary_key(subcategory_id: int, session: Union[AsyncSession, Session]) -> Subcategory:
        stmt = select(Subcategory).where(Subcategory.id == subcategory_id)
        subcategory = await session_execute(stmt, session)
        return subcategory.scalar()

    @staticmethod
    async def delete_if_not_used(subcategory_id: int, session: Union[AsyncSession, Session]):
        # TODO("Need testing")
        stmt = select(Subcategory).join(Item, Item.subcategory_id == subcategory_id).where(
            Subcategory.id == subcategory_id)
        result = await session_execute(stmt, session)
        if result.scalar() is None:
            stmt = delete(Subcategory).where(Subcategory.id == subcategory_id)
            await session_execute(stmt, session)
            await session_commit(session)
