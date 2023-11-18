from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SUPPORT_LINK
import logging

from handlers.admin.admin import admin_router
from handlers.user.all_categories import all_categories_router
from handlers.user.my_profile import my_profile_router
from services.user import UserService
from utils.custom_filters import IsUserExistFilter

logging.basicConfig(level=logging.INFO)
main_router = Router()


@main_router.message(Command(commands=["start", "help"]))
async def start(message: types.message):
    all_categories_button = types.KeyboardButton(text='📁 Categories')
    my_profile_button = types.KeyboardButton(text='👤 Profile')
    faq_button = types.KeyboardButton(text='ℹ️ Info')
    help_button = types.KeyboardButton(text='🆘 Support')
    keyboard = [[all_categories_button, my_profile_button], [faq_button, help_button]]
    start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, keyboard=keyboard)
    user_telegram_id = message.chat.id
    user_telegram_username = message.from_user.username
    is_exist = await UserService.is_exist(user_telegram_id)
    if is_exist is False:
        await UserService.create(user_telegram_id, user_telegram_username)
    else:
        await UserService.update_username(user_telegram_id, user_telegram_username)
    await message.answer('<b>Hi this is a demo of a bot for automating sales. One of the advantages of this bot is that it uses cryptocurrency as payment for goods. Contact admin if you want to buy the source code of this bot, or buy the bot turnkey.</b>', reply_markup=start_markup)


@main_router.message(F.text == 'ℹ️ Info', IsUserExistFilter())
async def faq(message: types.message):
    faq_string = """<b>Here you can post any information that may be useful to users of your bot.

For example</b>:
-Rule#1
-Rule#2
-Rule#3
-Rule#4
-Rule#5"""
    await message.answer(faq_string, parse_mode='html')


@main_router.message(F.text == '🆘 Support', IsUserExistFilter())
async def support(message: types.message):
    admin_keyboard_builder = InlineKeyboardBuilder()

    admin_keyboard_builder.button(text='Admin', url=SUPPORT_LINK)
    await message.answer(f'<b>Support</b>', reply_markup=admin_keyboard_builder.as_markup())


main_router.include_router(admin_router)
main_router.include_router(my_profile_router)
main_router.include_router(all_categories_router)
# dp.include_router(main_router)

# if __name__ == '__main__':
#     main()
