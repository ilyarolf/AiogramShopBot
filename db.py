from pathlib import Path

from sqlalchemy import event, Engine, create_engine
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

url = f"sqlite+pysqlcipher://:{DB_PASS}@/{DB_NAME}?cipher=aes-256-cfb&kdf_iter=64000"

engine = create_engine(url, echo=True, module=sqlcipher3)
session_maker = sessionmaker(engine)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def create_db_and_tables():
    # TODO("Doesn't work like I need")
    if Path(DB_NAME).exists():
        pass
    else:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
