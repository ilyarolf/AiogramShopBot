from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaAnimation, Message, \
    InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import AllCategoriesCallback, CartCallback, MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cart_action import CartAction
from enums.coupon_type import CouponType
from enums.item_type import ItemType
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from handlers.common.common import add_pagination_buttons
from handlers.user.constants import UserStates
from models.buy import BuyDTO
from models.buyItem import BuyItemDTO
from models.cartItem import CartItemDTO
from repositories.button_media import ButtonMediaRepository
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.cartItem import CartItemRepository
from repositories.category import CategoryRepository
from repositories.coupon import CouponRepository
from repositories.item import ItemRepository
from repositories.shipping_option import ShippingOptionRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.media import MediaService
from services.notification import NotificationService
from utils.utils import get_text
from utils.utils import get_bot_photo_id


class CartService:

    @staticmethod
    async def add_to_cart(callback: CallbackQuery,
                          callback_data: AllCategoriesCallback,
                          session: AsyncSession,
                          language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart = await CartRepository.get_or_create(user.id, session)
        cart_item = CartItemDTO(
            item_type=callback_data.item_type,
            category_id=callback_data.category_id,
            subcategory_id=callback_data.subcategory_id,
            quantity=callback_data.quantity,
            cart_id=cart.id
        )
        current_cart_content = await CartItemRepository.get_current_cart_content(cart_item, cart, session)
        if current_cart_content:
            available_qty = await ItemRepository.get_available_qty(callback_data.item_type,
                                                                   cart_item.category_id,
                                                                   cart_item.subcategory_id,
                                                                   session)
            current_cart_content.quantity = current_cart_content.quantity + cart_item.quantity
            if current_cart_content.quantity > available_qty:
                current_cart_content.quantity = available_qty
            await CartItemRepository.update(cart_item, session)
        else:
            await CartItemRepository.create(cart_item, session)
        await session_commit(session)
        caption = get_text(language, BotEntity.USER, "item_added_to_cart")
        bot_photo_id = get_bot_photo_id()
        media = InputMediaPhoto(media=bot_photo_id, caption=caption)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.USER, "cart"),
            callback_data=CartCallback.create(0)
        )
        kb_builder.row(callback_data.get_back_button(language, 0))
        return media, kb_builder

    @staticmethod
    async def create_buttons(telegram_id: int,
                             callback_data: CartCallback | None,
                             session: AsyncSession,
                             language: Language) -> tuple[InputMediaPhoto |
                                                          InputMediaVideo |
                                                          InputMediaAnimation,
    InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(telegram_id, session)
        if callback_data is None:
            callback_data = CartCallback.create(0)
        cart_items = await CartItemRepository.get_by_user_id(user.id, callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for cart_item in cart_items:
            item = await ItemRepository.get_single(cart_item.item_type,
                                                   cart_item.category_id,
                                                   cart_item.subcategory_id,
                                                   session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
            kb_builder.button(
                text=get_text(language, BotEntity.USER, "cart_item_button").format(
                    subcategory_name=subcategory.name,
                    qty=cart_item.quantity,
                    total_price=cart_item.quantity * item.price,
                    currency_sym=config.CURRENCY.get_localized_symbol()
                ),
                callback_data=CartCallback.create(
                    level=callback_data.level + 1,
                    cart_item_id=cart_item.id,
                    page=callback_data.page)
            )
        if len(kb_builder.as_markup().inline_keyboard) > 0:
            cart = await CartRepository.get_or_create(user.id, session)
            kb_builder.button(text=get_text(language, BotEntity.USER, "checkout"),
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
                None,
                language)
            caption = get_text(language, BotEntity.USER, "cart")
        else:
            caption = get_text(language, BotEntity.USER, "no_cart_items")

        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.CART, session)
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def delete_cart_item(callback_data: CartCallback,
                               session: AsyncSession | Session,
                               language: Language):
        kb_builder = InlineKeyboardBuilder()
        if callback_data.confirmation:
            await CartItemRepository.remove_from_cart(callback_data.cart_item_id, session)
            await session_commit(session)
            kb_builder.button(
                text=get_text(language, BotEntity.USER, "cart"),
                callback_data=CartCallback.create(0)
            )
            return get_text(language, BotEntity.USER, "delete_cart_item_confirmation_text"), kb_builder
        else:
            cart_item_dto = await CartItemRepository.get_by_primary_key(callback_data.cart_item_id, session)
            category = await CategoryRepository.get_by_id(cart_item_dto.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(cart_item_dto.subcategory_id, session)
            item_dto = await ItemRepository.get_single(cart_item_dto.item_type,
                                                       cart_item_dto.category_id,
                                                       cart_item_dto.subcategory_id,
                                                       session)
            kb_builder.button(text=get_text(language, BotEntity.COMMON, "confirm"),
                              callback_data=callback_data.model_copy(update={'confirmation': True}))
            kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                              callback_data=CartCallback.create(0))
            return get_text(language, BotEntity.USER, "delete_cart_item_confirmation").format(
                category_name=category.name,
                subcategory_name=subcategory.name,
                price=item_dto.price,
                currency_sym=config.CURRENCY.get_localized_symbol(),
                description=item_dto.description,
            ), kb_builder

    @staticmethod
    async def checkout_processing(callback: CallbackQuery,
                                  callback_data: CartCallback,
                                  state: FSMContext,
                                  session: AsyncSession | Session,
                                  language: Language) -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        cart_items_dict = {}
        for cart_item in cart_items:
            if cart_items_dict.get(cart_item.item_type) is None:
                cart_items_dict[cart_item.item_type] = [cart_item]
            else:
                cart_items_list = cart_items_dict.get(cart_item.item_type)
                cart_items_list.append(cart_item)
                cart_items_dict[cart_item.item_type] = cart_items_list
        cart_content = []
        state_data = await state.get_data()
        if callback_data.shipping_option_id:
            shipping_option = await ShippingOptionRepository.get_by_id(callback_data.shipping_option_id, session)
            cart_total_price = shipping_option.price
        else:
            shipping_option_id = state_data.get("shipping_option_id")
            cart_total_price = 0.0
            if shipping_option_id:
                callback_data.shipping_option_id = shipping_option_id
                shipping_option = await ShippingOptionRepository.get_by_id(shipping_option_id, session)
                cart_total_price += shipping_option.price
            else:
                shipping_option = None
        for item_type, cart_items in cart_items_dict.items():
            cart_content.append(item_type.get_localized(language))
            for cart_item in cart_items:
                item = await ItemRepository.get_single(item_type=cart_item.item_type,
                                                       category_id=cart_item.category_id,
                                                       subcategory_id=cart_item.subcategory_id,
                                                       session=session)
                subcategory = await SubcategoryRepository.get_by_id(cart_item.subcategory_id, session)
                line_item_total = item.price * cart_item.quantity
                cart_content.append(
                    get_text(language, BotEntity.USER, "cart_item_button").format(
                        subcategory_name=subcategory.name,
                        qty=cart_item.quantity,
                        total_price=line_item_total,
                        currency_sym=config.CURRENCY.get_localized_symbol()
                    ))
                cart_total_price += line_item_total
        coupon_id = state_data.get('coupon_id')
        shipping_address = state_data.get("shipping_address")
        has_physical = cart_items_dict.get(ItemType.PHYSICAL) is not None
        sym = config.CURRENCY.get_localized_symbol()
        if coupon_id is not None:
            cart_total_price_before_discount = cart_total_price
            coupon_dto = await CouponRepository.get_by_id(coupon_id, session)
            if coupon_dto.type == CouponType.PERCENTAGE:
                cart_total_price = ((100 - coupon_dto.value) / 100) * cart_total_price
            else:
                cart_total_price = cart_total_price - coupon_dto.value
                cart_total_price = max(cart_total_price, 1)
            discount_amount = cart_total_price_before_discount - cart_total_price
            cart_content.append(f"\n{get_text(language, BotEntity.USER, "cart_total_price").format(
                cart_total_price=cart_total_price_before_discount,
                currency_sym=sym
            )}")
            cart_content.append(get_text(language, BotEntity.USER, "cart_total_discount").format(
                cart_total_discount=discount_amount,
                currency_sym=sym,
            ))
            cart_content.append(get_text(language, BotEntity.USER, "cart_total_with_discount").format(
                cart_total_final=cart_total_price,
                currency_sym=sym
            ))
        else:
            cart_content.append(f"\n{get_text(language, BotEntity.USER, "cart_total_price").format(
                cart_total_price=cart_total_price,
                currency_sym=sym
            )}")
        if shipping_option:
            cart_content.append(f"\n{get_text(language, BotEntity.USER, "shipping_details").format(
                shipping_option_name=shipping_option.name,
                shipping_address=shipping_address
            )}")
        cart_content.append(get_text(language, BotEntity.USER, "checkout_cart"))
        confirm_text = get_text(language, BotEntity.COMMON, "confirm")
        if has_physical is False or (
                has_physical is True and shipping_address is not None and shipping_option is not None):
            confirm_button = InlineKeyboardButton(text=confirm_text,
                                                  callback_data=CartCallback.create(
                                                      level=6,
                                                      shipping_option_id=callback_data.shipping_option_id,
                                                      confirmation=True).pack())
        else:
            confirm_button = InlineKeyboardButton(text=confirm_text,
                                                  callback_data=CartCallback.create(level=4).pack())
        kb_builder = InlineKeyboardBuilder()
        kb_builder.add(confirm_button)
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                          callback_data=CartCallback.create(level=0))
        if coupon_id is None:
            kb_builder.row(InlineKeyboardButton(
                text=get_text(language, BotEntity.COMMON, "coupon"),
                callback_data=CartCallback.create(level=3,
                                                  shipping_option_id=callback_data.shipping_option_id).pack()
            ))
        message_text = f"<b>{"\n".join(cart_content)}</b>"
        return message_text, kb_builder

    @staticmethod
    async def buy_processing(callback: CallbackQuery,
                             callback_data: CartCallback,
                             state: FSMContext,
                             session: AsyncSession | Session,
                             language: Language) -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        cart_items = await CartItemRepository.get_all_by_user_id(user.id, session)
        if callback_data.shipping_option_id:
            shipping_option = await ShippingOptionRepository.get_by_id(callback_data.shipping_option_id, session)
            cart_total_price = shipping_option.price
        else:
            shipping_option = None
            cart_total_price = 0.0
        out_of_stock = []
        for cart_item in cart_items:
            item = await ItemRepository.get_single(item_type=cart_item.item_type,
                                                   category_id=cart_item.category_id,
                                                   subcategory_id=cart_item.subcategory_id,
                                                   session=session)
            cart_total_price += item.price * cart_item.quantity
            is_in_stock = await ItemRepository.get_available_qty(item_type=cart_item.item_type,
                                                                 category_id=cart_item.category_id,
                                                                 subcategory_id=cart_item.subcategory_id,
                                                                 session=session) >= cart_item.quantity
            if is_in_stock is False:
                out_of_stock.append(cart_item)
        total_discount_amount = 0
        state_data = await state.get_data()
        coupon_id = state_data.get('coupon_id')
        if coupon_id is not None:
            cart_total_price_before_discount = cart_total_price
            coupon_dto = await CouponRepository.get_by_id(coupon_id, session)
            if coupon_dto.usage_limit == 1:
                coupon_dto.is_active = False
                coupon_dto.usage_count += 1
                await CouponRepository.update(coupon_dto, session)
            if coupon_dto.type == CouponType.PERCENTAGE:
                cart_total_price = ((100 - coupon_dto.value) / 100) * cart_total_price
            else:
                cart_total_price = cart_total_price - coupon_dto.value
                cart_total_price = max(cart_total_price, 1)
            total_discount_amount = cart_total_price_before_discount - cart_total_price
        is_enough_money = (user.top_up_amount - user.consume_records) >= cart_total_price
        kb_builder = InlineKeyboardBuilder()
        if callback_data.confirmation and len(out_of_stock) == 0 and is_enough_money:
            msg = get_text(language, BotEntity.USER, "purchase_completed")
            buy_dto = BuyDTO(buyer_id=user.id,
                             total_price=cart_total_price,
                             discount=total_discount_amount,
                             coupon_id=coupon_id,
                             shipping_address=state_data.get('shipping_address'),
                             shipping_option_id=shipping_option.id if shipping_option else None)
            buy_dto = await BuyRepository.create(buy_dto, session)
            for cart_item in cart_items:
                purchased_items = await ItemRepository.get_purchased_items(cart_item.category_id,
                                                                           cart_item.subcategory_id, cart_item.quantity,
                                                                           session)
                item_ids = [item.id for item in purchased_items]
                buy_item_dto = BuyItemDTO(buy_id=buy_dto.id, item_ids=item_ids)
                await BuyItemRepository.create_single(buy_item_dto, session)
                for item in purchased_items:
                    item.is_sold = True
                await ItemRepository.update(purchased_items, session)
                await CartItemRepository.remove_from_cart(cart_item.id, session)
            kb_builder.button(
                text=get_text(language, BotEntity.USER, "purchase_history_item").format(
                    buy_id=buy_dto.id,
                    total_price=buy_dto.total_price,
                    currency_sym=config.CURRENCY.get_localized_symbol()
                ),
                callback_data=MyProfileCallback.create(level=4,
                                                       buy_id=buy_dto.id)
            )
            user.consume_records = user.consume_records + cart_total_price
            await UserRepository.update(user, session)
            await session_commit(session)
            await NotificationService.new_buy(buy_dto, user, session)
            return msg, kb_builder
        elif callback_data.confirmation is False:
            kb_builder.row(callback_data.get_back_button(language, 0))
            return get_text(language, BotEntity.USER, "purchase_confirmation_declined"), kb_builder
        elif is_enough_money is False:
            kb_builder.row(callback_data.get_back_button(language, 0))
            return get_text(language, BotEntity.USER, "insufficient_funds"), kb_builder
        elif len(out_of_stock) > 0:
            kb_builder.row(callback_data.get_back_button(language, 0))
            msg = get_text(language, BotEntity.USER, "out_of_stock")
            for item in out_of_stock:
                subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
                msg += subcategory.name + "\n"
            return msg, kb_builder

    @staticmethod
    async def show_cart_item(callback_data: CartCallback,
                             session: AsyncSession,
                             language: Language):
        cart_item_dto = await CartItemRepository.get_by_primary_key(callback_data.cart_item_id, session)
        available_qty = await ItemRepository.get_available_qty(cart_item_dto.item_type,
                                                               cart_item_dto.category_id,
                                                               cart_item_dto.subcategory_id,
                                                               session)
        if callback_data.cart_action == CartAction.REMOVE_ALL or cart_item_dto.quantity == 0:
            return await CartService.delete_cart_item(callback_data, session, language)
        elif callback_data.cart_action in [CartAction.PLUS_ONE, CartAction.MINUS_ONE]:
            cart_item_dto.quantity += callback_data.cart_action.value
            if cart_item_dto.quantity > available_qty:
                cart_item_dto.quantity = available_qty
            elif cart_item_dto.quantity == 0:
                return await CartService.delete_cart_item(callback_data, session, language)
            await CartItemRepository.update(cart_item_dto, session)
            await session_commit(session)
        elif callback_data.cart_action == CartAction.MAX:
            cart_item_dto.quantity = available_qty
            await CartItemRepository.update(cart_item_dto, session)
            await session_commit(session)
        item_dto = await ItemRepository.get_single(cart_item_dto.item_type,
                                                   cart_item_dto.category_id,
                                                   cart_item_dto.subcategory_id,
                                                   session)
        category = await CategoryRepository.get_by_id(cart_item_dto.category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(cart_item_dto.subcategory_id, session)
        cart_actions = [CartAction.REMOVE_ALL, CartAction.MINUS_ONE, CartAction.PLUS_ONE, CartAction.MAX]
        if cart_item_dto.quantity == available_qty:
            cart_actions.remove(CartAction.PLUS_ONE)
            cart_actions.remove(CartAction.MAX)
        kb_builder = InlineKeyboardBuilder()
        for cart_action in cart_actions:
            kb_builder.button(
                text=cart_action.get_localized(language),
                callback_data=callback_data.model_copy(update={'cart_action': cart_action})
            )
        kb_builder.row(callback_data.get_back_button(language, 0))
        return get_text(language, BotEntity.USER, "cart_item_preview").format(
            item_type=item_dto.item_type.get_localized(language),
            category_name=category.name,
            subcategory_name=subcategory.name,
            price=item_dto.price,
            currency_sym=config.CURRENCY.get_localized_symbol(),
            description=item_dto.description,
            available_qty=available_qty,
            qty=cart_item_dto.quantity,
            total_price=cart_item_dto.quantity * item_dto.price
        ), kb_builder

    @staticmethod
    async def set_coupon(callback_data: CartCallback, state: FSMContext, language: Language):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "pagination_next"),
            callback_data=CartCallback.create(2, shipping_option_id=callback_data.shipping_option_id)
        )
        kb_builder.adjust(1)
        await state.set_state(UserStates.coupon)
        await state.update_data(shipping_option_id=callback_data.shipping_option_id)
        return get_text(language, BotEntity.USER, "request_coupon"), kb_builder

    @staticmethod
    async def receive_purchase_details(message: Message,
                                       state: FSMContext,
                                       session: AsyncSession,
                                       language: Language) -> tuple[
        InputMediaPhoto | InputMediaVideo | InputMediaVideo, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        current_state = await state.get_state()
        await state.set_state()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.CART, session)
        media = MediaService.convert_to_media(button_media.media_id, caption="")
        if current_state == UserStates.coupon:
            kb_builder = InlineKeyboardBuilder()
            coupon_dto = await CouponRepository.get_by_code(message.text, session)
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "pagination_next"),
                callback_data=CartCallback.create(level=2,
                                                  shipping_option_id=state_data.get(""))
            )
            if coupon_dto is None:
                caption = get_text(language, BotEntity.USER, "coupon_not_found")
            else:
                await state.update_data(coupon_id=coupon_dto.id)
                caption = get_text(language, BotEntity.USER, "coupon_applied")
        else:
            await state.update_data(shipping_address=message.html_text)
            caption, kb_builder = await CartService.get_shipping_options_paginated(0, session, language)
        media.caption = caption
        return media, kb_builder

    @staticmethod
    async def set_shipping_address(state: FSMContext, language: Language):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=CartCallback.create(0)
        )
        kb_builder.adjust(1)
        await state.set_state(UserStates.shipping_address)
        return get_text(language, BotEntity.USER, "request_shipping_address"), kb_builder

    @staticmethod
    async def get_shipping_options_paginated(page: int,
                                             session: AsyncSession,
                                             language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        shipping_options = await ShippingOptionRepository.get_paginated(page, False, session)
        for shipping_option in shipping_options:
            kb_builder.button(
                text=get_text(language, BotEntity.USER, "ship_via_button").format(
                    shipping_option_name=shipping_option.name,
                    currency_sym=config.CURRENCY.get_localized_symbol(),
                    shipping_option_price=shipping_option.price
                ),
                callback_data=CartCallback.create(level=2,
                                                  shipping_option_id=shipping_option.id)
            )
        kb_builder.adjust(1)
        cart_callback = CartCallback.create(level=5, page=page)
        kb_builder = await add_pagination_buttons(kb_builder,
                                                  cart_callback,
                                                  ShippingOptionRepository.get_max_page(False, session),
                                                  cart_callback.get_back_button(language, 2),
                                                  language)
        msg = get_text(language, BotEntity.USER, "pick_shipping_option")
        return msg, kb_builder
