from sqlalchemy import select, func

from db import get_db_session, session_execute
from models.item import Item


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
    async def get_available_qty(category_id: int, subcategory_id: int):
        sub_stmt = (select(Item)
                    .where(Item.category_id == category_id,
                           Item.subcategory_id == subcategory_id,
                           Item.is_sold is False))
        stmt = select(func.count()).select_from(sub_stmt)
        async with get_db_session() as session:
            available_qty = await session_execute(stmt, session)
            return available_qty.scalar()
