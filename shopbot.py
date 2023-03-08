from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from re import split
from db_requests import RequestToDB
from web_requests import WebRequest
from file_requests import FileRequests
from datetime import date
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging
from aiogram.utils.executor import start_webhook
from os import getenv, remove

# webhook settings
WEBHOOK_HOST = f"{getenv('WEBHOOK_HOST')}"
WEBHOOK_PATH = ''
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = 'localhost'  # or ip
WEBAPP_PORT = 5000

logging.basicConfig(level=logging.INFO)

RequestToDB = RequestToDB('items.db')
WebRequest = WebRequest()
FileRequests = FileRequests()
token = f"{getenv('TOKEN')}"
admin_id = int(getenv('ADMIN_ID'))
bot = Bot(token)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())


async def on_startup(dp):
    # Функция отправляет сообщение админу при запуске
    await bot.set_webhook(WEBHOOK_URL)
    await bot.send_message(admin_id, 'Bot is working')


async def on_shutdown(dp):
    # Функция закрывает бд, удаляет вебхук
    logging.warning('Shutting down..')
    RequestToDB.close()
    # insert code here to run it before shutdown

    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

    logging.warning('Bye!')


class AdminMessage(StatesGroup):
    # Класс нужен для получения состояний админских сообщений в админ панели
    admin_message = State()
    restocking = State()
    category_to_delete = State()
    subcategory_to_delete = State()


@dp.message_handler(commands='admin')
async def admin_menu(message: types.message):
    if message.chat.id == admin_id:
        # -Функция рассылки сообщения по всем юзерам
        # -Функция добавления товара в базу данных
        # -Функция получения новых пользователей
        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        send_to_all_users_button = types.InlineKeyboardButton('Разослать всем',
                                                              callback_data='admin_send_to_all')
        restocking_button = types.InlineKeyboardButton('Пополнение товара',
                                                       callback_data='admin_restocking')
        get_new_users_button = types.InlineKeyboardButton('Получить новых пользователей',
                                                          callback_data='admin_get_new_users')
        delete_category_button = types.InlineKeyboardButton('Удалить категорию',
                                                            callback_data='delete_category')
        delete_subcategory_button = types.InlineKeyboardButton('Удалить подкатегорию',
                                                               callback_data='delete_subcategory')
        admin_markup.add(send_to_all_users_button, restocking_button, get_new_users_button,
                         delete_category_button, delete_subcategory_button)
        await message.answer('Admin menu', reply_markup=admin_markup)


@dp.message_handler(content_types=['text'], state=AdminMessage.admin_message)
async def get_admin_message(message: types.message, state: FSMContext):
    """
    Функция рассылки сообщения по всем пользователям в БД
    """
    async with state.proxy():
        admin_message = message.text
        await state.finish()
        users = RequestToDB.get_all_users()
        for user_id in users:
            try:
                await bot.send_message(user_id[0], admin_message)
            except:
                pass
        await message.answer(f'Разослано\n<code>{admin_message}</code>', parse_mode='html')


@dp.message_handler(content_types=['text'], state=AdminMessage.category_to_delete)
async def delete_category(message: types.message, state: FSMContext):
    """
    Функция для удаления категории товара из БД
    """
    async with state.proxy():
        data_to_delete = message.text
        RequestToDB.delete_category(data_to_delete)
        await state.finish()
        await message.answer(f'<b>Успешно!</b>', parse_mode='html')


@dp.message_handler(content_types=['text'], state=AdminMessage.subcategory_to_delete)
async def delete_subcategory(message: types.message, state: FSMContext):
    """
    Функция для удаления подкатегории товара из БД
    """
    async with state.proxy():
        data_to_delete = message.text
        RequestToDB.delete_subcategory(data_to_delete)
        await state.finish()
        await message.answer(f'<b>Успешно!</b>', parse_mode='html')


async def send_restocking_message(quantity, category, subcategory):
    """
    Функция для отправления сообщения о новом поступлении товара
    """
    users = RequestToDB.get_all_users()
    update_data = date.today()
    for user_id in users:
        try:
            await bot.send_message(user_id[0], f"<b>Update {update_data}\n"
                                               f"Category {category}\n"
                                               f"Subcategory {subcategory}, {quantity} pcs</b>", parse_mode='html')
        except:
            pass


