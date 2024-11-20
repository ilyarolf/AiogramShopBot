from db import get_db_session, session_commit, session_refresh
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
