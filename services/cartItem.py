# import math
# from typing import List
#
# from sqlalchemy import select, delete
#
# import config
# from db import get_db_session, session_execute, session_commit
# from models.cart import Cart
# from models.cartItem import CartItem
# # from services.user import UserService
#
#
# class CartItemService:
#
#     @staticmethod
#     async def get_cart_items_by_user_id(user_id: int, page: int) -> List[CartItem]:
#         async with get_db_session() as session:
#             stmt = select(CartItem).join(Cart, CartItem.cart_id == Cart.id).where(Cart.user_id == user_id).limit(
#                 config.PAGE_ENTRIES).offset(config.PAGE_ENTRIES * page)
#             cart_items = await session_execute(stmt, session)
#             return cart_items.scalars().all()
#
#     @staticmethod
#     async def remove_from_cart(cart_item_id: int):
#         async with get_db_session() as session:
#             stmt = delete(CartItem).where(CartItem.id == cart_item_id)
#             await session_execute(stmt, session)
#             await session_commit(session)
#
#     @staticmethod
#     async def get_all_cart_items_by_cart_id(cart_id: int) -> List[CartItem]:
#         async with get_db_session() as session:
#             stmt = select(CartItem).join(Cart, CartItem.cart_id == Cart.id).where(Cart.id == cart_id)
#             cart_items = await session_execute(stmt, session)
#             return cart_items.scalars().all()
#
#     @staticmethod
#     async def get_maximum_page(telegram_id: int) -> int:
#         user = await UserService.get_by_tgid(telegram_id)
#         max_page = len(await CartItemService.get_all_items_by_user_id(user.id))
#         if max_page % config.PAGE_ENTRIES == 0:
#             return max_page / config.PAGE_ENTRIES - 1
#         else:
#             return math.trunc(max_page / config.PAGE_ENTRIES)
#
#     @staticmethod
#     async def get_all_items_by_user_id(user_id: int):
#         async with get_db_session() as session:
#             stmt = select(CartItem).join(Cart, CartItem.cart_id == Cart.id).where(Cart.user_id == user_id)
#             cart_items = await session_execute(stmt, session)
#             return cart_items.scalars().all()