@dp.message_handler(content_types=['document'], state=AdminMessage.restocking)
async def get_restocking(message: types.message, state: FSMContext):
    """
    Функция для добавления нового товара включает:
    1) Подфункцию для получения файла с товаром из диалога с админом
    2) Распарсинг .json файла с списком товара, категорией, подкатегорией, прайсом, описанием
    3) Подфункцию для отправки сообщения по пользователям о новом поступлении
    """
    async with state.proxy():
        document_id = message.document.file_id
        file_info = await bot.get_file(document_id)
        filename = file_info.file_path.split('/')[1]
        url = f'https://api.telegram.org/file/bot{token}/{file_info.file_path}'
        await WebRequest.get_admin_file(url, filename)
        try:
            restocking_list, category, subcategory, price, description = FileRequests.get_new_items(filename)
            RequestToDB.insert_restocking(restocking_list, category, subcategory, price, description)
            await state.finish()
            await send_restocking_message(len(restocking_list), category, subcategory)
            await message.answer('Done')
        except Exception:
            remove(filename)
            await state.finish()
            await message.answer('Error')


async def consume_and_send_data(telegram_id, total_price, quantity, subcategory):
    """
    1) Получает баланс пользователя в USD и проверяет может ли он что-то купить
    1.1) Проверяет выбранное пользователем количество товара и количество товаров в наличии
    2) Обновляет данные о балансе пользователя (Парсит с API криптобирж и получает текущий баланс в USD)
    3) Обновляет данные о тратах пользователя и заносит в БД
    4) Формирует строку с купленным товаром
    4.1) Помечает товары как купленные в БД
    4.2) Отправляет пользователю покупку
    5) Создаёт запись в БД о покупке пользователя.
    """
    if RequestToDB.get_balance_in_usd_from_db(telegram_id) - int(total_price) >= 0 \
            and RequestToDB.get_quantity_in_stock(subcategory) >= int(quantity):
        balances = await WebRequest.parse_balances(telegram_id)
        await WebRequest.refresh_balance_in_usd(balances, telegram_id)
        RequestToDB.update_consume_records(telegram_id=telegram_id, total_price=total_price)
        private_data_list = ''
        for i in range(int(quantity)):
            try:
                data = RequestToDB.get_unsold_data(subcategory)
                item_id = data[1]
                private_data = data[0]
                private_data_list += f'{private_data}_end'
                RequestToDB.set_item_sold(item_id)
                await bot.send_message(chat_id=telegram_id, text=private_data)
            except Exception:
                await bot.send_message(chat_id=telegram_id, text='Error')
        RequestToDB.insert_new_buy(telegram_id, subcategory, quantity, total_price, private_data_list)
    elif RequestToDB.get_quantity_in_stock(subcategory) <= int(quantity):
        await bot.send_message(telegram_id, 'Out of stock!')
    else:
        await bot.send_message(telegram_id, 'Insufficient funds!')


@dp.message_handler(commands=['start', 'help'])
async def start(message: types.message):
    """
    Функция создаёт кнопки для взаимодействия с ботом
    1) Если пользователя нет в базе данных то,
    вызывает функцию добавления нового пользователя с добавлением btc,ltc,trx адресов.
    2) Если у пользователя есть username, то добавляет его в поле с его id. (Username- опциональное поле)
    """
    all_categories_button = types.KeyboardButton('🔍 All categories')
    my_profile_button = types.KeyboardButton('🎓 My profile')
    faq_button = types.KeyboardButton('🤝 FAQ')
    help_button = types.KeyboardButton('🚀 Help')
    start_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    start_markup.add(all_categories_button, my_profile_button, faq_button, help_button)
    if RequestToDB.is_exist(message.chat.id) == 0:
        RequestToDB.insert_new_user(message.chat.id, message.from_user.username)
    if message.from_user.username:
        RequestToDB.update_username(message.from_user.username, message.chat.id)
    await message.answer('Hi', reply_markup=start_markup)


@dp.message_handler(text='🔍 All categories')
async def all_categories(message: types.message):
    """Функция получает все категории из БД, и создаёт инлайн кнопки с категориями, если их нет то пишет 'Empty'"""
    categories = RequestToDB.get_categories()
    if categories:
        all_categories_markup = types.InlineKeyboardMarkup(row_width=2)
        for category in categories:
            category_button = types.InlineKeyboardButton(category[0], callback_data=f'show_{category[0]}')
            all_categories_markup.insert(category_button)
        await message.answer('🔍 <b>All categories</b>', parse_mode='html', reply_markup=all_categories_markup)
    else:
        await message.answer('Empty')


