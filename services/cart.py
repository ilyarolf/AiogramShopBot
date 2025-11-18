from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback, CartCallback
from db import session_commit
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from models.buy import BuyDTO
from models.buyItem import BuyItemDTO
from models.cartItem import CartItemDTO
from models.item import ItemDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.cartItem import CartItemRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from utils.localizator import Localizator
from utils.utils import get_bot_photo_id


class CartService:

    @staticmethod
    async def add_to_cart(callback: CallbackQuery,
                          callback_data: AllCategoriesCallback,
                          session: AsyncSession) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart = await CartRepository.get_or_create(user.id, session)
        cart_item = CartItemDTO(
            category_id=callback_data.category_id,
            subcategory_id=callback_data.subcategory_id,
            quantity=callback_data.quantity,
            cart_id=cart.id
        )
        await CartRepository.add_to_cart(cart_item, cart, session)
        await session_commit(session)
        caption = Localizator.get_text(BotEntity.USER, "item_added_to_cart")
        bot_photo_id = get_bot_photo_id()
        media = InputMediaPhoto(media=bot_photo_id, caption=caption)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(callback_data.get_back_button(0))
        return media, kb_builder


    @staticmethod
    async def create_buttons(message: Message | CallbackQuery, session: AsyncSession | Session):
        user = await UserRepository.get_by_tgid(message.from_user.id, session)
        page = 0 if isinstance(message, Message) else CartCallback.unpack(message.data).page
        cart_items = await CartItemRepository.get_by_user_id(user.id, 0, session)
        kb_builder = InlineKeyboardBuilder()
        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                subcategory_name=subcategory.name,
                qty=cart_item.quantity,
                total_price=cart_item.quantity * price,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=CartCallback.create(1, page, cart_item_id=cart_item.id))
        if len(kb_builder.as_markup().inline_keyboard) > 0:
            cart = await CartRepository.get_or_create(user.id, session)
            unpacked_cb = CartCallback.create(0) if isinstance(message, Message) else CartCallback.unpack(message.data)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "checkout"),
                              callback_data=CartCallback.create(2, page, cart.id))
            kb_builder.adjust(1)
            kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                      CartItemRepository.get_maximum_page(user.id, session),
                                                      None)
            return Localizator.get_text(BotEntity.USER, "cart"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "no_cart_items"), kb_builder

    @staticmethod
    async def delete_cart_item(callback: CallbackQuery, session: AsyncSession | Session):
        unpacked_cb = CartCallback.unpack(callback.data)
        cart_item_id = unpacked_cb.cart_item_id
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation:
            await CartItemRepository.remove_from_cart(cart_item_id, session)
            await session_commit(session)
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation_text"), kb_builder
        else:
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                              callback_data=CartCallback.create(1, cart_item_id=cart_item_id,
                                                                confirmation=True))
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                              callback_data=CartCallback.create(0))
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation"), kb_builder

    @staticmethod
    async def __create_checkout_msg(cart_items: list[CartItemDTO], session: AsyncSession | Session) -> str:
        message_text = Localizator.get_text(BotEntity.USER, "cart_confirm_checkout_process")
        message_text += "<b>\n\n"
        cart_grand_total = 0.0

        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
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
    async def checkout_processing(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        message_text = await CartService.__create_checkout_msg(cart_items, session)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=CartCallback.create(3,
                                                            confirmation=True))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=CartCallback.create(0))
        return message_text, kb_builder

    @staticmethod
    async def buy_processing(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = CartCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        cart_total = 0.0
        out_of_stock = []
        for cart_item in cart_items:
            item_dto = ItemDTO(category_id=cart_item.category_id, subcategory_id=cart_item.subcategory_id)
            price = await ItemRepository.get_price(item_dto, session)
            cart_total += price * cart_item.quantity
            is_in_stock = await ItemRepository.get_available_qty(item_dto, session) >= cart_item.quantity
            if is_in_stock is False:
                out_of_stock.append(cart_item)
        is_enough_money = (user.top_up_amount - user.consume_records) >= cart_total
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation and len(out_of_stock) == 0 and is_enough_money:
            sold_items = []
            msg = ""
            for cart_item in cart_items:
                price = await ItemRepository.get_price(ItemDTO(category_id=cart_item.category_id,
                                                               subcategory_id=cart_item.subcategory_id), session)
                purchased_items = await ItemRepository.get_purchased_items(cart_item.category_id,
                                                                           cart_item.subcategory_id, cart_item.quantity, session)
                buy_dto = BuyDTO(buyer_id=user.id, quantity=cart_item.quantity, total_price=cart_item.quantity * price)
                buy_id = await BuyRepository.create(buy_dto, session)
                buy_item_dto_list = [BuyItemDTO(item_id=item.id, buy_id=buy_id) for item in purchased_items]
                await BuyItemRepository.create_many(buy_item_dto_list, session)
                for item in purchased_items:
                    item.is_sold = True
                await ItemRepository.update(purchased_items, session)
                await CartItemRepository.remove_from_cart(cart_item.id, session)
                sold_items.append(cart_item)
                msg += MessageService.create_message_with_bought_items(purchased_items)
            user.consume_records = user.consume_records + cart_total
            await UserRepository.update(user, session)
            await session_commit(session)
            await NotificationService.new_buy(sold_items, user, session)
            return msg, kb_builder
        elif unpacked_cb.confirmation is False:
            kb_builder.row(unpacked_cb.get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "purchase_confirmation_declined"), kb_builder
        elif is_enough_money is False:
            kb_builder.row(unpacked_cb.get_back_button(0))
            return Localizator.get_text(BotEntity.USER, "insufficient_funds"), kb_builder
        elif len(out_of_stock) > 0:
            kb_builder.row(unpacked_cb.get_back_button(0))
            msg = Localizator.get_text(BotEntity.USER, "out_of_stock")
            for item in out_of_stock:
                subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
                msg += subcategory.name + "\n"
            return msg, kb_builder
