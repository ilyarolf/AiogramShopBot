import math

from sqlalchemy import select, delete

import config
from db import get_db_session, session_commit, session_refresh, session_execute
from models.cart import Cart
from models.cartItem import CartItemDTO, CartItem


class CartItemRepository:
    @staticmethod
    async def create(cart_item: CartItemDTO) -> int:
        cart_item = CartItem(**cart_item.model_dump())
        async with get_db_session() as session:
            session.add(cart_item)
            await session_commit(session)
            await session_refresh(session, cart_item)
            return cart_item.id

    @staticmethod
    async def get_by_user_id(user_id: int, page: int) -> list[CartItemDTO]:
        stmt = select(CartItem).join(Cart, CartItem.cart_id == Cart.id).where(Cart.user_id == user_id).limit(
            config.PAGE_ENTRIES).offset(config.PAGE_ENTRIES * page)
        async with get_db_session() as session:
            cart_items = await session_execute(stmt, session)
            return [CartItemDTO.model_validate(cart_item, from_attributes=True) for cart_item in
                    cart_items.scalars().all()]

    @staticmethod
    async def get_maximum_page(user_id: int) -> int:
        max_page = len(await CartItemRepository.get_all_by_user_id(user_id))
        if max_page % config.PAGE_ENTRIES == 0:
            return max_page / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_all_by_user_id(user_id: int) -> list[CartItemDTO]:
        stmt = select(CartItem).join(Cart, CartItem.cart_id == Cart.id).where(Cart.user_id == user_id)
        async with get_db_session() as session:
            cart_items = await session_execute(stmt, session)
            return [CartItemDTO.model_validate(cart_item, from_attributes=True) for cart_item in
                    cart_items.scalars().all()]

    @staticmethod
    async def remove_from_cart(cart_item_id: int):
        stmt = delete(CartItem).where(CartItem.id == cart_item_id)
        async with get_db_session() as session:
            await session_execute(stmt, session)
            await session_commit(session)
