import math
from typing import List

from requests import session
from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload

from db import async_session_maker
from models.cart import Cart, CartItem
from services.category import CategoryService


class CartService:

    @staticmethod
    async def get_or_create_cart(telegram_id: int) -> Cart:
        async with async_session_maker() as db_session:
            stmt = (select(Cart).join(
                CartItem, CartItem.cart_id == Cart.id, isouter=True).where(
                Cart.telegram_id == telegram_id, Cart.is_closed == 0).options(
                joinedload(Cart.cart_items)))
            cart = await db_session.execute(stmt)
            cart = cart.scalar()
            if cart is None:
                new_cart_obj = Cart(telegram_id=telegram_id, is_closed=False, shipment=0, cart_items=[])
                db_session.add(new_cart_obj)
                await db_session.commit()
                await db_session.refresh(new_cart_obj)
                return new_cart_obj
            else:
                return cart


    @staticmethod
    async def get_cart_by_primary_key(primary_key: int) -> Cart:
        async with async_session_maker() as session:
            stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id, isouter=True).where(
                Cart.id == primary_key).options(
                joinedload(Cart.cart_items))
            cart = await session.execute(stmt)
            return cart.scalar()


    @staticmethod
    async def get_open_cart_by_user(telegram_id: int) -> Cart:
        async with async_session_maker() as session:
            stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id, isouter=True).where(
                Cart.telegram_id == telegram_id, Cart.is_closed == 0).options(
                joinedload(Cart.cart_items))
            cart = await session.execute(stmt)
            return cart.scalar()


    @staticmethod
    async def get_all_cart_items(telegram_id: int) -> List[CartItem]:
       cart = await CartService.get_or_create_cart(telegram_id=telegram_id)
       return cart.cart_items


    @staticmethod
    async def remove_from_cart(cart_item_id: int):
        async with async_session_maker() as db_session:
            stmt = select(CartItem, CartItem==cart_item_id)
            cart_item = await db_session.execute(stmt)
            cart_item = cart_item.scalar()

            await db_session.delete(cart_item)
            await db_session.commit()


    @staticmethod
    async def add_to_cart(cart_item: CartItem, cart: Cart):

        async with (async_session_maker() as db_session):
            # if there exists a cart with a cart_item with the same category and subcategory, increase the quantity
            # and if not, there is either no cart_item in the cart at all or no cart_item of the same (sub-)category
            get_old_cart_content_stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id, isouter=True).where(
                Cart.id == cart.id,
                CartItem.subcategory_id == cart_item.subcategory_id).options(
                joinedload(Cart.cart_items))
            old_cart_records = await db_session.execute(get_old_cart_content_stmt)
            old_cart_records = old_cart_records.scalar()

            if old_cart_records is None:
                await CartService.create_cart_item(
                    cart_item=CartItem(
                           cart=cart
                         , cart_id=cart.id
                         , category_id=cart_item.category_id
                         , category_name=cart_item.category_name
                         , subcategory_id=cart_item.subcategory_id
                         , subcategory_name=cart_item.subcategory_name
                         , quantity=cart_item.quantity
                         , a_piece_price=cart_item.a_piece_price))
            elif old_cart_records is not None:
                quantity_update_stmt = (update(CartItem).where(CartItem.cart_id == cart.id)
                                        .values(quantity=CartItem.quantity + cart_item.quantity))
                await db_session.execute(quantity_update_stmt)
                db_session.refresh(cart)
                db_session.refresh(cart_item)
            await db_session.commit()


    @staticmethod
    async def create_cart_item(cart_item: CartItem) -> int:

        async with (async_session_maker() as session):
            session.add(cart_item)
            await session.commit()
            await session.refresh(cart_item)
            return cart_item.id


    @staticmethod
    async def get_all_cart_items_count(telegram_id: int) -> int:
        all_cart_items = await CartService.get_all_cart_items(telegram_id=telegram_id)
        return len(all_cart_items)


    @staticmethod
    async def get_maximum_page(telegram_id: int) -> int:
        max_page = await CartService.get_all_cart_items_count(telegram_id)
        if max_page % CategoryService.items_per_page == 0:
            return max_page / CategoryService.items_per_page - 1
        else:
            return math.trunc(max_page / CategoryService.items_per_page)


    @staticmethod
    async def get_cart_item_by_id(cart_item_id: int) -> CartItem:
        async with (async_session_maker() as session):
            stmnt = select(CartItem, CartItem.id==cart_item_id)
            cart_item = await session.execute(stmnt)
            return cart_item.scalar()


    @staticmethod
    async def close_cart(cart_id: int):
        async with (async_session_maker() as db_session):
            stmnt = update(Cart).where(Cart.id == cart_id).values(is_closed=True)
            await db_session.execute(stmnt)
