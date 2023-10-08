import datetime
from dateutil.parser import parse
from CryptoAddressGenerator import CryptoAddressGenerator
from db import db


class User:
    def __init__(self, telegram_id: int, telegram_username: str):
        next_user_id = self.__get_next_user_id()
        crypto_wallets = CryptoAddressGenerator().get_addresses(next_user_id)
        btc_address = crypto_wallets['btc']
        ltc_address = crypto_wallets['ltc']
        trx_address = crypto_wallets['trx']
        self.telegram_id = telegram_id
        self.btc_address = btc_address
        self.ltc_address = ltc_address
        self.trx_address = trx_address
        self.telegram_username = telegram_username

    def __get_next_user_id(self) -> int:
        last_id = db.cursor.execute("SELECT MAX(user_id) FROM `users`").fetchone()["MAX(user_id)"]
        if last_id is not None:
            return last_id + 1
        else:
            return 0

    def create(self):
        if self.telegram_username:
            db.cursor.execute(
                "INSERT OR IGNORE INTO `users` (`telegram_username`,`telegram_id`,`btc_address`,`ltc_address`,"
                " `trx_address`) VALUES (?, ?, ?, ?, ?)",
                (self.telegram_username, self.telegram_id, self.btc_address, self.ltc_address, self.trx_address))
            db.connect.commit()
        else:
            db.cursor.execute(
                "INSERT OR IGNORE INTO `users` (`telegram_id`,`btc_address`,`ltc_address`,"
                " `trx_address`) VALUES (?, ?, ?, ?)",
                (self.telegram_id, self.btc_address, self.ltc_address, self.trx_address))
            db.connect.commit()

    @staticmethod
    def is_exist(telegram_id: int) -> bool:
        is_exist = db.cursor.execute('SELECT EXISTS (SELECT * from `users` where `telegram_id` = ?)',
                                     (telegram_id,)).fetchone()[
            "EXISTS (SELECT * from `users` where `telegram_id` = ?)"]
        return bool(is_exist)

    @staticmethod
    def update_username(telegram_id: int, telegram_username: str):
        db.cursor.execute('UPDATE `users` SET `telegram_username`= ? where `telegram_id` = ?',
                          (telegram_username, telegram_id))
        db.connect.commit()

    @staticmethod
    def get(telegram_id: int):
        user = db.cursor.execute('SELECT * FROM `users` WHERE `telegram_id` = ?', (telegram_id,)).fetchall()[0]
        return user

    @staticmethod
    def can_refresh_balance(telegram_id: int):
        now_time = datetime.datetime.now()
        last_time = \
            db.cursor.execute('SELECT `last_refresh` FROM `users` where telegram_id = ?', (telegram_id,)).fetchone()[
                "last_refresh"]
        if last_time is None:
            User.create_last_balance_refresh_data(telegram_id)
            return True
        else:
            last_time = parse(last_time)
            timedelta = (now_time - last_time).total_seconds()
            return timedelta > 30

    @staticmethod
    def create_last_balance_refresh_data(telegram_id):
        time = datetime.datetime.now()
        db.cursor.execute('UPDATE `users` SET `last_refresh` = ? where `telegram_id` = ?', (time, telegram_id))
        db.connect.commit()

    @staticmethod
    def get_balances(telegram_id):
        wallets = db.cursor.execute(
            'SELECT `btc_balance`, `usdt_balance`, `ltc_balance` FROM `users` WHERE `telegram_id` = ?',
            (telegram_id,)).fetchall()[0]
        return wallets

    @staticmethod
    def get_addresses(telegram_id: int):
        addresses = db.cursor.execute(
            'SELECT `btc_address`, `ltc_address`, `trx_address` FROM `users` WHERE `telegram_id` = ?',
            (telegram_id,)).fetchall()[0]
        return addresses

    @staticmethod
    def update_crypto_balances(telegram_id: int, crypto_balances: dict):
        btc_balance = crypto_balances['btc_balance']
        ltc_balance = crypto_balances['ltc_balance']
        usdt_balance = crypto_balances['usdt_balance']
        db.cursor.execute(
            'update `users` set (`btc_balance`, `usdt_balance`, `ltc_balance`) = (?, ?, ?) Where `telegram_id` = ?',
            (btc_balance, usdt_balance, ltc_balance, telegram_id))
        db.connect.commit()

    @staticmethod
    def update_top_up_amount(telegram_id: int, usd_balance: float):
        old_usd_balance = db.cursor.execute('SELECT `top_up_amount` from `users` WHERE `telegram_id` = ?',
                                            (telegram_id,)).fetchone()[0]
        new_usd_balance = old_usd_balance + usd_balance
        db.cursor.execute("UPDATE `users` SET `top_up_amount` = ? where `telegram_id` = ?",
                          (format(new_usd_balance, '.2f'), telegram_id))
        db.connect.commit()

    @staticmethod
    def update_consume_records(telegram_id: int, total_price: float) -> None:
        consume_records = \
            db.cursor.execute('SELECT `consume_records` from `users` where `telegram_id` = ?',
                              (telegram_id,)).fetchone()['consume_records']
        consume_records += float(total_price)
        db.cursor.execute("UPDATE `users` SET `consume_records` = ? where `telegram_id` = ?",
                          (consume_records, telegram_id))
        db.connect.commit()

    @staticmethod
    def is_buy_possible(telegram_id: int, total_price: float) -> bool:
        user = User.get(telegram_id)
        user_balance = user['top_up_amount'] - user['consume_records']
        return user_balance >= total_price

    @staticmethod
    def get_users_tg_ids():
        telegram_ids = db.cursor.execute("SELECT `telegram_id` FROM `users`").fetchall()
        return telegram_ids
