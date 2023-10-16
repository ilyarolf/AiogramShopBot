from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import ADMIN_ID_LIST, TOKEN, WEBHOOK_URL, WEBAPP_HOST, WEBAPP_PORT, SUPPORT_LINK
from handlers.admin.admin import admin_command_handler, admin_menu_navigation, admin_callback, AdminStates, \
    get_message_to_sending, receive_new_items_file
from handlers.user.all_categories import navigate_categories, all_categories_cb, all_categories_text_message
from handlers.user.my_profile import navigate, my_profile_cb, my_profile_text_message
from models.user import db, User
from file_requests import FileRequests
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging
from aiogram.utils.executor import start_webhook

from utils.admin_filter import AdminIdFilter

logging.basicConfig(level=logging.INFO)
FileRequests = FileRequests()

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    for admin in ADMIN_ID_LIST:
        try:
            await bot.send_message(admin, 'Bot is working')
        except:
            pass


async def on_shutdown(dp):
    logging.warning('Shutting down..')
    db.close()
    # insert code here to run it before shutdown

    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

    logging.warning('Bye!')


@dp.message_handler(commands=['start', 'help'])
async def start(message: types.message):
    all_categories_button = types.KeyboardButton('🔍 All categories')
    my_profile_button = types.KeyboardButton('🎓 My profile')
    faq_button = types.KeyboardButton('🤝 FAQ')
    help_button = types.KeyboardButton('🚀 Help')
    start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    start_markup.add(all_categories_button, my_profile_button, faq_button, help_button)
    user_telegram_id = message.chat.id
    user_telegram_username = message.from_user.username
    user = User(user_telegram_id, user_telegram_username)
    if User.is_exist(message.chat.id) is False:
        user.create()
    else:
        telegram_username = User.get_by_tgid(user_telegram_id)["telegram_username"]
        if telegram_username != user_telegram_username:
            User.update_username(user_telegram_id, user_telegram_username)
    await message.answer('Hi', reply_markup=start_markup)

@dp.message_handler(text='🤝 FAQ')
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


@dp.message_handler(text='🚀 Help')
async def support(message: types.message):
    admin_markup = types.InlineKeyboardMarkup()
    admin_button = types.InlineKeyboardButton('Admin', url=SUPPORT_LINK)
    admin_markup.add(admin_button)
    await message.answer(f'<b>Support</b>', parse_mode='html', reply_markup=admin_markup)


dp.register_callback_query_handler(navigate, my_profile_cb.filter())
dp.register_message_handler(my_profile_text_message, text="🎓 My profile")

dp.register_callback_query_handler(navigate_categories, all_categories_cb.filter())
dp.register_message_handler(all_categories_text_message, text="🔍 All categories")

dp.register_callback_query_handler(admin_menu_navigation, admin_callback.filter())
dp.register_message_handler(admin_command_handler, AdminIdFilter("/admin"))

dp.register_message_handler(get_message_to_sending, state=AdminStates.message_to_send,
                            content_types=types.ContentTypes.all())

dp.register_message_handler(receive_new_items_file, state=AdminStates.new_items_file,
                            content_types=types.ContentTypes.DOCUMENT | types.ContentTypes.TEXT)

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path="",
        on_startup=on_startup,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
