from pathlib import Path

from sqlalchemy import event, Engine, create_engine, inspect
from sqlalchemy.orm import sessionmaker

from config import DB_NAME, DB_PASS
from models.base import Base
from sqlcipher3 import dbapi2 as sqlcipher3

# import sqlcipher3
"""
Imports of these models are needed to correctly create tables in the database.
For more information see https://stackoverflow.com/questions/7478403/sqlalchemy-classes-across-files
"""
from models.item import Item
from models.user import User
from models.buy import Buy
from models.buyItem import BuyItem
from models.category import Category
from models.subcategory import Subcategory

url = f"sqlite+pysqlcipher://:{DB_PASS}@/{DB_NAME}"

engine = create_engine(url, echo=True, module=sqlcipher3)
session_maker = sessionmaker(engine)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def check_all_tables_exist(db_engine):
    insp = inspect(db_engine)
    for table in Base.metadata.tables.values():
        if not insp.has_table(table.name):
            return False
    return True


async def create_db_and_tables():
    if check_all_tables_exist(engine):
        pass
    else:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
