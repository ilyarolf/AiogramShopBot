from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from re import split

# from aiogram.utils import executor

from CryptoAddressGenerator import CryptoAddressGenerator
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
admin_id = getenv('ADMIN_ID').split(',')
admin_id = list(map(int, admin_id))
bot = Bot(token)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())


async def on_startup(dp):
    # Функция отправляет сообщение админу при запуске
    await bot.set_webhook(WEBHOOK_URL)
    for admin in admin_id:
        try:
            await bot.send_message(admin, 'Bot is working')
        except:
            pass


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
    new_freebies = State()



async def new_top_up(new_balances, telegram_id):
    for key, value in new_balances.items():
        if value > 0:
            username = RequestToDB.get_username(telegram_id)
            wallet_addresses = RequestToDB.get_user_wallets(telegram_id)
            wallet_addresses = {'btc': wallet_addresses[0], 'ltc': wallet_addresses[2], 'usdt': wallet_addresses[1]}
            user_id = RequestToDB.get_user_id(telegram_id)
            private_key = CryptoAddressGenerator().get_private_keys(user_id)[key]
            if username:
                user_button = types.InlineKeyboardButton(f'{username}', url=f't.me/{username}')
                top_up_markup = types.InlineKeyboardMarkup()
                top_up_markup.add(user_button)
                for admin in admin_id:
                    await bot.send_message(admin,
                                           f"<b>New deposit by @{username} for"
                                           f" {value} {key}\n"
                                           f"{key.upper()}: <code>{wallet_addresses[key]}</code>\n"
                                           f"Key: <code>{private_key}</code></b>",
                                           parse_mode='html', reply_markup=top_up_markup)
            else:
                for admin in admin_id:
                    await bot.send_message(admin,
                                           f"<b>New deposit by user with id {telegram_id} for"
                                           f" {value} {key}\n"
                                           f"{key.upper()}: <code>{wallet_addresses[key]}</code>\n"
                                           f"Key: <code>{private_key}</code></b>",
                                           parse_mode='html')


async def new_buy(telegram_id, subcategory, quantity, total_price):
    username = RequestToDB.get_username(telegram_id)
    if username:
        new_purchase_markup = types.InlineKeyboardMarkup()
        user_button = types.InlineKeyboardButton(text=username, url=f't.me/{username}')
        new_purchase_markup.add(user_button)
        for admin in admin_id:
            await bot.send_message(admin, f'<b>New purchase by user @{username} for ${total_price}\n'
                                          f'Subcategory:{subcategory}\nQuantity:{quantity} pcs</b>',
                                   reply_markup=new_purchase_markup, parse_mode="html")
    else:
        for admin in admin_id:
            await bot.send_message(admin,
                                   f'<b>New purchase by user with ID <code>{telegram_id}<code> for ${total_price}\n'
                                   f'Subcategory:{subcategory}\nQuantity:{quantity} pcs</b>', parse_mode="html")


@dp.message_handler(commands='admin')
async def admin_menu(message: types.message):
    if message.chat.id in admin_id:
        # -Функция рассылки сообщения по всем юзерам
        # -Функция добавления товара в базу данных
        # -Функция получения новых пользователей
        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        send_to_all_users_button = types.InlineKeyboardButton('Send to everyone',
                                                              callback_data='admin_send_to_all')
        restocking_button = types.InlineKeyboardButton('Add items',
                                                       callback_data='admin_restocking')
        get_new_users_button = types.InlineKeyboardButton('Get new users',
                                                          callback_data='admin_get_new_users')
        delete_category_button = types.InlineKeyboardButton('Delete category',
                                                            callback_data='delete_category')
        delete_subcategory_button = types.InlineKeyboardButton('Delete subcategory',
                                                               callback_data='delete_subcategory')
        send_message_restocking = types.InlineKeyboardButton('Send restocking message',
                                                             callback_data='send_restocking_message')
        new_freebies_button = types.InlineKeyboardButton('Add new freebies',
                                                         callback_data='admin_new_freebies')
        delete_freebies_button = types.InlineKeyboardButton('Delete freebie',
                                                            callback_data='delete_freebie')
        get_received_freebies = types.InlineKeyboardButton('Get received freebies',
                                                           callback_data='admin_get_received_freebies')
        make_refund_button = types.InlineKeyboardButton('Make refund', callback_data='admin_make_refund')
        admin_markup.add(send_to_all_users_button, restocking_button, get_new_users_button,
                         delete_category_button, delete_subcategory_button,
                         send_message_restocking, new_freebies_button, delete_freebies_button, get_received_freebies,
                         make_refund_button)
        await message.answer('Admin menu', reply_markup=admin_markup)


