from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute, session_flush
from models.cart import Cart, CartDTO


class CartRepository:
    @staticmethod
    async def get_or_create(user_id: int, session: AsyncSession | Session):
        stmt = select(Cart).where(Cart.user_id == user_id)
        cart = await session_execute(stmt, session)
        cart = cart.scalar()
        if cart is None:
            cart = Cart(user_id=user_id)
            session.add(cart)
            await session_flush(session)
        return CartDTO.model_validate(cart, from_attributes=True)
