from sqlalchemy import select, func, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.buyItem import BuyItem
from models.item import Item, ItemDTO


class ItemRepository:

    @staticmethod
    async def get_available_qty(category_id: int | None, subcategory_id: int, session: AsyncSession) -> int:
        conditions = [
            Item.subcategory_id == subcategory_id,
            Item.is_sold == False
        ]
        if category_id:
            conditions.append(Item.category_id == category_id)
        sub_stmt = (select(Item)
                    .where(and_(*conditions)))
        stmt = select(func.count()).select_from(sub_stmt)
        available_qty = await session_execute(stmt, session)
        return available_qty.scalar()

    @staticmethod
    async def get_single(category_id: int | None, subcategory_id: int, session: AsyncSession) -> ItemDTO:
        conditions = [
            Item.subcategory_id == subcategory_id,
            Item.is_sold == False
        ]
        if category_id:
            conditions.append(Item.category_id == category_id)
        columns_to_select = [column for column in Item.__table__.columns if column.name != 'id']
        stmt = (select(*columns_to_select).where(and_(*conditions))).distinct()

        item = await session_execute(stmt, session)
        return ItemDTO.model_validate(item.one(), from_attributes=True)

    @staticmethod
    async def get_by_id(item_id: int, session: AsyncSession) -> ItemDTO:
        stmt = select(Item).where(Item.id == item_id)
        item = await session_execute(stmt, session)
        return ItemDTO.model_validate(item.scalar(), from_attributes=True)

    @staticmethod
    async def get_purchased_items(category_id: int, subcategory_id: int, quantity: int,
                                  session: Session | AsyncSession) -> list[ItemDTO]:
        stmt = (select(Item)
                .where(Item.category_id == category_id, Item.subcategory_id == subcategory_id,
                       Item.is_sold == False).limit(quantity))
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def update(item_dto_list: list[ItemDTO], session: AsyncSession):
        for item in item_dto_list:
            stmt = update(Item).where(Item.id == item.id).values(**item.model_dump())
            await session_execute(stmt, session)

    @staticmethod
    async def get_by_buy_id(buy_id: int, session: AsyncSession) -> list[ItemDTO]:
        stmt = (
            select(Item)
            .join(BuyItem, BuyItem.item_id == Item.id)
            .where(BuyItem.buy_id == buy_id)
        )
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]

    @staticmethod
    async def set_not_new(session: AsyncSession):
        stmt = update(Item).values(is_new=False)
        await session_execute(stmt, session)

    @staticmethod
    async def delete_unsold_by_category_id(entity_id: int, session: AsyncSession):
        stmt = delete(Item).where(Item.category_id == entity_id, Item.is_sold == False)
        await session_execute(stmt, session)

    @staticmethod
    async def delete_unsold_by_subcategory_id(entity_id: int, session: AsyncSession):
        stmt = delete(Item).where(Item.subcategory_id == entity_id, Item.is_sold == False)
        await session_execute(stmt, session)

    @staticmethod
    async def add_many(items: list[ItemDTO], session: AsyncSession):
        items = [Item(**item.model_dump()) for item in items]
        session.add_all(items)

    @staticmethod
    async def get_new(session: AsyncSession) -> list[ItemDTO]:
        stmt = select(Item).where(Item.is_new == True)
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def get_in_stock(session: AsyncSession) -> list[ItemDTO]:
        stmt = select(Item).where(Item.is_sold == False)
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]
