from aiogram.types import CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback, CartCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cart_action import CartAction
from enums.keyboardbutton import KeyboardButton
from handlers.common.common import add_pagination_buttons
from models.buy import BuyDTO
from models.buyItem import BuyItemDTO
from models.cartItem import CartItemDTO
from repositories.button_media import ButtonMediaRepository
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.cartItem import CartItemRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.media import MediaService
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
        current_cart_content = await CartItemRepository.get_current_cart_content(cart_item, cart, session)
        if current_cart_content:
            available_qty = await ItemRepository.get_available_qty(cart_item.category_id,
                                                                   cart_item.subcategory_id,
                                                                   session)
            current_cart_content.quantity = current_cart_content.quantity + cart_item.quantity
            if current_cart_content.quantity > available_qty:
                current_cart_content.quantity = available_qty
            await CartItemRepository.update(cart_item, session)
        else:
            await CartItemRepository.create(cart_item, session)
        await session_commit(session)
        caption = Localizator.get_text(BotEntity.USER, "item_added_to_cart")
        bot_photo_id = get_bot_photo_id()
        media = InputMediaPhoto(media=bot_photo_id, caption=caption)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=Localizator.get_text(BotEntity.USER, "cart"),
            callback_data=CartCallback.create(0)
        )
        kb_builder.row(callback_data.get_back_button(0))
        return media, kb_builder

    @staticmethod
    async def create_buttons(telegram_id: int,
                             callback_data: CartCallback | None,
                             session: AsyncSession) -> tuple[InputMediaPhoto |
                                                             InputMediaVideo |
                                                             InputMediaAnimation,
    InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(telegram_id, session)
        if callback_data is None:
            callback_data = CartCallback.create(0)
        cart_items = await CartItemRepository.get_by_user_id(user.id, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for cart_item in cart_items:
            item = await ItemRepository.get_single(cart_item.category_id, cart_item.subcategory_id, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                    subcategory_name=subcategory.name,
                    qty=cart_item.quantity,
                    total_price=cart_item.quantity * item.price,
                    currency_sym=Localizator.get_currency_symbol()
                ),
                callback_data=CartCallback.create(
                    level=callback_data.level + 1,
                    cart_item_id=cart_item.id,
                    page=callback_data.page)
            )
        if len(kb_builder.as_markup().inline_keyboard) > 0:
            cart = await CartRepository.get_or_create(user.id, session)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "checkout"),
                              callback_data=CartCallback.create(
                                  level=2,
                                  cart_id=cart.id,
                                  page=callback_data.page)
                              )
            kb_builder.adjust(1)
            kb_builder = await add_pagination_buttons(
                kb_builder,
                callback_data,
                CartItemRepository.get_maximum_page(user.id, session),
                None)
            caption = Localizator.get_text(BotEntity.USER, "cart")
        else:
            caption = Localizator.get_text(BotEntity.USER, "no_cart_items")

        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.CART, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def delete_cart_item(callback_data: CartCallback, session: AsyncSession | Session):
        kb_builder = InlineKeyboardBuilder()
        if callback_data.confirmation:
            await CartItemRepository.remove_from_cart(callback_data.cart_item_id, session)
            await session_commit(session)
            kb_builder.button(
                text=Localizator.get_text(BotEntity.USER, "cart"),
                callback_data=CartCallback.create(0)
            )
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation_text"), kb_builder
        else:
            cart_item_dto = await CartItemRepository.get_by_primary_key(callback_data.cart_item_id, session)
            category = await CategoryRepository.get_by_id(cart_item_dto.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item_dto.subcategory_id, session)
            item_dto = await ItemRepository.get_single(cart_item_dto.category_id, cart_item_dto.subcategory_id, session)
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                              callback_data=callback_data.model_copy(update={'confirmation': True}))
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                              callback_data=CartCallback.create(0))
            return Localizator.get_text(BotEntity.USER, "delete_cart_item_confirmation").format(
                category_name=category.name,
                subcategory_name=subcategory.name,
                price=item_dto.price,
                currency_sym=Localizator.get_currency_symbol(),
                description=item_dto.description,
            ), kb_builder

    @staticmethod
    async def checkout_processing(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[
        str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        message_text = Localizator.get_text(BotEntity.USER, "cart_confirm_checkout_process")
        cart_content = []
        cart_total_price = 0.0

        for cart_item in cart_items:
            item = await ItemRepository.get_single(category_id=cart_item.category_id,
                                                   subcategory_id=cart_item.subcategory_id,
                                                   session=session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            line_item_total = item.price * cart_item.quantity
            cart_content.append(
                Localizator.get_text(BotEntity.USER, "cart_item_button").format(
                    subcategory_name=subcategory.name,
                    qty=cart_item.quantity,
                    total_price=line_item_total,
                    currency_sym=Localizator.get_currency_symbol()
                ))
            cart_total_price += line_item_total
        message_text = message_text.format(
            cart_content="\n".join(cart_content),
            cart_total_price=cart_total_price,
            currency_sym=Localizator.get_currency_symbol()
        )
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=CartCallback.create(3,
                                                            confirmation=True))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=CartCallback.create(0))
        return message_text, kb_builder

    @staticmethod
    async def buy_processing(callback: CallbackQuery, session: AsyncSession | Session) -> tuple[
        str, InlineKeyboardBuilder]:
        unpacked_cb = CartCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        cart_total = 0.0
        out_of_stock = []
        for cart_item in cart_items:
            item = await ItemRepository.get_single(category_id=cart_item.category_id,
                                                   subcategory_id=cart_item.subcategory_id,
                                                   session=session)
            cart_total += item.price * cart_item.quantity
            is_in_stock = await ItemRepository.get_available_qty(category_id=cart_item.category_id,
                                                                 subcategory_id=cart_item.subcategory_id,
                                                                 session=session) >= cart_item.quantity
            if is_in_stock is False:
                out_of_stock.append(cart_item)
        is_enough_money = (user.top_up_amount - user.consume_records) >= cart_total
        kb_builder = InlineKeyboardBuilder()
        if unpacked_cb.confirmation and len(out_of_stock) == 0 and is_enough_money:
            sold_items = []
            msg = ""
            for cart_item in cart_items:
                item = await ItemRepository.get_single(category_id=cart_item.category_id,
                                                       subcategory_id=cart_item.subcategory_id,
                                                       session=session)
                purchased_items = await ItemRepository.get_purchased_items(cart_item.category_id,
                                                                           cart_item.subcategory_id, cart_item.quantity,
                                                                           session)
                buy_dto = BuyDTO(buyer_id=user.id, quantity=cart_item.quantity,
                                 total_price=cart_item.quantity * item.price)
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

    @staticmethod
    async def show_cart_item(callback_data: CartCallback, session: AsyncSession):
        cart_item_dto = await CartItemRepository.get_by_primary_key(callback_data.cart_item_id, session)
        available_qty = await ItemRepository.get_available_qty(cart_item_dto.category_id,
                                                               cart_item_dto.subcategory_id,
                                                               session)
        if callback_data.cart_action == CartAction.REMOVE_ALL or cart_item_dto.quantity == 0:
            return await CartService.delete_cart_item(callback_data, session)
        elif callback_data.cart_action in [CartAction.PLUS_ONE, CartAction.MINUS_ONE]:
            cart_item_dto.quantity += callback_data.cart_action.value
            if cart_item_dto.quantity > available_qty:
                cart_item_dto.quantity = available_qty
            elif cart_item_dto.quantity == 0:
                return await CartService.delete_cart_item(callback_data, session)
            await CartItemRepository.update(cart_item_dto, session)
            await session_commit(session)
        elif callback_data.cart_action == CartAction.MAX:
            cart_item_dto.quantity = available_qty
            await CartItemRepository.update(cart_item_dto, session)
            await session_commit(session)
        item_dto = await ItemRepository.get_single(cart_item_dto.category_id, cart_item_dto.subcategory_id, session)
        category = await CategoryRepository.get_by_id(cart_item_dto.category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(cart_item_dto.subcategory_id, session)
        cart_actions = [CartAction.REMOVE_ALL, CartAction.MINUS_ONE, CartAction.PLUS_ONE, CartAction.MAX]
        if cart_item_dto.quantity == available_qty:
            cart_actions.remove(CartAction.PLUS_ONE)
            cart_actions.remove(CartAction.MAX)
        kb_builder = InlineKeyboardBuilder()
        for cart_action in cart_actions:
            kb_builder.button(
                text=cart_action.get_localized(),
                callback_data=callback_data.model_copy(update={'cart_action': cart_action})
            )
        kb_builder.row(callback_data.get_back_button(0))
        return Localizator.get_text(BotEntity.USER, "cart_item_preview").format(
            category_name=category.name,
            subcategory_name=subcategory.name,
            price=item_dto.price,
            currency_sym=Localizator.get_currency_symbol(),
            description=item_dto.description,
            available_qty=available_qty,
            qty=cart_item_dto.quantity,
            total_price=cart_item_dto.quantity * item_dto.price
        ), kb_builder
