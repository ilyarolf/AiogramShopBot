import math
from sqlalchemy import select, update
import config
from callbacks import AllCategoriesCallback
from db import get_db_session, session_execute, session_commit, session_refresh
from models.cart import Cart
from models.cartItem import CartItem, CartItemDTO
from models.user import UserDTO
from repositories.cart import CartRepository
from repositories.user import UserRepository


# from services.cartItem import CartItemService
# from services.user import UserService


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
    async def add_to_cart(unpacked_cb: AllCategoriesCallback, telegram_id: int):
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=telegram_id))
        cart = await CartRepository.get_or_create(user.id)
        cart_item = CartItemDTO(
            category_id=unpacked_cb.category_id,
            subcategory_id=unpacked_cb.subcategory_id,
            quantity=unpacked_cb.quantity,
            cart_id=cart.id
        )
        await CartRepository.add_to_cart(cart_item, cart)
