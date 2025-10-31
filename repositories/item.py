from datetime import datetime

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.buyItem import BuyItem
from models.item import Item, ItemDTO


class ItemRepository:

    @staticmethod
    async def get_price(item_dto: ItemDTO, session: Session | AsyncSession) -> float:
        stmt = (select(Item.price)
                .where(Item.category_id == item_dto.category_id,
                       Item.subcategory_id == item_dto.subcategory_id)
                .limit(1))
        price = await session_execute(stmt, session)
        return price.scalar()

    @staticmethod
    async def get_available_qty(item_dto: ItemDTO, session: Session | AsyncSession) -> int:
        sub_stmt = (select(Item)
                    .where(Item.category_id == item_dto.category_id,
                           Item.subcategory_id == item_dto.subcategory_id,
                           Item.is_sold == False,
                           Item.order_id == None))  # Only count unreserved items
        stmt = select(func.count()).select_from(sub_stmt)
        available_qty = await session_execute(stmt, session)
        return available_qty.scalar()

    @staticmethod
    async def get_single(category_id: int, subcategory_id: int, session: Session | AsyncSession) -> ItemDTO | None:
        """
        Get a single item for display purposes (price, description).
        Includes reserved items since we just need metadata, not actual purchase.
        For availability check, use get_available_qty().

        Returns:
            ItemDTO if found, None if no items exist for this category/subcategory
        """
        stmt = (select(Item)
                .where(Item.category_id == category_id,
                       Item.subcategory_id == subcategory_id,
                       Item.is_sold == False)  # Include reserved items
                .limit(1))
        item = await session_execute(stmt, session)
        result = item.scalar()

        if result is None:
            return None

        return ItemDTO.model_validate(result, from_attributes=True)

    @staticmethod
    async def get_by_id(item_id: int, session: Session | AsyncSession) -> ItemDTO:
        stmt = select(Item).where(Item.id == item_id)
        item = await session_execute(stmt, session)
        return ItemDTO.model_validate(item.scalar(), from_attributes=True)

    @staticmethod
    async def get_purchased_items(category_id: int, subcategory_id: int, quantity: int, session: Session | AsyncSession) -> list[ItemDTO]:
        stmt = (select(Item)
                .where(Item.category_id == category_id, Item.subcategory_id == subcategory_id,
                       Item.is_sold == False,
                       Item.order_id == None)  # Only get unreserved items
                .limit(quantity))
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def update(item_dto_list: list[ItemDTO], session: Session | AsyncSession):
        for item in item_dto_list:
            stmt = update(Item).where(Item.id == item.id).values(**item.model_dump())
            await session_execute(stmt, session)

    @staticmethod
    async def get_by_buy_id(buy_id: int, session: Session | AsyncSession) -> list[ItemDTO]:
        stmt = (
            select(Item)
            .join(BuyItem, BuyItem.item_id == Item.id)
            .where(BuyItem.buy_id == buy_id)
        )
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]

    @staticmethod
    async def set_not_new(session: Session | AsyncSession):
        stmt = update(Item).values(is_new=False)
        await session_execute(stmt, session)

    @staticmethod
    async def delete_unsold_by_category_id(entity_id: int, session: Session | AsyncSession):
        stmt = delete(Item).where(Item.category_id == entity_id, Item.is_sold == False)
        await session_execute(stmt, session)

    @staticmethod
    async def delete_unsold_by_subcategory_id(entity_id: int, session: Session | AsyncSession):
        stmt = delete(Item).where(Item.subcategory_id == entity_id, Item.is_sold == False)
        await session_execute(stmt, session)

    @staticmethod
    async def add_many(items: list[ItemDTO], session: Session | AsyncSession):
        items = [Item(**item.model_dump()) for item in items]
        session.add_all(items)

    @staticmethod
    async def get_new(session: Session | AsyncSession) -> list[ItemDTO]:
        stmt = select(Item).where(Item.is_new == True)
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def get_in_stock(session: Session | AsyncSession) -> list[ItemDTO]:
        stmt = select(Item).where(Item.is_sold == False)
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def get_available_quantity_for_subcategory(
        subcategory_id: int,
        session: Session | AsyncSession
    ) -> int:
        """
        Returns the number of available items for a subcategory (not sold, not reserved).

        Args:
            subcategory_id: Subcategory ID
            session: Database session

        Returns:
            Number of available items
        """
        stmt = select(func.count()).select_from(
            select(Item)
            .where(Item.subcategory_id == subcategory_id)
            .where(Item.is_sold == False)
            .where(Item.order_id == None)
        )
        result = await session_execute(stmt, session)
        return result.scalar()

    @staticmethod
    async def reserve_items_for_order(
        subcategory_id: int,
        quantity: int,
        order_id: int,
        session: Session | AsyncSession
    ) -> tuple[list[ItemDTO], int]:
        """
        Reserves items for an order, taking what's available (partial reservation allowed).
        Uses SELECT FOR UPDATE for race-condition safety.

        Args:
            subcategory_id: Subcategory ID
            quantity: Requested quantity
            order_id: Order ID
            session: Database session

        Returns:
            Tuple of (reserved_items, requested_quantity)
            - reserved_items: List of reserved ItemDTOs (may be less than requested)
            - requested_quantity: Original requested quantity for tracking
        """
        # SELECT FOR UPDATE: Lock available items atomically
        stmt = (
            select(Item)
            .where(Item.subcategory_id == subcategory_id)
            .where(Item.is_sold == False)
            .where(Item.order_id == None)  # Only unreserved items
            .limit(quantity)
            .with_for_update()  # 🔒 Row-Level Lock!
        )

        result = await session_execute(stmt, session)
        items = result.scalars().all()

        # Reserve whatever is available (no error if less than requested)
        for item in items:
            item.order_id = order_id
            item.reserved_at = datetime.now()

        return [ItemDTO.model_validate(item, from_attributes=True) for item in items], quantity

    @staticmethod
    async def get_by_order_id(order_id: int, session: Session | AsyncSession) -> list[ItemDTO]:
        """Holt alle Items einer Order"""
        stmt = select(Item).where(Item.order_id == order_id)
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]

    @staticmethod
    async def get_sold_items_by_subcategory(
        subcategory_id: int,
        category_id: int,
        price: float,
        limit: int,
        session: Session | AsyncSession
    ) -> list[ItemDTO]:
        """
        Get sold items (is_sold=true) for a specific subcategory/category/price combination.
        Used for stock restoration when orders are cancelled.

        Args:
            subcategory_id: Subcategory ID
            category_id: Category ID
            price: Item price
            limit: Maximum number of items to return
            session: Database session

        Returns:
            List of sold ItemDTOs matching the criteria
        """
        stmt = (
            select(Item)
            .where(Item.subcategory_id == subcategory_id)
            .where(Item.category_id == category_id)
            .where(Item.price == price)
            .where(Item.is_sold == True)
            .where(Item.order_id == None)  # Not currently reserved
            .limit(limit)
        )
        result = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in result.scalars().all()]


