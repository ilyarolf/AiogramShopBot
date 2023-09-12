from pysqlcipher3 import dbapi2 as sqlite3
import datetime
from dateutil.parser import parse
from CryptoAddressGenerator import CryptoAddressGenerator
from config import DB_PASS


class RequestToDB:
    """Класс для запросов в БД"""

    def __init__(self, db_file: str) -> None:
        """Инициализация класса, подключение к БД"""
        self.connect = sqlite3.connect(db_file)
        self.cursor = self.connect.cursor()
        self.cursor.execute(f"PRAGMA key={DB_PASS}")

    def get_user_wallets(self, telegram_id: int) -> list:
        """Получает адреса криптокошельков пользователя из БД"""
        currency_list = ['btc', 'trx', 'ltc']
        wallets = []
        for currency in currency_list:
            wallet = (
                self.cursor.execute(f'SELECT `{currency}_address` from `users` where `telegram_id` = ?',
                                    (telegram_id,)).fetchone()[
                    0])
            wallet = wallet.replace('\n', '')
            wallets.append(wallet)

        return wallets

    def create_refresh_data(self, telegram_id: int) -> None:
        """Создаёт дату и время последнего обновления баланса пользователя"""
        time = datetime.datetime.now()
        self.cursor.execute('UPDATE `users` SET `last_refresh` = ? where `telegram_id` = ?', (time, telegram_id))
        self.connect.commit()

    def get_balance_in_usd_from_db(self, telegram_id: int) -> int:
        """Получает сумму пополнений и сумму трат, из разницы получается баланс и возвращает его"""
        top_up_amount = \
            self.cursor.execute("SELECT `top_up_amount` FROM `users` WHERE `telegram_id` = ?",
                                (telegram_id,)).fetchone()[0]
        consume_records = \
            self.cursor.execute('SELECT `consume_records` from `users` where `telegram_id` = ?',
                                (telegram_id,)).fetchone()[
                0]
        balance = top_up_amount - consume_records
        return balance

    def get_wallets_balances_from_db(self, telegram_id: int):
        """Получает балансы крипты из БД"""
        wallets = \
            self.cursor.execute(
                'SELECT `btc_balance`, `usdt_balance`, `ltc_balance` FROM `users` WHERE `telegram_id` = ?',
                (telegram_id,)).fetchall()[0]
        return wallets

    def insert_new_user(self, telegram_id: int, username: str) -> None:
        """Создаёт запись в БД о новом пользователе"""
        wallets = CryptoAddressGenerator().get_addresses(self.get_next_user_id())
        btc_wallet = wallets['btc']
        ltc_wallet = wallets['ltc']
        trx_wallet = wallets['trx']
        if username:
            self.cursor.execute(
                "INSERT OR IGNORE INTO `users` (`telegram_username`,`telegram_id`,`btc_address`,`ltc_address`,"
                " `trx_address`) VALUES (?, ?, ?, ?, ?)",
                (username, telegram_id, btc_wallet, ltc_wallet, trx_wallet))
            self.connect.commit()
        else:
            self.cursor.execute(
                "INSERT OR IGNORE INTO `users` (`telegram_id`,`btc_address`,`ltc_address`,"
                " `trx_address`) VALUES (?, ?, ?, ?)",
                (telegram_id, btc_wallet, ltc_wallet, trx_wallet))
            self.connect.commit()

    def get_data(self, category: str):
        """Возвращает подкатегории с нужной категорией"""
        data = self.cursor.execute(f'SELECT `subcategory` from `items` where `category` = ?', (category,)).fetchall()
        return data

    # def get_freebies(self) -> list:
    #     """Возвращает имена халявы из БД"""
    #     freebies_name = self.cursor.execute('SELECT `freebie_name` FROM `freebies`').fetchall()
    #     return freebies_name

    def get_freebie_data(self, freebie_name) -> str:
        """Возвращает данные халявы из БД"""
        freebie_data = self.cursor.execute('SELECT `freebie_data` FROM `freebies` WHERE `freebie_name` = ?',
                                           (freebie_name,)).fetchone()[0]
        return freebie_data

    def set_freebie_received(self, freebie_name, telegram_id, telegram_username) -> None:
        """Проверяет, если пользователь ещё не получал халяву,
         то добавляет его в таблицу получателей халявы, если получал то ничего не делает"""
        is_exist = self.cursor.execute("SELECT EXISTS(SELECT * FROM `received_freebies`"
                                       " WHERE `telegram_id` = ? AND `freebie_name` = ?)",
                                       (telegram_id, freebie_name)).fetchone()[0]
        if is_exist != 1:
            self.cursor.execute("INSERT OR IGNORE INTO `received_freebies` "
                                "(`telegram_id`, `freebie_name`, `telegram_username`) VALUES (?, ?, ?)",
                                (telegram_id, freebie_name, telegram_username))
            self.connect.commit()

    def insert_new_freebie(self, freebies_dict):
        """Функция добавляет халяву в БД"""
        for freebie_name, freebie_data in freebies_dict.items():
            self.cursor.execute("INSERT INTO `freebies` (`freebie_name`, `freebie_data`) VALUES (?, ?)",
                                (freebie_name, freebie_data))
        self.connect.commit()

    def delete_freebie(self, freebie_name):
        """Функция удаляет халяву из БД"""
        self.cursor.execute(f'DELETE FROM `freebies` WHERE `freebie_name` = ?', (freebie_name,))
        self.connect.commit()

    def get_received_freebies(self):
        """Подфункция для получения пользователей которые получили халяву"""
        new_users = self.cursor.execute(
            'SELECT `telegram_username`, `freebie_name` FROM `received_freebies` WHERE `is_new` = 1 AND'
            ' `telegram_username` not NULL').fetchall()
        user_freebie_dict = {}
        for key, value in new_users:
            if key not in user_freebie_dict:
                user_freebie_dict[key] = [value]
            else:
                user_freebie_dict[key].append(value)
        new_users_quantity = self.cursor.execute(
            'SELECT count (DISTINCT `telegram_id`) FROM `received_freebies` WHERE `is_new` == 1').fetchone()[0]
        received_freebies_quantity = \
            self.cursor.execute('SELECT count (*) FROM `received_freebies` WHERE `is_new` == 1').fetchone()[0]
        self.cursor.execute('UPDATE `received_freebies` SET `is_new` = 0 WHERE `is_new` = 1')
        self.connect.commit()
        return user_freebie_dict, new_users_quantity, received_freebies_quantity

    def get_price(self, subcategory: str):
        """Возвращает цену подкатегории"""
        price = self.cursor.execute(f'SELECT `price` from `items` where `subcategory` = ?', (subcategory,)).fetchone()[
            0]
        return price

    def get_quantity_in_stock(self, subcategory: str):
        """Возвращает количество непроданных позиций подкатегории"""
        quantity = \
            self.cursor.execute(f'SELECT COUNT(*) as `count` FROM `items` WHERE `subcategory`= ? and `is_sold` = ?',
                                (subcategory, 0)).fetchone()[0]
        return quantity

    def can_be_refreshed(self, telegram_id: int):
        """Возвращает булево значение, возможно ли обновить баланс пользователя"""
        now_time = datetime.datetime.now()
        last_time = \
            self.cursor.execute('SELECT `last_refresh` FROM `users` where telegram_id = ?', (telegram_id,)).fetchone()[
                0]
        if last_time is None:
            RequestToDB.create_refresh_data(self, telegram_id)
            return True
        else:
            last_time = parse(last_time)
            timedelta = (now_time - last_time).total_seconds()
            # return True
            return timedelta > 30

    def update_balances(self, balances: list, telegram_id: int) -> None:
        """Обновляет балансы крипты для пользователя"""
        self.cursor.execute(
            'update `users` set (`btc_balance`, `usdt_balance`, `ltc_balance`) = (?, ?, ?) Where `telegram_id` = ?',
            (balances[0], balances[1], balances[2], telegram_id))
        self.connect.commit()

    def update_consume_records(self, total_price: str, telegram_id: str) -> None:
        """Обновляет расход пользователя, прибавляет к текущему расходу итоговую цену купленных позиций"""
        consume_records = \
            self.cursor.execute('SELECT `consume_records` from `users` where `telegram_id` = ?',
                                (telegram_id,)).fetchone()[
                0]
        consume_records += int(total_price)
        self.cursor.execute("UPDATE `users` SET `consume_records` = ? where `telegram_id` = ?",
                            (consume_records, telegram_id))
        self.connect.commit()

    def get_unsold_data(self, subcategory: str):
        """Возвращет строку с данными которые вот-вот продадутся """
        data = \
            self.cursor.execute(
                'SELECT `private_data`, `item_id` FROM `items` WHERE `subcategory`= ? AND `is_sold` = ?',
                (subcategory, 0)).fetchall()[0]
        return data

    def set_item_sold(self, item_id: int) -> None:
        """Помечает позицию как купленную"""
        self.cursor.execute("UPDATE `items` SET `is_sold` = ? where `item_id` = ?",
                            (1, item_id))
        self.connect.commit()

    def insert_new_buy(self, telegram_id: int, subcategory, quantity, total_price, private_data_list) -> None:
        """Создаёт запись о новой покупке пользователя"""
        self.cursor.execute(
            'INSERT INTO `buys`(`telegram_id`,`subcategory`,`quantity`, `price_total`, sold_data) '
            'VALUES (?, ?, ?, ?, ?)',
            (telegram_id, subcategory, quantity, total_price, private_data_list))
        self.connect.commit()

    def get_user_orders(self, telegram_id: int):
        """Получает все покупки пользователя"""
        orders = self.cursor.execute('SELECT * FROM `buys` where `telegram_id` = ?', (telegram_id,)).fetchall()
        return orders

    def update_balance_usd(self, balance_list: list, telegram_id) -> None:
        """Обновляет баланс в долларах"""
        old_balance = self.cursor.execute('SELECT `top_up_amount` from `users` WHERE `telegram_id` = ?',
                                          (telegram_id,)).fetchall()[0][0]
        usd_balance = sum(balance_list) + old_balance
        self.cursor.execute("UPDATE `users` SET `top_up_amount` = ? where `telegram_id` = ?",
                            (format(usd_balance, '.2f'), telegram_id))
        self.connect.commit()

    def get_sold_data(self, order_id):
        """Отправляет ранее купленные данные пользователем, служит подфункцией для функционала истории покупок"""
        sold_data = self.cursor.execute('SELECT `sold_data` FROM `buys` WHERE `buys_id` = ?', (order_id,)).fetchone()[0]
        return sold_data

    def get_all_users(self):
        """Возвращает все telegram id пользователей из БД"""
        users = self.cursor.execute('SELECT `telegram_id` FROM `users`').fetchall()
        return users

    def insert_restocking(self, restocking_list, category, subcategory, price, description) -> None:
        """Создаёт записи с новыми товарами"""
        for item in restocking_list:
            self.cursor.execute('INSERT INTO `items` (`category`,'
                                '`subcategory`,'
                                '`private_data`,'
                                '`price`,'
                                '`is_sold`,'
                                '`is_new`,'
                                '`description`) VALUES (?, ?, ?, ?, ?, ?, ?) ',
                                (category, subcategory, str(item), price, 0, 1, description))
            self.connect.commit()

    def get_new_users(self):
        """Подфункция для получения новых пользователей, нунжа для админского функционала получения новых юзеров"""
        new_users = self.cursor.execute('SELECT `telegram_username` FROM `users` WHERE `is_new` = 1 AND'
                                        ' `telegram_username` not NULL').fetchall()
        new_users_quantity = self.cursor.execute('SELECT count (*) FROM `users` WHERE `is_new` == 1').fetchone()
        self.cursor.execute('UPDATE `users` SET `is_new` = 0 WHERE `is_new` = 1')
        self.connect.commit()
        return new_users, new_users_quantity

    def is_exist(self, telegram_id: int):
        """Проверяет наличие пользователя в БД"""
        is_exist = \
            self.cursor.execute('SELECT EXISTS (SELECT * from `users` where `telegram_id` = ?)',
                                (telegram_id,)).fetchone()[0]
        return is_exist

    def update_username(self, username: str, telegram_id: int) -> None:
        """Обновляет юзернейм пользователя в бд"""
        self.cursor.execute('UPDATE `users` SET `telegram_username`= ? where `telegram_id` = ?',
                            (username, telegram_id))
        self.connect.commit()

    def get_from_all_categories(self, categories: bool = False, subcategories: bool = False, freebies: bool = False):
        if categories:
            categories = self.cursor.execute('SELECT DISTINCT `category` FROM `items`').fetchall()
            return categories
        elif subcategories:
            categories = self.cursor.execute('SELECT DISTINCT `subcategory` FROM `items`').fetchall()
            return categories
        elif freebies:
            freebies_name = self.cursor.execute('SELECT `freebie_name` FROM `freebies`').fetchall()
            return freebies_name

    def delete_category(self, data_to_delete):
        """Удаляет категорию в БД"""
        self.cursor.execute(f'DELETE FROM `items` WHERE `category` = ?', (data_to_delete,))
        self.connect.commit()

    def delete_subcategory(self, data_to_delete):
        """Удаляет подкатегорию в БД"""
        self.cursor.execute(f'DELETE FROM `items` WHERE `subcategory` = ?', (data_to_delete,))
        self.connect.commit()

    def get_description(self, subcategory):
        """Функция получения описания товара из БД"""
        description = self.cursor.execute(f'SELECT `description` FROM `items` WHERE `subcategory` = ?',
                                          (subcategory,)).fetchone()[0]
        return description

    def get_username(self, telegram_id):
        """Функция получения telegram username из БД"""
        username = self.cursor.execute('SELECT `telegram_username` FROM `users` WHERE `telegram_id` = ?',
                                       (telegram_id,)).fetchone()
        return username[0]

    def get_new_items(self):
        """
        Функция возвращает категории, подкатегории, количество подкатегорий новых товаров. Функция нужна для рассылки
        сообщения о новом пополнении
        """
        new_items = self.cursor.execute(
            'SELECT `category`,'
            '`subcategory`,'
            'COUNT(*) AS count FROM `items` WHERE `is_new` = 1 GROUP BY category, subcategory ORDER BY category;').fetchall()
        return new_items

    def get_not_refunded_buys(self):
        not_refunded_buys = self.cursor.execute(
            "SELECT `subcategory`, `telegram_id`, `price_total`, `buys_id` FROM `buys` WHERE `is_refunded` = 0").fetchall()
        return not_refunded_buys

    # def __get_refund_data(self, buy_id):
    #     data = self.cursor.execute("SELECT `telegram_id`, `price_total` FROM `buys` WHERE `buys_id` = ?",
    #                                (buy_id,)).fetchall()[0]
    #     return data

    def make_refund(self, buy_id):
        refund_data = self.get_buy_data(buy_id)
        telegram_id = refund_data['telegram_id']
        sum_of_refund = refund_data['price_total']
        consume_records = \
            self.cursor.execute('SELECT `consume_records` FROM `users` WHERE `telegram_id` = ?',
                                (telegram_id,)).fetchone()[
                0]
        new_consume_records = int(consume_records) - int(sum_of_refund)
        self.cursor.execute('UPDATE `users` SET `consume_records` = ? WHERE `telegram_id` = ?',
                            (new_consume_records, telegram_id))
        self.cursor.execute('UPDATE `buys` SET `is_refunded` = 1 WHERE `buys_id` = ?', (buy_id,))
        self.connect.commit()
        return telegram_id

    def get_buy_data(self, buy_id):
        data = self.cursor.execute("SELECT * FROM `buys` WHERE `buys_id` = ?", (buy_id,)).fetchall()[0]
        column_names = [column[0] for column in self.cursor.description]
        data_dict = {}
        for i, column_name in enumerate(column_names):
            data_dict[column_name] = data[i]

        return data_dict

    def unset_new_items(self):
        """
        Функция помечает новые предметы как не новые после рассылки сообщения о новом пополнении товаров
        """
        self.cursor.execute('UPDATE `items` SET `is_new` = 0 WHERE `is_new` = 1')
        self.connect.commit()

    def get_next_user_id(self) -> int:
        last_id = self.cursor.execute("SELECT MAX(user_id) FROM `users`").fetchone()[0]
        if last_id is not None:
            return last_id + 1
        else:
            return 0

    def get_user_id(self, telegram_id: int) -> int:
        user_id = self.cursor.execute("SELECT `user_id` FROM `users` WHERE `telegram_id` = ?",(telegram_id, )).fetchone()[0]
        return user_id

    def close(self):
        """Закрывает соедининие с БД"""
        self.connect.close()