@dp.message_handler(content_types=['text'], state=AdminMessage.admin_message)
async def get_admin_message(message: types.message, state: FSMContext):
    """
    Функция рассылки сообщения по всем пользователям в БД
    """
    async with state.proxy():
        if message.text != 'cancel':
            await state.finish()
            users = RequestToDB.get_all_users()
            send_count = int()
            for user_id in users:
                try:
                    await message.copy_to(chat_id=user_id[0])
                    send_count += 1
                except:
                    pass
            for admin in admin_id:
                await bot.send_message(admin, f'<b>Sent out to {send_count} users out of {len(users)}</b>\n'
                                              f'<code>{message.text}</code>', parse_mode='html')
        else:
            await state.finish()
            await bot.send_message(message.chat.id, f'<b>Cancelled!</b>', parse_mode='html')


async def send_restocking_message():
    """
    Функция для отправления сообщения о новом поступлении товара
    """
    new_items = RequestToDB.get_new_items()
    if new_items:
        users = RequestToDB.get_all_users()
        update_data = date.today()
        message = f'<b>📅 Update {update_data}\n'
        output_dict = dict()
        send_count = int()
        for item in new_items:
            category = item[0]
            subcategory = item[1]
            quantity = item[2]
            if output_dict.get(category) is None:
                output_dict[category] = [[subcategory, quantity]]
            else:
                temp_list = output_dict.get(category)
                temp_list.append([subcategory, quantity])
                output_dict[category] = temp_list
        for category, items in output_dict.items():
            message += f'\n📁 Category {category}\n\n'
            for item in items:
                subcategory = item[0]
                quantity = item[1]
                message += f'📄 Subcategory {subcategory} {quantity} pcs\n'
        message += '</b>'
        for user_id in users:
            try:
                await bot.send_message(user_id[0], message, parse_mode='html')
                send_count += 1
            except:
                pass
        RequestToDB.unset_new_items()
        for admin in admin_id:
            await bot.send_message(
                admin,
                f'<b>Messages about adding items have been sent to {send_count} out of {len(users)} users</b>',
                parse_mode='html')
    else:
        for admin in admin_id:
            await bot.send_message(admin, "No new items in database")


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
        RequestToDB.update_consume_records(telegram_id=telegram_id, total_price=total_price)
        private_data_list = str()
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
        await new_buy(telegram_id, subcategory, quantity, total_price)
    elif RequestToDB.get_quantity_in_stock(subcategory) <= int(quantity):
        await bot.send_message(telegram_id, 'Out of stock!')
    else:
        await bot.send_message(telegram_id, 'Insufficient funds!')


