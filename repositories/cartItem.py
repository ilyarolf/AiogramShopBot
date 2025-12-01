import math

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_flush, session_execute
from models.cart import Cart, CartDTO
from models.cartItem import CartItemDTO, CartItem


class CartItemRepository:
    @staticmethod
    async def create(cart_item: CartItemDTO, session: AsyncSession | Session) -> int:
        cart_item = CartItem(**cart_item.model_dump())
        session.add(cart_item)
        await session_flush(session)
        return cart_item.id

    @staticmethod
    async def get_by_user_id(user_id: int, page: int, session: AsyncSession | Session) -> list[CartItemDTO]:
        stmt = (select(CartItem)
                .join(Cart, CartItem.cart_id == Cart.id)
                .where(Cart.user_id == user_id)
                .limit(config.PAGE_ENTRIES)
                .offset(config.PAGE_ENTRIES * page))
        cart_items = await session_execute(stmt, session)
        return [CartItemDTO.model_validate(cart_item, from_attributes=True) for cart_item in
                cart_items.scalars().all()]

    @staticmethod
    async def get_maximum_page(user_id: int, session: AsyncSession | Session) -> int:
        sub_stmt = (select(CartItem)
                    .join(Cart, CartItem.cart_id == Cart.id)
                    .where(Cart.user_id == user_id))
        stmt = select(func.count()).select_from(sub_stmt)
        max_page = await session_execute(stmt, session)
        max_page = max_page.scalar_one()
        if max_page % config.PAGE_ENTRIES == 0:
            return max_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_all_by_user_id(user_id: int, session: AsyncSession | Session) -> list[CartItemDTO]:
        stmt = select(CartItem).join(Cart, CartItem.cart_id == Cart.id).where(Cart.user_id == user_id)
        cart_items = await session_execute(stmt, session)
        return [CartItemDTO.model_validate(cart_item, from_attributes=True) for cart_item in
                cart_items.scalars().all()]

    @staticmethod
    async def remove_from_cart(cart_item_id: int, session: AsyncSession | Session):
        stmt = delete(CartItem).where(CartItem.id == cart_item_id)
        await session_execute(stmt, session)

    @staticmethod
    async def get_by_primary_key(cart_item_id: int, session: AsyncSession) -> CartItemDTO:
        stmt = select(CartItem).where(CartItem.id == cart_item_id)
        cart_item = await session_execute(stmt, session)
        return CartItemDTO.model_validate(cart_item.scalar_one(), from_attributes=True)

    @staticmethod
    async def update(cart_item_dto: CartItemDTO, session: AsyncSession):
        stmt = update(CartItem).where(CartItem.id == cart_item_dto.id).values(**cart_item_dto.model_dump())
        await session.execute(stmt)

    @staticmethod
    async def get_current_cart_content(cart_item_dto: CartItemDTO,
                                       cart_dto: CartDTO,
                                       session: AsyncSession) -> CartItemDTO | None:
        stmt = (select(CartItem)
                .join(Cart, Cart.id == CartItem.cart_id)
                .where(Cart.id == cart_dto.id,
                       CartItem.category_id == cart_item_dto.category_id,
                       CartItem.subcategory_id == cart_item_dto.subcategory_id))
        cart_content = await session_execute(stmt, session)
        cart_content = cart_content.scalar_one_or_none()
        if cart_content is not None:
            cart_content = CartItemDTO.model_validate(cart_content, from_attributes=True)
        return cart_content