@dp.message_handler(text='🤝 FAQ')
async def faq(message: types.message):
    """Функция с правилами, отправляет сообщение с правилами"""
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
    """
    Функция отправляет инлайн кнопку на чат с админом
    """
    admin_link = getenv('ADMIN_LINK')
    admin_markup = types.InlineKeyboardMarkup()
    admin_button = types.InlineKeyboardButton('Admin', url=admin_link)
    admin_markup.add(admin_button)
    await message.answer(f'<b>Support</b>', parse_mode='html', reply_markup=admin_markup)


@dp.message_handler(text='🎓 My profile')
async def my_profile(message: types.message):
    """
    Функция отправляет сообщение пользователю с данными его профиля, балансы выгружаются из БД
    """
    balances = await RequestToDB.get_wallets_balances_from_db(message.chat.id)
    top_up_button = types.InlineKeyboardButton('Top Up balance', callback_data='top_up_balance')
    purchase_history = types.InlineKeyboardButton('Purchase history', callback_data='purchase_history')
    update_balance = types.InlineKeyboardButton('Refresh balance', callback_data='refresh_balance')
    my_profile_markup = types.InlineKeyboardMarkup(row_width=2)
    my_profile_markup.add(top_up_button, purchase_history, update_balance)
    balance_usd = RequestToDB.get_balance_in_usd_from_db(message.chat.id)
    await message.answer(f'<b>Your profile\nID:</b> <code>{message.chat.id}</code>\n\n'
                         f'<b>Your BTC balance:</b>\n<code>{balances[0]}</code>\n'
                         f'<b>Your USDT balance:</b>\n<code>{balances[1]}</code>\n'
                         f'<b>Your LTC balance:</b>\n<code>{balances[2]}</code>\n'
                         f"<b>Your balance in USD:</b>\n{format(balance_usd, '.2f')}$",
                         parse_mode="HTML", reply_markup=my_profile_markup)


