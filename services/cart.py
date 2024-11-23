import math

from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update
import config
from callbacks import AllCategoriesCallback, CartCallback
from db import get_db_session, session_execute, session_commit, session_refresh
from handlers.common.common import add_pagination_buttons
from models.cart import Cart
from models.cartItem import CartItem, CartItemDTO
from models.user import UserDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.cartItem import CartItemRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from utils.localizator import Localizator, BotEntity


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
    async def add_to_cart(callback: CallbackQuery):
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=callback.from_user.id))
        cart = await CartRepository.get_or_create(user.id)
        cart_item = CartItemDTO(
            category_id=unpacked_cb.category_id,
            subcategory_id=unpacked_cb.subcategory_id,
            quantity=unpacked_cb.quantity,
            cart_id=cart.id
        )
        await CartRepository.add_to_cart(cart_item, cart)

    @staticmethod
    async def create_buttons(message: Message | CallbackQuery):
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=message.from_user.id))
        page = 0 if isinstance(message, Message) else CartCallback.unpack(message.data).page
        cart_items = await CartItemRepository.get_by_user_id(user.id, 0)
        kb_builder = InlineKeyboardBuilder()
        for cart_item in cart_items:
            price = await ItemRepository.get_price(cart_item.category_id, cart_item.subcategory_id)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                subcategory_name=subcategory.name,
                qty=cart_item.quantity,
                total_price=cart_item.quantity * price,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=CartCallback.create(1, page, cart_item_id=cart_item.id))
        if len(kb_builder.as_markup().inline_keyboard) > 0:
            cart = await CartRepository.get_or_create(user.id)
            unpacked_cb = CartCallback.create(0) if isinstance(message, Message) else CartCallback.unpack(message.data)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "checkout"),
                              callback_data=CartCallback.create(2, page, cart.id))
            kb_builder.adjust(1)
            kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                      CartItemRepository.get_maximum_page(user.id),
                                                      None)
            return Localizator.get_text(BotEntity.USER, "cart"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "no_cart_items"), kb_builder

    @staticmethod
    async def delete_cart_item(callback: CallbackQuery):
        unpacked_cb = CartCallback.unpack(callback.data)
        cart_item_id = unpacked_cb.cart_item_id
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.delete_cart_item_confirmation:
            await CartItemRepository.remove_from_cart(cart_item_id)
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation_text"), kb_builder
        else:
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                              callback_data=CartCallback.create(1, cart_item_id=cart_item_id,
                                                                delete_cart_item_confirmation=True))
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                              callback_data=CartCallback.create(0))
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation"), kb_builder

    @staticmethod
    async def __create_checkout_msg(cart_items: list[CartItemDTO]) -> str:
        message_text = Localizator.get_text(BotEntity.USER, "cart_confirm_checkout_process")
        message_text += "<b>\n\n"
        cart_grand_total = 0.0

        for cart_item in cart_items:
            price = await ItemRepository.get_price(cart_item.category_id, cart_item.subcategory_id)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id)
            line_item_total = price * cart_item.quantity
            cart_line_item = Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                subcategory_name=subcategory.name, qty=cart_item.quantity,
                total_price=line_item_total, currency_sym=Localizator.get_currency_symbol()
            )
            cart_grand_total += line_item_total
            message_text += cart_line_item
        message_text += Localizator.get_text(BotEntity.USER, "cart_grand_total_string").format(
            cart_grand_total=cart_grand_total, currency_sym=Localizator.get_currency_symbol())
        message_text += "</b>"
        return message_text

    @staticmethod
    async def checkout_processing(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=callback.from_user.id))
        cart_items = await CartItemRepository.get_all_by_user_id(user.id)
        message_text = await CartService.__create_checkout_msg(cart_items)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=CartCallback.create(3,
                                                            purchase_confirmation=True))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=CartCallback.create(0))
        return message_text, kb_builder

    @staticmethod
    async def buy_processing(callback: CallbackQuery):
        unpacked_cb = CartCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=callback.from_user.id))
        cart_items = await CartItemRepository.get_all_by_user_id(user.id)
        cart_total = 0.0
        out_of_stock = []
        for cart_item in cart_items:
            price = await ItemRepository.get_price(cart_item.category_id, cart_item.subcategory_id)
            cart_total += price * cart_item.quantity
            is_in_stock = await ItemRepository.get_available_qty(cart_item.category_id,
                                                                 cart_item.category_id) >= cart_item.quantity
            if is_in_stock is False:
                out_of_stock.append(cart_item)
        is_enough_money = (user.top_up_amount - user.consume_records) >= cart_total
        if unpacked_cb.purchase_confirmation and len(out_of_stock) == 0:
            for cart_item in cart_items:
                price = await ItemRepository.get_price(cart_item.category_id, cart_item.subcategory_id)
                purchased_items = await ItemRepository.get_purchased_items(cart_item.category_id,
                                                                           cart_item.subcategory_id, cart_item.quantity)
                total_price = cart_item.quantity * price
                # TODO (use DTO)
                buy_id = await BuyRepository.create(user.id, cart_item.quantity, total_price)
                await BuyItemRepository.create_many(purchased_items, buy_id)
                for item in purchased_items:
                    item.is_sold = True
                await ItemRepository.update(purchased_items)
        elif unpacked_cb.purchase_confirmation is False:
            pass
        elif is_enough_money is False:
            pass
        elif len(out_of_stock) > 0:
            pass
