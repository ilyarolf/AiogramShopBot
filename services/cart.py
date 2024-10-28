from typing import List

from sqlalchemy import select, update, delete
from sqlalchemy.orm import joinedload

from db import async_session_maker
from models.buyItem import BuyItem
from models.cart import Cart, CartItem
from models.category import Category
from models.shipment import Shipment
from models.subcategory import Subcategory


class CartService:

    @staticmethod
    async def get_or_create_cart(telegram_id: int) -> Cart:
        async with async_session_maker() as session:
            stmt = (select(Cart).join(
                CartItem, CartItem.cart_id == Cart.id, isouter=True).where(
                Cart.telegram_id == telegram_id, Cart.is_closed == 0).options(
                joinedload(Cart.cart_items)))
            cart = await session.execute(stmt)
            cart = cart.scalar()
            if cart is None:
                new_cart_obj = Cart(telegram_id=telegram_id, is_closed=False, shipment=0, cart_items=[])
                session.add(new_cart_obj)
                await session.commit()
                await session.refresh(new_cart_obj)
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
    async def remove_from_cart(cart_item_id: int, cart_id: int):
        async with async_session_maker() as session:
            stmt = delete(CartItem).where(CartItem.id == cart_item_id, CartItem.cart_id == cart_id)
            await session.execute(stmt)


    @staticmethod
    async def add_to_cart(cart_item: CartItem, cart: Cart):

        async with (async_session_maker() as session):
            # if there exists a cart with a cart_item with the same category and subcategory, increase the quantity
            # and if not, there is either no cart_item at all or no cart_item of the same (sub-)category
            get_old_cart_content_stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id, isouter=True).where(
                Cart.id == cart.id,
                CartItem.subcategory_id == cart_item.subcategory_id).options(
                joinedload(Cart.cart_items))
            old_cart_records = await session.execute(get_old_cart_content_stmt)
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
                await session.execute(quantity_update_stmt)
                session.refresh(cart)
                session.refresh(cart_item)
            await session.commit()


    @staticmethod
    async def create_cart_item(cart_item: CartItem) -> int:

        async with (async_session_maker() as session):
            category_name_stmt = select(Category.name).where(Category.id == cart_item.category_id)
            category_name = await session.execute(category_name_stmt)
            subcategory_name_stmt = select(Subcategory.name).where(Subcategory.id == cart_item.subcategory_id)
            subcategory_name = await session.execute(subcategory_name_stmt)
            cart_item.category_name = category_name
            cart_item.subcategory_name = subcategory_name
            session.add(cart_item)
            await session.commit()
            await session.refresh(cart_item)
            return cart_item.id


    @staticmethod
    async def get_all_cart_items(telegram_id: int) -> List[CartItem]:
        async with async_session_maker() as session:
            stmt = select(Cart).join(
                CartItem, Cart.id == CartItem.cart_id, isouter=True).where(
                Cart.telegram_id == telegram_id, Cart.is_closed == 0).options(
                joinedload(Cart.cart_items))
            cart_items = await session.execute(stmt)
            cart_items = cart_items.scalars().all()

        return cart_items

    @staticmethod
    async def get_all_cart_items_count(telegram_id: int) -> int:
        all_cart_items = await CartService.get_all_cart_items(telegram_id=telegram_id)
        return len(all_cart_items)
