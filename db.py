import pathlib

import config

if config.DB_ENCRYPTION is True:
    from pysqlcipher3 import dbapi2 as sqlite3
else:
    import sqlite3

from config import DB_PASS, DB_NAME


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


class Database:
    def __init__(self, db_name=DB_NAME) -> None:
        if pathlib.Path(db_name).exists() is False:
            connect = sqlite3.connect(db_name)
            cursor = connect.cursor()
            with open("items_clean_dump.sql", "r") as sql_clean_dump:
                print(f"Database {db_name} created successfully!")
                cursor.executescript(sql_clean_dump.read())
        self.connect = sqlite3.connect(db_name)
        self.connect.row_factory = dict_factory
        self.cursor = self.connect.cursor()
        if config.DB_ENCRYPTION is True:
            self.cursor.execute(f"PRAGMA key={DB_PASS}")

    def close(self):
        self.connect.close()


db = Database()
