import sqlite3

from config import DB_PASS, DB_NAME


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}

class Database:
    def __init__(self, db_name=DB_NAME) -> None:
        """Инициализация класса, подключение к БД"""
        self.connect = sqlite3.connect(db_name)
        self.connect.row_factory = dict_factory
        self.cursor = self.connect.cursor()
        self.cursor.execute(f"PRAGMA key={DB_PASS}")

    def close(self):
        self.connect.close()

db = Database()
