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


    def __get_next_user_id(self)->int:
        last_id = db.cursor.execute("SELECT MAX(user_id) FROM `users`").fetchone()[0]
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
    def is_exist(telegram_id:int) ->bool:
        is_exist = db.cursor.execute('SELECT EXISTS (SELECT * from `users` where `telegram_id` = ?)',
                                        (telegram_id,)).fetchone()[0]
        return bool(is_exist)
    @staticmethod
    def update_username(telegram_id:int, telegram_username:str):
        db.cursor.execute('UPDATE `users` SET `telegram_username`= ? where `telegram_id` = ?',
                                    (telegram_username, telegram_id))
        db.connect.commit()
    @staticmethod
    def get(telegram_id:int):
        user = db.cursor.execute('SELECT * FROM `users` WHERE `telegram_id` = ?', (telegram_id, )).fetchall()[0]
        return user

