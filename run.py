from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import dp, main
from config import SUPPORT_LINK
import logging

from handlers.admin.admin import admin_router
from handlers.user.all_categories import all_categories_router
from handlers.user.my_profile import my_profile_router
from services.user import UserService
from utils.custom_filters import IsUserExistFilter

logging.basicConfig(level=logging.INFO)


@dp.message(Command(commands=["start", "help"]))
async def start(message: types.message):
    all_categories_button = types.KeyboardButton(text='🔍 All categories')
    my_profile_button = types.KeyboardButton(text='🎓 My profile')
    faq_button = types.KeyboardButton(text='🤝 FAQ')
    help_button = types.KeyboardButton(text='🚀 Help')
    keyboard = [[all_categories_button, my_profile_button], [faq_button, help_button]]
    start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, keyboard=keyboard)
    user_telegram_id = message.chat.id
    user_telegram_username = message.from_user.username
    is_exist = await UserService.is_exist(user_telegram_id)
    if is_exist is False:
        await UserService.create(user_telegram_id, user_telegram_username)
    else:
        await UserService.update_username(user_telegram_id, user_telegram_username)
    await message.answer('Hi', reply_markup=start_markup)


@dp.message(F.text == '🤝 FAQ', IsUserExistFilter())
async def faq(message: types.message):
    faq_string = """<b>In our store ignorance of the rules does not exempt you from responsibility. Buying at least 
one product in the store you automatically agree with all the rules of the store!\n
Rules of the store</b>\n
❗1.In case of inadequate/offensive behavior the seller has the right to refuse the service!
❗2.A replacement is provided only if the product is invalid.
❗3.Replacement is provided only if there is a video proof.
❗4.30 minutes warranty period.
❗5.The administration is not responsible for any unlawful actions performed by the buyer with the items purchased in the
store.
❗6.These terms and conditions may change at any time.
❗7.Money cannot be withdrawn from your balance."""
    await message.answer(faq_string, parse_mode='html')


@dp.message(F.text == '🚀 Help', IsUserExistFilter())
async def support(message: types.message):
    admin_keyboard_builder = InlineKeyboardBuilder()

    admin_keyboard_builder.button(text='Admin', url=SUPPORT_LINK)
    await message.answer(f'<b>Support</b>', reply_markup=admin_keyboard_builder.as_markup())


main_router = Router()
main_router.include_router(admin_router)
main_router.include_router(my_profile_router)
main_router.include_router(all_categories_router)
dp.include_router(main_router)

if __name__ == '__main__':
    main()
