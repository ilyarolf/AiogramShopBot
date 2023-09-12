import sqlite3

from config import DB_PASS, DB_NAME


class Database:
    def __init__(self, db_name=DB_NAME) -> None:
        """Инициализация класса, подключение к БД"""
        self.connect = sqlite3.connect(db_name)
        self.cursor = self.connect.cursor()
        self.cursor.execute(f"PRAGMA key={DB_PASS}")

    def close(self):
        self.connect.close()