@dp.message_handler(content_types=[types.ContentType.DOCUMENT, types.ContentType.TEXT], state=AdminMessage.restocking)
async def get_restocking(message: types.message, state: FSMContext):
    """
    Функция для добавления нового товара включает:
    1) Подфункцию для получения файла с товаром из диалога с админом
    2) Распарсинг .json файла с списком товара, категорией, подкатегорией, прайсом, описанием
    3) Подфункцию для отправки сообщения по пользователям о новом поступлении
    """
    async with state.proxy():
        if message.document:
            document_id = message.document.file_id
            file_info = await bot.get_file(document_id)
            filename = file_info.file_path.split('/')[1]
            url = f'https://api.telegram.org/file/bot{token}/{file_info.file_path}'
            await WebRequest.get_admin_file(url, filename)
            try:
                restocking_dict = FileRequests.get_new_items(filename)
                for i in range(len(restocking_dict)):
                    position = restocking_dict[i]
                    restocking_list = position[0]
                    category = position[1]
                    subcategory = position[2]
                    price = position[3]
                    description = position[4]
                    RequestToDB.insert_restocking(restocking_list, category, subcategory, price, description)
                await state.finish()
                await message.answer('Done')
            except Exception as ex:
                print(ex)
                remove(filename)
                await state.finish()
                await message.answer('Error')
        else:
            await state.finish()
            await message.answer('Error')


