import datetime
import re
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message, InputMediaPhoto, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import MyProfileCallback, ReviewManagementCallback
from enums.bot_entity import BotEntity
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from enums.user_role import UserRole
from handlers.admin.constants import AdminConstants
from handlers.common.common import add_pagination_buttons
from handlers.user.constants import UserStates
from models.review import ReviewDTO
from repositories.button_media import ButtonMediaRepository
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.review import ReviewRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.media import MediaService
from services.notification import NotificationService
from utils.utils import get_text, get_bot_photo_id


class ReviewService:
    @staticmethod
    async def get_rating_picker(callback_data: ReviewManagementCallback,
                                language: Language) -> [str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        for i in range(5, 0, -1):
            kb_builder.button(
                text="⭐️" * i,
                callback_data=callback_data.model_copy(update={"level": callback_data.level + 1,
                                                               "rating": i})
            )
        kb_builder.adjust(1)
        back_button = InlineKeyboardButton(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=MyProfileCallback.create(level=5,
                                                   buy_id=callback_data.buy_id,
                                                   buyItem_id=callback_data.buyItem_id,
                                                   language=language).pack()
        )
        kb_builder.row(back_button)
        return get_text(language, BotEntity.USER, "select_rating"), kb_builder

    @staticmethod
    async def set_review_next_state(callback_data: ReviewManagementCallback,
                                    state: FSMContext,
                                    next_state: State,
                                    language: Language) -> tuple[str, InlineKeyboardBuilder]:
        await state.set_state(next_state)
        await state.update_data(buy_id=callback_data.buy_id,
                                buyItem_id=callback_data.buyItem_id,
                                rating=callback_data.rating)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "pagination_next"),
            callback_data=callback_data.model_copy(update={"level": callback_data.level + 1})
        )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=MyProfileCallback.create(level=5,
                                                   buy_id=callback_data.buy_id,
                                                   buyItem_id=callback_data.buyItem_id,
                                                   language=language)
        )
        kb_builder.adjust(1)
        if next_state == UserStates.review_text:
            localizator_key = "review_text_request"
        else:
            localizator_key = "review_image_request"
        return get_text(language, BotEntity.USER, localizator_key), kb_builder

    @staticmethod
    def is_review_text_safe(text: str) -> bool:
        url_pattern = re.compile(r'https?://\S+|www\.\S+')
        telegram_username_pattern = re.compile(r'@\w+')
        if url_pattern.search(text) or telegram_username_pattern.search(text):
            return False
        return True

    @staticmethod
    async def process_review_message(message: Message,
                                     state: FSMContext,
                                     session: AsyncSession,
                                     language: Language) -> tuple[str | InputMediaPhoto, InlineKeyboardBuilder]:
        current_state = await state.get_state()
        state_data = await state.get_data()
        kb_builder = InlineKeyboardBuilder()
        await NotificationService.edit_reply_markup(message.bot,
                                                    state_data['chat_id'],
                                                    state_data['msg_id'])
        rating = state_data['rating']
        buy_id = state_data['buy_id']
        buyItem_id = state_data['buyItem_id']
        base_callback = ReviewManagementCallback.create(level=0,
                                                        rating=rating,
                                                        buy_id=buy_id,
                                                        buyItem_id=buyItem_id)
        if message.text and current_state == UserStates.review_text:
            if not ReviewService.is_review_text_safe(message.html_text) or len(message.html_text) > 512:
                msg_text = get_text(language, BotEntity.USER, "review_text_is_not_safe")
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "pagination_next"),
                    callback_data=base_callback.model_copy(update={"level": 3})
                )
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "back_button"),
                    callback_data=base_callback.model_copy(update={"level": 1})
                )
                return msg_text, kb_builder

            await state.set_state(UserStates.review_image)
            await state.update_data(review_text=message.html_text)
            msg_text = get_text(language, BotEntity.USER, "review_image_request")
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "pagination_next"),
                callback_data=base_callback.model_copy(update={"level": 4})
            )
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "back_button"),
                callback_data=base_callback.model_copy(update={"level": 2})
            )

        elif message.photo and current_state == UserStates.review_image:
            await message.delete()
            photo_id = message.photo[-1].file_id
            await state.clear()
            await state.update_data(**state_data, photo_id=photo_id)

            buyitem_dto = await BuyItemRepository.get_by_id(buyItem_id, session)
            item_dto = await ItemRepository.get_by_id(buyitem_dto.item_ids[0], session)
            category = await CategoryRepository.get_by_id(item_dto.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item_dto.subcategory_id, session)

            review_text = state_data.get("review_text") or get_text(language,
                                                                    BotEntity.USER, "review_text_is_not_provided")

            caption = get_text(language, BotEntity.COMMON, "review").format(
                item_type=item_dto.item_type.get_localized(language),
                category_name=category.name,
                subcategory_name=subcategory.name,
                currency_sym=config.CURRENCY.get_localized_symbol(),
                price=item_dto.price,
                rating_stars="⭐️" * rating,
                review_text=review_text
            )

            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "confirm"),
                callback_data=base_callback.model_copy(update={"level": 4, "confirmation": True})
            )
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "cancel"),
                callback_data=MyProfileCallback.create(0)
            )
            msg_text = InputMediaPhoto(media=photo_id, caption=caption)

        else:
            if current_state == UserStates.review_text:
                msg_text = get_text(language, BotEntity.USER, "review_text_request")
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "pagination_next"),
                    callback_data=base_callback.model_copy(update={"level": 3})
                )
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "back_button"),
                    callback_data=base_callback.model_copy(update={"level": 1})
                )
            else:
                msg_text = get_text(language, BotEntity.USER, "review_image_request")
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "pagination_next"),
                    callback_data=base_callback.model_copy(update={"level": 4})
                )
                kb_builder.button(
                    text=get_text(language, BotEntity.COMMON, "back_button"),
                    callback_data=base_callback.model_copy(update={"level": 2})
                )
        kb_builder.adjust(1)
        return msg_text, kb_builder

    @staticmethod
    async def review_confirmation(callback_data: ReviewManagementCallback,
                                  state: FSMContext,
                                  session: AsyncSession,
                                  language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        buyItem_dto = await BuyItemRepository.get_by_id(callback_data.buyItem_id, session)
        item_dto = await ItemRepository.get_by_id(buyItem_dto.item_ids[0], session)
        category = await CategoryRepository.get_by_id(item_dto.category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(item_dto.category_id, session)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "confirm"),
            callback_data=callback_data.model_copy(update={"confirmation": True})
        )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=MyProfileCallback.create(level=5,
                                                   buy_id=callback_data.buy_id,
                                                   buyItem_id=callback_data.buyItem_id,
                                                   language=language)
        )
        review_text = state_data.get("review_text") or get_text(language, BotEntity.USER,
                                                                "review_text_is_not_provided")
        caption = (get_text(language, BotEntity.COMMON, "review")
                   .format(item_type=item_dto.item_type.get_localized(language),
                           category_name=category.name,
                           subcategory_name=subcategory.name,
                           currency_sym=config.CURRENCY.get_localized_symbol(),
                           price=item_dto.price,
                           rating_stars=callback_data.rating * "⭐️",
                           review_text=review_text
                           ))
        photo_id = state_data.get("photo_id") or get_bot_photo_id()
        media = InputMediaPhoto(media=photo_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def create_review(callback_data: ReviewManagementCallback,
                            state: FSMContext,
                            session: AsyncSession,
                            language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        await state.clear()
        review_dto = await ReviewRepository.get_by_buy_item_id(callback_data.review_id, session)
        if review_dto is None:
            review_dto = ReviewDTO(
                buyItem_id=callback_data.buyItem_id,
                rating=callback_data.rating,
                text=state_data.get("review_text"),
                image_id=state_data.get("photo_id")
            )
            review_dto = await ReviewRepository.create(review_dto, session)
            await session.commit()
        await NotificationService.new_review_published(review_dto, session)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=MyProfileCallback.create(level=5,
                                                   buy_id=callback_data.buy_id,
                                                   buyItem_id=callback_data.buyItem_id,
                                                   language=language)
        )
        caption = get_text(language, BotEntity.USER, "review_successfully_published")
        media = get_bot_photo_id()
        media = InputMediaPhoto(media=media, caption=caption)
        return media, kb_builder

    @staticmethod
    async def get_reviews_paginated(callback_data: ReviewManagementCallback | None,
                                    session: AsyncSession,
                                    language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        callback_data = callback_data or ReviewManagementCallback.create(level=5)
        reviews = await ReviewRepository.get_reviews_paginated(callback_data.page, session)
        kb_builder = InlineKeyboardBuilder()
        for review in reviews:
            buyItem_dto = await BuyItemRepository.get_by_id(review.buyItem_id, session)
            item_dto = await ItemRepository.get_by_id(buyItem_dto.item_ids[0], session)
            subcategory_dto = await SubcategoryRepository.get_by_id(item_dto.subcategory_id, session)
            kb_builder.button(
                text=get_text(language, BotEntity.USER, "review_button").format(
                    subcategory_name=subcategory_dto.name,
                    price=len(buyItem_dto.item_ids) * item_dto.price,
                    currency_sym=config.CURRENCY.get_localized_symbol()
                ),
                callback_data=callback_data.model_copy(update={
                    "level": callback_data.level + 1,
                    "review_id": review.id,
                    "buy_id": buyItem_dto.buy_id,
                    "buyItem_id": review.buyItem_id,
                    "page": callback_data.page
                })
            )
        kb_builder.adjust(1)
        back_button = None
        if callback_data.user_role == UserRole.ADMIN:
            back_button = AdminConstants.back_to_main_button(language)
        kb_builder = await add_pagination_buttons(kb_builder,
                                                  callback_data,
                                                  ReviewRepository.get_max_page(session),
                                                  back_button,
                                                  language)
        button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.REVIEWS, session)
        caption = get_text(language, BotEntity.USER, "reviews")
        media = MediaService.convert_to_media(button_media.media_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def view_review_single(callback_data: ReviewManagementCallback,
                                 session: AsyncSession,
                                 language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        review = await ReviewRepository.get_by_id(callback_data.review_id, session)
        buyItem_dto = await BuyItemRepository.get_by_id(review.buyItem_id, session)
        item_dto = await ItemRepository.get_by_id(buyItem_dto.item_ids[0], session)
        category_dto = await CategoryRepository.get_by_id(item_dto.category_id, session)
        subcategory_dto = await SubcategoryRepository.get_by_id(item_dto.subcategory_id, session)
        kb_builder = InlineKeyboardBuilder()
        review_text = review.text or get_text(language, BotEntity.USER, "review_text_is_not_provided")
        msg_text = (get_text(language, BotEntity.COMMON, "review")
                    .format(item_type=item_dto.item_type.get_localized(language),
                            category_name=category_dto.name,
                            subcategory_name=subcategory_dto.name,
                            currency_sym=config.CURRENCY.get_localized_symbol(),
                            price=len(buyItem_dto.item_ids) * item_dto.price,
                            rating_stars=review.rating * "⭐️",
                            review_text=review_text
                            ))
        if callback_data.user_role == UserRole.ADMIN:
            kb_builder.button(
                text=get_text(language, BotEntity.ADMIN, "remove_review_text"),
                callback_data=callback_data.model_copy(update={"level": callback_data.level + 1,
                                                               "confirmation": False})
            )
            kb_builder.button(
                text=get_text(language, BotEntity.ADMIN, "remove_review_image"),
                callback_data=callback_data.model_copy(update={"level": callback_data.level + 2,
                                                               "confirmation": False})
            )
            buy_dto = await BuyRepository.get_by_id(buyItem_dto.buy_id, session)
            user_dto = await UserRepository.get_user_entity(buy_dto.buyer_id, session)
            kb_builder.button(
                text=get_text(language, BotEntity.COMMON, "user"),
                url=f"tg://user?id={user_dto.telegram_id}"
            )
        kb_builder.adjust(1)
        back_button = InlineKeyboardButton(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=callback_data.model_copy(update={"level": callback_data.level - 1,
                                                           "page": callback_data.page}).pack()
        )
        kb_builder.row(back_button)
        media = review.image_id or get_bot_photo_id()
        return InputMediaPhoto(media=media, caption=msg_text), kb_builder

    @staticmethod
    async def remove_review_details_confirmation(callback_data: ReviewManagementCallback,
                                                 session: AsyncSession,
                                                 language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "confirm"),
            callback_data=callback_data.model_copy(update={"confirmation": True})
        )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=callback_data.model_copy(update={"level": 6})
        )
        kb_builder.adjust(1)
        review_field_key = "remove_review_text_confirmation" if callback_data.level == 7 else "remove_review_image_confirmation"
        caption = get_text(language, BotEntity.ADMIN, review_field_key)
        review_dto = await ReviewRepository.get_by_id(callback_data.review_id, session)
        media = review_dto.image_id or get_bot_photo_id()
        return InputMediaPhoto(media=media, caption=caption), kb_builder

    @staticmethod
    async def remove_review_details(callback: CallbackQuery,
                                    callback_data: ReviewManagementCallback,
                                    session: AsyncSession,
                                    language: Language):
        is_admin = callback.from_user.id in config.ADMIN_ID_LIST
        review_field = "text" if callback_data.level == 7 else "image_id"
        if callback_data.user_role == UserRole.ADMIN and is_admin:
            review_dto = await ReviewRepository.get_by_id(callback_data.review_id, session)
            review_dto.__setattr__(review_field, None)
            await ReviewRepository.update(review_dto, session)
            await session.commit()
            callback_data.level = 6
            return await ReviewService.view_review_single(callback_data, session, language)
