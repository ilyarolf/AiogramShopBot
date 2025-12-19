from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.buyItem import BuyItem
from models.item import Item, ItemDTO


class ItemRepository:
    """
    Simplified Item repository.
    Items now only belong to a product category (no subcategory).
    Price and description are stored on the Category, not the Item.
    """

    @staticmethod
    async def get_available_qty(category_id: int, session: Session | AsyncSession) -> int:
        """Get count of unsold items for a product category."""
        stmt = (
            select(func.count())
            .select_from(Item)
            .where(Item.category_id == category_id, Item.is_sold == False)
        )
        result = await session_execute(stmt, session)
        return result.scalar() or 0

    @staticmethod
    async def get_purchased_items(category_id: int, quantity: int, session: Session | AsyncSession) -> list[ItemDTO]:
        """Get N unsold items from a product category for purchase."""
        stmt = (
            select(Item)
            .where(Item.category_id == category_id, Item.is_sold == False)
            .limit(quantity)
        )
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]

    @staticmethod
    async def get_by_id(item_id: int, session: Session | AsyncSession) -> ItemDTO:
        """Get single item by ID."""
        stmt = select(Item).where(Item.id == item_id)
        result = await session_execute(stmt, session)
        return ItemDTO.model_validate(result.scalar(), from_attributes=True)

    @staticmethod
    async def get_by_buy_id(buy_id: int, session: Session | AsyncSession) -> list[ItemDTO]:
        """Get items associated with a purchase."""
        stmt = (
            select(Item)
            .join(BuyItem, BuyItem.item_id == Item.id)
            .where(BuyItem.buy_id == buy_id)
        )
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]

    @staticmethod
    async def update(item_dto_list: list[ItemDTO], session: Session | AsyncSession):
        """Update multiple items."""
        for item in item_dto_list:
            item_dict = item.model_dump(exclude_none=True)
            if 'id' in item_dict:
                item_id = item_dict.pop('id')
                stmt = update(Item).where(Item.id == item_id).values(**item_dict)
                await session_execute(stmt, session)

    @staticmethod
    async def set_not_new(session: Session | AsyncSession):
        """Mark all items as not new (after restocking announcement)."""
        stmt = update(Item).values(is_new=False)
        await session_execute(stmt, session)

    @staticmethod
    async def delete_unsold_by_category_id(category_id: int, session: Session | AsyncSession):
        """Delete unsold items for a category."""
        stmt = delete(Item).where(Item.category_id == category_id, Item.is_sold == False)
        await session_execute(stmt, session)

    @staticmethod
    async def add_many(items: list[ItemDTO], session: Session | AsyncSession):
        """Add multiple items."""
        item_objs = [Item(**item.model_dump(exclude_none=True)) for item in items]
        session.add_all(item_objs)

    @staticmethod
    async def get_new(session: Session | AsyncSession) -> list[ItemDTO]:
        """Get newly added items (for restocking announcement)."""
        stmt = select(Item).where(Item.is_new == True)
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]

    @staticmethod
    async def get_in_stock(session: Session | AsyncSession) -> list[ItemDTO]:
        """Get all unsold items (for full stock announcement)."""
        stmt = select(Item).where(Item.is_sold == False)
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]
