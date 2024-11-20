from sqlalchemy import select, func

from db import get_db_session, session_execute
from models.item import Item, ItemDTO


class ItemRepository:

    @staticmethod
    async def get_price(category_id: int, subcategory_id: int) -> float:
        stmt = (select(Item.price)
                .where(Item.category_id == category_id,
                       Item.subcategory_id == subcategory_id)
                .limit(1))
        async with get_db_session() as session:
            price = await session_execute(stmt, session)
            return price.scalar()

    @staticmethod
    async def get_available_qty(category_id: int, subcategory_id: int) -> int:
        sub_stmt = (select(Item)
                    .where(Item.category_id == category_id,
                           Item.subcategory_id == subcategory_id,
                           Item.is_sold == False))
        stmt = select(func.count()).select_from(sub_stmt)
        async with get_db_session() as session:
            available_qty = await session_execute(stmt, session)
            return available_qty.scalar()

    @staticmethod
    async def get_single(category_id: int, subcategory_id: int):
        stmt = (select(Item)
                .where(Item.category_id == category_id,
                       Item.subcategory_id == subcategory_id,
                       Item.is_sold == False)
                .limit(1))
        async with get_db_session() as session:
            item = await session_execute(stmt, session)
            return ItemDTO.model_validate(item.scalar(), from_attributes=True)