@dp.message_handler(content_types=[types.ContentType.DOCUMENT, types.ContentType.TEXT], state=AdminMessage.new_freebies)
async def get_new_freebies(message: types.message, state: FSMContext):
    async with state.proxy():
        if message.document:
            document_id = message.document.file_id
            file_info = await bot.get_file(document_id)
            filename = file_info.file_path.split('/')[1]
            url = f'https://api.telegram.org/file/bot{token}/{file_info.file_path}'
            await WebRequest.get_admin_file(url, filename)
            try:
                freebies_dict = FileRequests.get_new_freebies(filename)
                RequestToDB.insert_new_freebie(freebies_dict)
                await state.finish()
                await message.answer('Done')
            except Exception as ex:
                print(ex)
                remove(filename)
                await state.finish()
                await message.answer('Error')
        else:
            await state.finish()
            await message.answer('Error')


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
    """
    Функция получает все категории из БД, и создаёт инлайн кнопки с категориями,если их нет то пишет 'No categories'
    """
    categories = RequestToDB.get_from_all_categories(categories=True)
    if categories:
        all_categories_markup = types.InlineKeyboardMarkup(row_width=2)
        for category in categories:
            category_button = types.InlineKeyboardButton(category[0], callback_data=f'show_{category[0]}')
            all_categories_markup.insert(category_button)
        free_manuals_button = types.InlineKeyboardButton('Free', callback_data='show_freebies')
        all_categories_markup.insert(free_manuals_button)
        await message.answer('🔍 <b>All categories</b>', parse_mode='html', reply_markup=all_categories_markup)
    else:
        await message.answer('<b>No categories</b>', parse_mode='html')


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
    balances = RequestToDB.get_wallets_balances_from_db(message.chat.id)
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
    back_button = types.InlineKeyboardButton('Back', callback_data='back_to_admin_menu')
    """Обрабатывает нажатия инлайн кнопок"""
    if 'show_' in callback.data:
        """
        Выгружает подкатегории из БД и создаёт инлайн кнопки с подкатегориями, ценой и их наличием
        """
        item = (split('_', callback.data)[1])
        back_button = types.InlineKeyboardButton('🔙 Back', callback_data='back_to_all_categories')
        freebies_markup = types.InlineKeyboardMarkup()
        if item == 'freebies':
            freebies = RequestToDB.get_from_all_categories(freebies=True)
            if freebies:
                freebies = [freebie[0] for freebie in freebies]
                for freebie in freebies:
                    freebie_button = types.InlineKeyboardButton(freebie, callback_data=f'get_freebie_{freebie}')
                    freebies_markup.add(freebie_button)
                freebies_markup.add(back_button)
                await callback.answer()
                await callback.message.edit_text('<b>Manuals</b>', parse_mode='html', reply_markup=freebies_markup)
            else:
                await callback.answer()
                freebies_markup.add(back_button)
                await callback.message.edit_text('<b>No Manuals</b>', parse_mode='html', reply_markup=freebies_markup)
        else:
            subcategory = RequestToDB.get_data(item)
            subcategory = list(dict.fromkeys(subcategory))
            subcategory_markup = types.InlineKeyboardMarkup()
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
            old_balances = RequestToDB.get_wallets_balances_from_db(telegram_id)
            RequestToDB.create_refresh_data(telegram_id)
            balances = await WebRequest.parse_balances(telegram_id)
            if (sum(balances) - sum(old_balances)) > 0:
                new_balances = dict()
                coin_list = ['btc', 'usdt', 'ltc']
                for i in range(len(balances)):
                    new_balances[coin_list[i]] = (balances[i] - old_balances[i])
                await new_top_up(new_balances, telegram_id)
                await WebRequest.refresh_balance_in_usd(list(new_balances.values()), telegram_id)
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
            except Exception as e:
                print(e)
                await callback.answer()

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
        categories = RequestToDB.get_from_all_categories(categories=True)
        all_categories_markup = types.InlineKeyboardMarkup(row_width=2)
        for category in categories:
            category_button = types.InlineKeyboardButton(category[0], callback_data=f'show_{category[0]}')
            all_categories_markup.insert(category_button)
        free_manuals_button = types.InlineKeyboardButton('Free', callback_data='show_freebies')
        all_categories_markup.insert(free_manuals_button)
        await callback.message.edit_text('🔍 <b>All categories</b>', parse_mode='html',
                                         reply_markup=all_categories_markup)
        await callback.answer()
    elif callback.data == 'back_to_my_profile':
        """Возвращает к профилю пользователя"""
        telegram_id = callback.message.chat.id
        balances = RequestToDB.get_wallets_balances_from_db(telegram_id)
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
        await callback.message.edit_text('Enter text to sent out\nType "cancel" for cancel')
        await AdminMessage.admin_message.set()
    elif callback.data == 'admin_restocking':
        """Получает сообщение админа с новым товаром, запускает подфункции добавления товара"""
        await callback.message.edit_text('<b>Send a .json file to add items</b>', parse_mode='html')
        await AdminMessage.restocking.set()
    elif callback.data == 'admin_new_freebies':
        """Получает сообщение админа с новой халявой, запускает подфункции добавления халявы"""
        await callback.message.edit_text('<b>Send a .json file to add new freebies</b>', parse_mode='html')
        await AdminMessage.new_freebies.set()
    elif callback.data == 'admin_get_new_users':
        """Функционал получения новых пользователей бота"""
        new_users, new_users_quantity = RequestToDB.get_new_users()
        users_markup = types.InlineKeyboardMarkup()
        if new_users:
            string_to_send = f'{new_users_quantity[0]} new users:\n'
            for user in new_users:
                user_button = types.InlineKeyboardButton(user[0], url=f't.me/{user[0]}')
                users_markup.add(user_button)
            users_markup.add(back_button)
            await callback.message.edit_text(string_to_send, reply_markup=users_markup)
        elif new_users_quantity[0] > 0:
            string_to_send = f'{new_users_quantity[0]} new users:\n'
            users_markup.add(back_button)
            await callback.message.edit_text(string_to_send, reply_markup=users_markup)
        else:
            users_markup.add(back_button)
            await callback.message.edit_text('No new users', reply_markup=users_markup)
    elif callback.data == 'admin_get_received_freebies':
        """Функционал получения новых пользователей, которые получили халяву"""
        new_users, new_users_quantity, received_freebies_quantity = RequestToDB.get_received_freebies()
        users_markup = types.InlineKeyboardMarkup()
        if new_users.keys():
            string_to_send = f'{new_users_quantity} users get freebie:\n'
            for user, freebies in new_users.items():
                user_button = types.InlineKeyboardButton(user, url=f't.me/{user}')
                users_markup.add(user_button)
                freebies_stringify = ', '.join(freebies)
                string_to_send += f'{user}:{freebies_stringify}\n'
            users_markup.add(back_button)
            await callback.message.edit_text(string_to_send, reply_markup=users_markup)
        elif new_users_quantity > 0 and received_freebies_quantity > 0:
            string_to_send = f'{new_users_quantity} users get {received_freebies_quantity} freebies'
            users_markup.add(back_button)
            await callback.message.edit_text(string_to_send, reply_markup=users_markup)
        else:
            users_markup.add(back_button)
            await callback.message.edit_text('No received freebies', reply_markup=users_markup)
    elif 'delete' in callback.data:
        """Функционал для удаления категорий и подкатегорий"""
        column = split("_", callback.data)[1]
        if column == 'category':
            categories = RequestToDB.get_from_all_categories(categories=True)
            categories_markup = types.InlineKeyboardMarkup()
            if len(categories) == 0:
                categories_markup.add(back_button)
                await callback.message.edit_text('No categories', reply_markup=categories_markup)
            else:
                for i in range(len(categories)):
                    category_button = types.InlineKeyboardButton(categories[i][0],
                                                                 callback_data=f'del_this_{column}_{categories[i][0]}')
                    categories_markup.add(category_button)
                    categories_markup.add(back_button)
                await callback.message.edit_text('Choose category to delete', reply_markup=categories_markup)
        elif column == 'subcategory':
            subcategories = RequestToDB.get_from_all_categories(subcategories=True)
            subcategories_markup = types.InlineKeyboardMarkup()
            if len(subcategories) == 0:
                subcategories_markup.add(back_button)
                await callback.message.edit_text('No subcategories', reply_markup=subcategories_markup)
            else:
                for i in range(len(subcategories)):
                    subcategory_button = types.InlineKeyboardButton(
                        subcategories[i][0], callback_data=f'del_this_{column}_{subcategories[i][0]}')
                    subcategories_markup.add(subcategory_button)
                subcategories_markup.add(back_button)
                await callback.message.edit_text('Choose subcategory to delete', reply_markup=subcategories_markup)
        elif column == 'freebie':
            freebies = RequestToDB.get_from_all_categories(freebies=True)
            freebies_markup = types.InlineKeyboardMarkup()
            if len(freebies) == 0:
                freebies_markup.add(back_button)
                await callback.message.edit_text('No freebies', reply_markup=freebies_markup)
            else:
                for i in range(len(freebies)):
                    freebie_button = types.InlineKeyboardButton(
                        freebies[i][0], callback_data=f'del_this_{column}_{freebies[i][0]}')
                    freebies_markup.add(freebie_button)
                freebies_markup.add(back_button)
                await callback.message.edit_text('Choose freebie to delete', reply_markup=freebies_markup)
    elif callback.data == 'back_to_admin_menu':
        """
        Функционал возврата в админское меню
        """
        admin_markup = types.InlineKeyboardMarkup(row_width=2)
        send_to_all_users_button = types.InlineKeyboardButton('Send to everyone',
                                                              callback_data='admin_send_to_all')
        restocking_button = types.InlineKeyboardButton('Add items',
                                                       callback_data='admin_restocking')
        get_new_users_button = types.InlineKeyboardButton('Get new users',
                                                          callback_data='admin_get_new_users')
        delete_category_button = types.InlineKeyboardButton('Delete category',
                                                            callback_data='delete_category')
        delete_subcategory_button = types.InlineKeyboardButton('Delete subcategory',
                                                               callback_data='delete_subcategory')
        send_message_restocking = types.InlineKeyboardButton('Send restocking message',
                                                             callback_data='send_restocking_message')
        new_freebies_button = types.InlineKeyboardButton('Add new freebies',
                                                         callback_data='admin_new_freebies')
        delete_freebies_button = types.InlineKeyboardButton('Delete freebie',
                                                            callback_data='delete_freebie')
        get_received_freebies = types.InlineKeyboardButton('Get received freebies',
                                                           callback_data='admin_get_received_freebies')
        make_refund_button = types.InlineKeyboardButton('Make refund', callback_data='admin_make_refund')
        admin_markup.add(send_to_all_users_button, restocking_button, get_new_users_button,
                         delete_category_button, delete_subcategory_button,
                         send_message_restocking, new_freebies_button, delete_freebies_button, get_received_freebies,
                         make_refund_button)
        await callback.message.edit_text('Admin menu', reply_markup=admin_markup)
    elif 'del_this' in callback.data:
        """
        Функционал удаления подкатегорий и категорий с помощью инлайн кнопок
        """
        item = split("_", callback.data)[2]
        item_name = split("_", callback.data)[3]
        if item == 'category':
            try:
                RequestToDB.delete_category(item_name)
                await callback.message.edit_text('<b>Done</b>', parse_mode='html')
            except Exception as e:
                await callback.message.edit_text(f'<b>Error</b>\n<code>{e}</code>', parse_mode='html')
        elif item == 'subcategory':
            try:
                RequestToDB.delete_subcategory(item_name)
                await callback.message.edit_text('<b>Done</b>', parse_mode='html')
            except Exception as e:
                await callback.message.edit_text(f'<b>Error</b>\n<code>{e}</code>', parse_mode='html')
        elif item == 'freebie':
            try:
                RequestToDB.delete_freebie(item_name)
                await callback.message.edit_text('<b>Done</b>', parse_mode='html')
            except Exception as e:
                await callback.message.edit_text(f'<b>Error</b>\n<code>{e}</code>', parse_mode='html')

    elif callback.data == 'send_restocking_message':
        await send_restocking_message()
    elif 'get_freebie_' in callback.data:
        freebie = split('get_freebie_', callback.data)[1]
        freebie_data = RequestToDB.get_freebie_data(freebie)
        freebie_markup = types.InlineKeyboardMarkup()
        freebie_button = types.InlineKeyboardButton(f'{freebie}', url=freebie_data)
        freebie_markup.add(freebie_button)
        await callback.message.edit_text('<b>Your freebie</b>', parse_mode='html', reply_markup=freebie_markup)
        RequestToDB.set_freebie_received(freebie, callback.from_user.id, callback.from_user.username)
    elif callback.data == 'admin_make_refund':
        buys = RequestToDB.get_not_refunded_buys()
        refund_markup = types.InlineKeyboardMarkup()
        for buy in buys:
            username = RequestToDB.get_username(buy[1])
            if username is None:
                refund_button = types.InlineKeyboardButton(f'{buy[0]}|ID:{buy[1]}|{buy[2]}$',
                                                           callback_data=f'refund_order_with_id_{buy[3]}')
                refund_markup.add(refund_button)
            else:
                refund_button = types.InlineKeyboardButton(f'{buy[0]}|{username}|{buy[2]}$',
                                                           callback_data=f'refund_order_with_id_{buy[3]}')
                refund_markup.add(refund_button)
        refund_markup.add(back_button)
        await callback.message.edit_text("<b>Refund menu</b>", parse_mode="html", reply_markup=refund_markup)
    elif 'refund_order_with_id_' in callback.data:
        buy_id = callback.data.split('refund_order_with_id_')[1]
        user_id = RequestToDB.make_refund(buy_id)
        await callback.message.edit_text("<b>Done!</b>", parse_mode="html")
        refund_data = RequestToDB.get_buy_data(buy_id)
        refund_sum = refund_data['price_total']
        refund_subcategory = refund_data['subcategory']
        try:
            await bot.send_message(user_id,
                                   f"<b>Refunded {refund_sum}$ for the purchase of {refund_subcategory}</b>",
                                   parse_mode='html')
        except:
            for admin in admin_id:
                username = RequestToDB.get_username(refund_data['telegram_id'])
                if username is not None:
                    await bot.send_message(admin,
                                           f"Failed to send a message to user @{username} about a ${refund_sum} refund on {refund_subcategory}")
                else:
                    await bot.send_message(admin,
                                           f"Failed to send a message to user with ID:{refund_data['telegram_id']} about a ${refund_sum} refund on {refund_subcategory}")


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
