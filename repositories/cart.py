from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute, session_flush
from models.cart import Cart, CartDTO
from models.cartItem import CartItemDTO, CartItem
from repositories.cartItem import CartItemRepository


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
        else:
            return CartDTO.model_validate(cart, from_attributes=True)

    @staticmethod
    async def add_to_cart(cart_item: CartItemDTO, cart: CartDTO, session: AsyncSession | Session):
        """
        Add item to cart. If same product category already exists, increase quantity.
        Uses category_id (product category) as the key for matching.
        """
        # Check if there's already a cart item with the same product category
        get_old_cart_content_stmt = select(Cart).join(
            CartItem, Cart.id == CartItem.cart_id).where(
            Cart.id == cart.id,
            CartItem.category_id == cart_item.category_id)
        old_cart_records = await session_execute(get_old_cart_content_stmt, session)
        old_cart_records = old_cart_records.scalar()

        if old_cart_records is None:
            await CartItemRepository.create(cart_item, session)
        elif old_cart_records is not None:
            quantity_update_stmt = (update(CartItem)
                                    .where(CartItem.cart_id == cart.id, CartItem.category_id == cart_item.category_id)
                                    .values(quantity=CartItem.quantity + cart_item.quantity))
            await session_execute(quantity_update_stmt, session)
