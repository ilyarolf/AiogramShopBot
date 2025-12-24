import traceback
from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import ErrorEvent, Message, BufferedInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
import config
from config import SUPPORT_LINK
import logging
from bot import dp, main, redis
from enums.bot_entity import BotEntity
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from handlers.common.review_management import review_management_router
from middleware.database import DBSessionMiddleware
from middleware.language import I18nMiddleware
from middleware.throttling_middleware import ThrottlingMiddleware
from models.user import UserDTO
from multibot import main as main_multibot
from handlers.user.cart import cart_router
from handlers.admin.admin import admin_router
from handlers.user.all_categories import all_categories_router
from handlers.user.my_profile import my_profile_router
from repositories.button_media import ButtonMediaRepository
from services.media import MediaService
from services.notification import NotificationService
from services.review import ReviewService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter, IsUserBannedFilter
from utils.utils import get_bot_photo_id, get_text

logging.basicConfig(level=logging.INFO)
main_router = Router()


@main_router.message(Command(commands=["start", "help"]))
async def start(message: Message, session: AsyncSession, language: Language):
    all_categories_button = types.KeyboardButton(text=get_text(language, BotEntity.USER, "all_categories"))
    my_profile_button = types.KeyboardButton(text=get_text(language, BotEntity.USER, "my_profile"))
    faq_button = types.KeyboardButton(text=get_text(language, BotEntity.USER, "faq"))
    help_button = types.KeyboardButton(text=get_text(language, BotEntity.USER, "help"))
    admin_menu_button = types.KeyboardButton(text=get_text(language, BotEntity.ADMIN, "menu"))
    reviews_button = types.KeyboardButton(text=get_text(language, BotEntity.USER, "reviews"))
    cart_button = types.KeyboardButton(text=get_text(language, BotEntity.USER, "cart"))
    telegram_id = message.from_user.id
    await UserService.create_if_not_exist(UserDTO(
        telegram_username=message.from_user.username,
        telegram_id=telegram_id,
        language=language
    ), session)
    keyboard = [[all_categories_button, my_profile_button], [faq_button, help_button],
                [reviews_button],
                [cart_button]]
    if telegram_id in config.ADMIN_ID_LIST:
        keyboard.append([admin_menu_button])
    start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, keyboard=keyboard)
    bot_photo_id = get_bot_photo_id()
    await message.answer_photo(photo=bot_photo_id,
                               caption=get_text(language, BotEntity.COMMON, "start_message"),
                               reply_markup=start_markup)


@main_router.message(F.text.in_(KeyboardButton.get_localized_set(KeyboardButton.FAQ)), IsUserExistFilter())
async def faq(message: Message, session: AsyncSession, language: Language):
    button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.FAQ, session)
    media = MediaService.convert_to_media(button_media.media_id,
                                          caption=get_text(language, BotEntity.USER, "faq_string"))
    await NotificationService.answer_media(message, media)


@main_router.message(F.text.in_(KeyboardButton.get_localized_set(KeyboardButton.HELP)), IsUserExistFilter())
async def support(message: Message, session: AsyncSession, language: Language):
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text=get_text(language, BotEntity.USER, "help_button"), url=SUPPORT_LINK)
    button_media = await ButtonMediaRepository.get_by_button(KeyboardButton.HELP, session)
    media = MediaService.convert_to_media(button_media.media_id,
                                          caption=get_text(language, BotEntity.USER, "help_string"))
    await NotificationService.answer_media(message, media)


@main_router.message(F.text.in_(KeyboardButton.get_localized_set(KeyboardButton.REVIEWS)), IsUserExistFilter())
async def support(message: Message, session: AsyncSession, language: Language):
    media, kb_builder = await ReviewService.get_reviews_paginated(None, session, language)
    await NotificationService.answer_media(message, media, reply_markup=kb_builder.as_markup())


@main_router.error(F.update.message.as_("message"))
async def error_handler(event: ErrorEvent, message: Message):
    await message.answer("Oops, something went wrong!")
    traceback_str = traceback.format_exc()
    admin_notification = (
        f"Critical error caused by {event.exception}\n\n"
        f"Stack trace:\n{traceback_str}"
    )
    if len(admin_notification) > 4096:
        byte_array = bytearray(admin_notification, 'utf-8')
        admin_notification = BufferedInputFile(byte_array, "exception.txt")
    await NotificationService.send_to_admins(admin_notification, None)


throttling_middleware = ThrottlingMiddleware(redis)
users_routers = Router()
users_routers.include_routers(
    all_categories_router,
    my_profile_router,
    cart_router,
    review_management_router
)
users_routers.message.middleware(throttling_middleware)
users_routers.callback_query.middleware(throttling_middleware)
main_router.include_router(admin_router)
main_router.include_routers(users_routers)
main_router.message.middleware(DBSessionMiddleware())
main_router.callback_query.middleware(DBSessionMiddleware())
main_router.message.middleware(I18nMiddleware())
main_router.callback_query.middleware(I18nMiddleware())


@main_router.message(IsUserBannedFilter())
async def banned_message(message: Message, language: Language):
    await message.answer(text=get_text(language, BotEntity.COMMON, "banned"))


@main_router.callback_query(IsUserBannedFilter())
async def banned_message(callback: CallbackQuery, language: Language):
    banned_text = get_text(language, BotEntity.COMMON, "banned")
    if callback.message.text:
        await callback.message.edit_text(banned_text)
    else:
        await callback.message.delete()
        await callback.message.answer(banned_text)


if __name__ == '__main__':
    if config.MULTIBOT:
        main_multibot(main_router)
    else:
        dp.include_router(main_router)
        main()
