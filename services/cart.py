import math
from sqlalchemy import select, update
import config
from db import get_db_session, session_execute, session_commit, session_refresh
from models.cart import Cart
from models.cartItem import CartItem
from services.cartItem import CartItemService
from services.user import UserService


class CartService:

    @staticmethod
    async def get_or_create_cart(user_id: int) -> Cart:
        async with get_db_session() as session:
            stmt = select(Cart).where(Cart.user_id == user_id)
            cart = await session_execute(stmt, session)
            cart = cart.scalar()
            if cart is None:
                new_cart_obj = Cart(user_id=user_id)
                session.add(new_cart_obj)
                await session_commit(session)
                await session_refresh(session, new_cart_obj)
                return new_cart_obj
            else:
                return cart

    @staticmethod
    async def get_cart_by_primary_key(primary_key: int) -> Cart:
        async with get_db_session() as session:
            stmt = select(Cart).where(Cart.id == primary_key)
            cart = await session_execute(stmt, session)
            return cart.scalar()

    @staticmethod
    async def get_cart_by_user_id(user_id: int) -> Cart:
        async with get_db_session() as session:
            stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id).where(Cart.user_id == user_id)
            cart = await session_execute(stmt, session)
            return cart.scalar()

    @staticmethod
    async def add_to_cart(cart_item: CartItem, cart: Cart):
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
                await CartService.create_cart_item(CartItem(
                    cart_id=cart.id,
                    category_id=cart_item.category_id,
                    subcategory_id=cart_item.subcategory_id,
                    quantity=cart_item.quantity)
                )
            elif old_cart_records is not None:
                quantity_update_stmt = (update(CartItem).where(CartItem.cart_id == cart.id)
                                        .values(quantity=CartItem.quantity + cart_item.quantity))
                await session_execute(quantity_update_stmt, session)
            await session.commit()

    @staticmethod
    async def create_cart_item(cart_item: CartItem) -> int:
        async with get_db_session() as session:
            session.add(cart_item)
            await session.commit()
            await session.refresh(cart_item)
            return cart_item.id

