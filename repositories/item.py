from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from enums.item_type import ItemType
from models.buyItem import BuyItem
from models.item import Item, ItemDTO, ItemAvailabilityDTO


class ItemRepository:

    @staticmethod
    async def get_available_qty(item_type: ItemType | None, category_id: int | None, subcategory_id: int,
                                session: AsyncSession) -> int:
        conditions = [
            Item.subcategory_id == subcategory_id,
            Item.is_sold == False,
        ]
        if item_type:
            conditions.append(Item.item_type == item_type)
        if category_id:
            conditions.append(Item.category_id == category_id)
        sub_stmt = (select(Item)
                    .where(and_(*conditions)))
        stmt = select(func.count()).select_from(sub_stmt)
        available_qty = await session_execute(stmt, session)
        return available_qty.scalar()

    @staticmethod
    async def get_single(item_type: ItemType | None,
                         category_id: int | None,
                         subcategory_id: int,
                         session: AsyncSession) -> ItemDTO:
        conditions = [
            Item.subcategory_id == subcategory_id,
            Item.is_sold == False
        ]
        if item_type:
            conditions.append(Item.item_type == item_type)
        if category_id:
            conditions.append(Item.category_id == category_id)
        columns_to_select = [column for column in Item.__table__.columns if column.name != 'id']
        stmt = (select(*columns_to_select).where(and_(*conditions))).distinct().limit(1)

        item = await session_execute(stmt, session)
        return ItemDTO.model_validate(item.one(), from_attributes=True)

    @staticmethod
    async def get_by_id(item_id: int, session: AsyncSession) -> ItemDTO:
        stmt = select(Item).where(Item.id == item_id)
        item = await session_execute(stmt, session)
        return ItemDTO.model_validate(item.scalar(), from_attributes=True)

    @staticmethod
    async def get_by_id_map(item_ids: list[int], session: AsyncSession | Session) -> dict[int, ItemDTO]:
        items = await ItemRepository.get_by_id_list(item_ids, session)
        return {item.id: item for item in items if item.id is not None}

    @staticmethod
    async def get_purchased_items(category_id: int, subcategory_id: int, quantity: int,
                                  session: Session | AsyncSession) -> list[ItemDTO]:
        stmt = (select(Item)
                .where(Item.category_id == category_id,
                       Item.subcategory_id == subcategory_id,
                       Item.is_sold == False)
                .limit(quantity)
                .with_for_update())
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def update(item_dto_list: list[ItemDTO], session: AsyncSession):
        for item in item_dto_list:
            item = Item.get_model_filtered_dict(item, Item)
            stmt = update(Item).where(Item.id == item.id).values(**item.model_dump(exclude_none=True))
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
        items = [Item(**item.model_dump(exclude_none=True)) for item in items]
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

    @staticmethod
    async def get_by_id_list(item_ids: list[int], session: AsyncSession) -> list[ItemDTO]:
        stmt = select(Item).where(Item.id.in_(item_ids))
        items = await session_execute(stmt, session)
        return [ItemDTO.model_validate(item, from_attributes=True) for item in items.scalars().all()]

    @staticmethod
    async def get_availability_by_cart_items(
            cart_items: list,
            session: AsyncSession | Session
    ) -> dict[tuple[ItemType, int, int], ItemAvailabilityDTO]:
        unique_keys = sorted({
            (cart_item.item_type, cart_item.category_id, cart_item.subcategory_id)
            for cart_item in cart_items
        }, key=lambda item: (item[0].value, item[1], item[2]))
        if not unique_keys:
            return {}

        conditions = [
            and_(
                Item.item_type == item_type,
                Item.category_id == category_id,
                Item.subcategory_id == subcategory_id,
            )
            for item_type, category_id, subcategory_id in unique_keys
        ]
        partition_by = (Item.item_type, Item.category_id, Item.subcategory_id)
        ranked_items = (
            select(
                Item.item_type,
                Item.category_id,
                Item.subcategory_id,
                Item.price,
                Item.description,
                func.count().over(partition_by=partition_by).label("available_qty"),
                func.row_number().over(partition_by=partition_by, order_by=Item.id).label("row_number"),
            )
            .where(Item.is_sold == False, or_(*conditions))
            .subquery()
        )
        stmt = (
            select(
                ranked_items.c.item_type,
                ranked_items.c.category_id,
                ranked_items.c.subcategory_id,
                ranked_items.c.price,
                ranked_items.c.description,
                ranked_items.c.available_qty,
            )
            .where(ranked_items.c.row_number == 1)
        )
        rows = await session_execute(stmt, session)
        result: dict[tuple[ItemType, int, int], ItemAvailabilityDTO] = {}
        for row in rows.mappings().all():
            dto = ItemAvailabilityDTO.model_validate(row, from_attributes=True)
            result[(dto.item_type, dto.category_id, dto.subcategory_id)] = dto
        return result

    @staticmethod
    async def get_available_item_types(session: AsyncSession) -> list[ItemType]:
        stmt = select(Item.item_type).where(Item.is_sold == False).distinct()
        item_types = await session_execute(stmt, session)
        return [ItemType(item_type) for item_type in item_types.scalars().all()]