@dp.callback_query_handler()
async def buy_buttons_inline(callback: types.callback_query):
    """Обрабатывает нажатия инлайн кнопок"""
    if 'show_' in callback.data:
        """
        Выгружает подкатегории из БД и создаёт инлайн кнопки с подкатегориями, ценой и их наличием
        """
        item = (split('_', callback.data)[1])
        subcategory = RequestToDB.get_data(item)
        subcategory = list(dict.fromkeys(subcategory))
        subcategory_markup = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton('🔙 Back', callback_data='back_to_all_categories')
        for i in range(len(subcategory)):
            subcategory_button = types.InlineKeyboardButton(
                f'{subcategory[i][0]} |'
                f' Price : {RequestToDB.get_price(subcategory[i][0])}$ |'
                f' Quantity : {RequestToDB.get_quantity_in_stock(subcategory[i][0])}',
                callback_data=f'choose_{item}_{subcategory[i][0]}')
            subcategory_markup.add(subcategory_button)
        subcategory_markup.add(back_button)
        await callback.answer()
        await callback.message.edit_text('<b>Subcategories</b>', parse_mode='html', reply_markup=subcategory_markup)
    elif 'choose_' in callback.data:
        """
        Функционал выбора количества товара
        Создаёт инлайн клавиатуру с кнопками от 1 до 10
        """
        subcategory = (split('_', callback.data)[1])
        item_of_buy = (split('_', callback.data)[2])
        price = RequestToDB.get_price(item_of_buy)
        description = RequestToDB.get_description(item_of_buy)
        count_markup = types.InlineKeyboardMarkup()
        back_button = types.InlineKeyboardButton('🔙 Back', parse_mode='html', callback_data=f'show_{subcategory}')
        for i in range(10):
            count_button = types.InlineKeyboardButton(f'{i + 1}',
                                                      callback_data=f'buy_{subcategory}_{item_of_buy}_{i + 1}')
            count_markup.insert(count_button)
        count_markup.add(back_button)
        await callback.answer()
        await callback.message.edit_text(f'<b>You choose:{item_of_buy}'
                                         f'\nPrice:{price}$'
                                         f'\nDescription: {description}'
                                         f'\nQuantity:</b>',
                                         reply_markup=count_markup, parse_mode='html')
    elif 'buy' in callback.data:
        """
        Выводит итоговую информацию о заказе с кнопками подтверждения заказа
        """
        subcategory = (split('_', callback.data)[1])
        item_of_buy = (split('_', callback.data)[2])
        quantity = (split('_', callback.data)[3])
        price = RequestToDB.get_price(item_of_buy)
        total_price = price * int(quantity)
        confirmation_markup = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton('Confirm', callback_data=f'confirm_{item_of_buy}_{quantity}')
        decline_button = types.InlineKeyboardButton('Decline', callback_data='decline')
        back_button = types.InlineKeyboardButton('🔙 Back', parse_mode='html',
                                                 callback_data=f'choose_{subcategory}_{item_of_buy}')
        confirmation_markup.add(confirm_button, decline_button, back_button)
        await callback.answer()
        await callback.message.edit_text(f'<b>You choose:{item_of_buy}\n'
                                         f'Price:{price}$\n'
                                         f'Quantity:{quantity} pcs\n'
                                         f'Total price:{total_price}$</b>',
                                         reply_markup=confirmation_markup, parse_mode='html')
    elif 'confirm' in callback.data:
        """
        Вызывает функционал завершения покупки
        """
        subcategory = (split('_', callback.data)[1])
        quantity = (split('_', callback.data)[2])
        price = RequestToDB.get_price(subcategory)
        total_price = int(price) * int(quantity)
        telegram_id = callback.message.chat.id
        await callback.answer()
        await bot.delete_message(callback.message.chat.id, callback.message.message_id)
        await consume_and_send_data(telegram_id, total_price, quantity, subcategory)
    elif callback.data == 'decline':
        """Функционал отмены покупки"""
        await callback.answer()
        await callback.message.edit_text('Declined!')
    elif callback.data == 'refresh_balance':
        """Функционал обновления балансов в коинах и USD, имеет КД в 30 секунд"""
        telegram_id = callback.message.chat.id
        if RequestToDB.can_be_refreshed(telegram_id):
            RequestToDB.create_refresh_data(telegram_id)
            balances = await WebRequest.parse_balances(telegram_id)
            await WebRequest.refresh_balance_in_usd(balances, telegram_id)
            top_up_button = types.InlineKeyboardButton('Top Up balance', callback_data='top_up_balance')
            purchase_history = types.InlineKeyboardButton('Purchase history', callback_data='purchase_history')
            update_balance = types.InlineKeyboardButton('Refresh balance', callback_data='refresh_balance')
            my_profile_markup = types.InlineKeyboardMarkup(row_width=2)
            balance_usd = RequestToDB.get_balance_in_usd_from_db(telegram_id)
            my_profile_markup.add(top_up_button, purchase_history, update_balance)
            try:
                await callback.message.edit_text(f'<b>Your profile\nID:</b> <code>{telegram_id}</code>\n\n'
                                                 f'<b>Your BTC balance:</b>\n<code>{balances[0]}</code>\n'
                                                 f'<b>Your USDT balance:</b>\n<code>{balances[1]}</code>\n'
                                                 f'<b>Your LTC balance:</b>\n<code>{balances[2]}</code>\n'
                                                 f"<b>Your balance in USD:</b>\n{format(balance_usd, '.2f')}$",
                                                 parse_mode="HTML", reply_markup=my_profile_markup)
                await callback.answer()
            except Exception:
                await callback.message.edit_text('<b>Please wait and try again later</b>', parse_mode='HTML')

        else:
            await callback.message.edit_text('<b>Please wait and try again later</b>', parse_mode='HTML')
    elif callback.data == 'purchase_history':
        """Функционал по выводу истории покупок:
        1) Получает из БД данные о покупках
        2) Создаёт инлайн кнопки с каждым заказом если они есть
        """
        telegram_id = callback.message.chat.id
        orders = RequestToDB.get_user_orders(telegram_id)
        orders_markup = types.InlineKeyboardMarkup()
        back_to_profile_button = types.InlineKeyboardButton('Back', callback_data='back_to_my_profile')
        for i in range(len(orders)):
            order_inline = types.InlineKeyboardButton(
                f'{orders[i][2]} | Total Price: {orders[i][4]}$ | Quantity: {orders[i][3]} pcs',
                callback_data=f'order_history_{orders[i][0]}')
            orders_markup.add(order_inline)
        orders_markup.add(back_to_profile_button)
        if not orders:
            await callback.message.edit_text("<b>You haven't had any orders yet</b>", reply_markup=orders_markup,
                                             parse_mode='html')
        else:
            await callback.message.edit_text('<b>Your orders</b>', reply_markup=orders_markup, parse_mode='html')
        await callback.answer()
    elif 'order_history' in callback.data:
        """Отправляет купленные данные при нажатии на историю конкретного заказа"""
        order_id = split('_', callback.data)[2]
        data = RequestToDB.get_sold_data(order_id)
        data = split('_end', data)
        for i in range(len(data)):
            if data[i] != '':
                await callback.message.answer(data[i])
    elif callback.data == 'top_up_balance':
        """Отправляет сообщение с адресами криптокошельков пользователя"""
        telegram_id = callback.message.chat.id
        wallets = RequestToDB.get_user_wallets(telegram_id)
        back_to_profile_button = types.InlineKeyboardButton('Back', callback_data='back_to_my_profile')
        back_button_markup = types.InlineKeyboardMarkup()
        back_button_markup.add(back_to_profile_button)
        await callback.message.edit_text(
            f'<b>Deposit to the address the amount you want to top up the Shop Bot</b> \n\n'
            f'<b>Important</b>\n<i>A unique BTC/LTC/USDT addresses is given for each deposit\n'
            f'The top up takes place within 5 minutes after the transfer</i>\n\n'
            f'<b>Your BTC address\n</b><code>{wallets[0]}</code>\n'
            f'<b>Your USDT TRC-20 address\n</b><code>{wallets[1]}</code>\n'
            f'<b>Your LTC address</b>\n<code>{wallets[2]}</code>\n', parse_mode='html',
            reply_markup=back_button_markup)
        await callback.answer()
    elif callback.data == 'back_to_all_categories':
        """Возвращает ко всем категориям"""
        categories = RequestToDB.get_categories()
        all_categories_markup = types.InlineKeyboardMarkup(row_width=2)
        for category in categories:
            category_button = types.InlineKeyboardButton(category[0], callback_data=f'show_{category[0]}')
            all_categories_markup.insert(category_button)
        await callback.message.edit_text('🔍 <b>All categories</b>', parse_mode='html',
                                         reply_markup=all_categories_markup)
        await callback.answer()
    elif callback.data == 'back_to_my_profile':
        """Возвращает к профилю пользователя"""
        telegram_id = callback.message.chat.id
        balances = await RequestToDB.get_wallets_balances_from_db(telegram_id)
        top_up_button = types.InlineKeyboardButton('Top Up balance', callback_data='top_up_balance')
        purchase_history = types.InlineKeyboardButton('Purchase history', callback_data='purchase_history')
        update_balance = types.InlineKeyboardButton('Refresh balance', callback_data='refresh_balance')
        my_profile_markup = types.InlineKeyboardMarkup(row_width=2)
        my_profile_markup.add(top_up_button, purchase_history, update_balance)
        balance_usd = RequestToDB.get_balance_in_usd_from_db(telegram_id)
        await callback.message.edit_text(f'<b>Your profile\nID:</b> <code>{telegram_id}</code>\n\n'
                                         f'<b>Your BTC balance:</b>\n<code>{balances[0]}</code>\n'
                                         f'<b>Your USDT balance:</b>\n<code>{balances[1]}</code>\n'
                                         f'<b>Your LTC balance:</b>\n<code>{balances[2]}</code>\n'
                                         f"<b>Your balance in USD:</b>\n{format(balance_usd, '.2f')}$",
                                         parse_mode="HTML", reply_markup=my_profile_markup)
        await callback.answer()
    elif callback.data == 'admin_send_to_all':
        """Получает сообщение админа для рассылки по пользователям"""
        await callback.message.edit_text('Введите текст для рассылки')
        await AdminMessage.admin_message.set()
    elif callback.data == 'admin_restocking':
        """Получает сообщение админа с новым товаром, запускает подфункции добавления товара"""
        await callback.message.edit_text('Отправьте .json файл для добавления товаров')
        await AdminMessage.restocking.set()
    elif callback.data == 'admin_get_new_users':
        """Функционал получения новых пользователей бота"""
        new_users, new_users_quantity = RequestToDB.get_new_users()
        if new_users:
            users_markup = types.InlineKeyboardMarkup()
            string_to_send = f'{new_users_quantity[0]} new users:\n'
            for user in new_users:
                user_button = types.InlineKeyboardButton(user[0], url=f't.me/{user[0]}')
                users_markup.add(user_button)
            await callback.message.edit_text(string_to_send, reply_markup=users_markup)
        else:
            await callback.message.edit_text('No new users')
    elif 'delete' in callback.data:
        """Функционал для удаления категорий и подкатегорий"""
        column = split("_", callback.data)[1]
        await callback.message.edit_text('Введите столбец для удаления')
        if column == 'category':
            await AdminMessage.category_to_delete.set()
        else:
            await AdminMessage.subcategory_to_delete.set()


if __name__ == '__main__':
    # executor.start_polling(dp, skip_updates=True)
    start_webhook(
        dispatcher=dp,
        webhook_path="",
        on_startup=on_startup,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
