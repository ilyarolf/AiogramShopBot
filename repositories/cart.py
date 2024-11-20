from sqlalchemy import select, update

from db import get_db_session, session_execute, session_commit, session_refresh
from models.cart import Cart, CartDTO
from models.cartItem import CartItemDTO, CartItem
from repositories.cartItem import CartItemRepository


class CartRepository:
    @staticmethod
    async def get_or_create(user_id: int):
        stmt = select(Cart).where(Cart.user_id == user_id)
        async with get_db_session() as session:
            cart = await session_execute(stmt, session)
            cart = cart.scalar()
            if cart is None:
                cart = Cart(user_id=user_id)
                session.add(cart)
                await session_commit(session)
                await session_refresh(session, cart)
                return CartDTO.model_validate(cart, from_attributes=True)
            else:
                return CartDTO.model_validate(cart, from_attributes=True)

    @staticmethod
    async def add_to_cart(cart_item: CartItemDTO, cart: CartDTO):
        async with get_db_session() as session:
            # if there exists a cart with a cart_item with the same category and subcategory, increase the quantity
            # and if not, there is either no cart_item in the cart at all or no cart_item of the same (sub-)category
            get_old_cart_content_stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id).where(
                Cart.id == cart.id,
                CartItem.subcategory_id == cart_item.subcategory_id)
            old_cart_records = await session_execute(get_old_cart_content_stmt, session)
            old_cart_records = old_cart_records.scalar()

            if old_cart_records is None:
                await CartItemRepository.create(cart_item)
            elif old_cart_records is not None:
                quantity_update_stmt = (update(CartItem).where(CartItem.cart_id == cart.id)
                                        .values(quantity=CartItem.quantity + cart_item.quantity))
                await session_execute(quantity_update_stmt, session)
            await session_commit(session)
