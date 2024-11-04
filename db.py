from pathlib import Path
from typing import Union

from sqlalchemy import event, Engine, text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

import config
from config import DB_NAME
from models.base import Base

if config.DB_ENCRYPTION:
    pass
    # from sqlcipher import dbapi2 as sqlcipher
"""
Imports of these models are needed to correctly create tables in the database.
For more information see https://stackoverflow.com/questions/7478403/sqlalchemy-classes-across-files
"""
from models.item import Item
from models.cart import Cart
from models.cartItem import CartItem
from models.user import User
from models.buy import Buy
from models.buyItem import BuyItem
from models.category import Category
from models.subcategory import Subcategory
from models.deposit import Deposit

url = ""
engine = None
session_maker = None
if config.DB_ENCRYPTION:
    # url += f"sqlite+pysqlcipher://:{config.DB_PASS}@/data/{DB_NAME}"
    url += f"sqlite+pysqlite:///{DB_NAME}"
    # engine = create_engine(url, echo=True, module=sqlcipher)
    engine = create_engine(url, echo=True)
    session_maker = sessionmaker(engine)
else:
    url += f"sqlite+aiosqlite:///data/{DB_NAME}"
    engine = create_async_engine(url, echo=True)
    session_maker = async_sessionmaker(engine, class_=AsyncSession)

data_folder = Path("data")
if data_folder.exists() is False:
    data_folder.mkdir()


async def execute_stmt(stmt, session: Union[AsyncSession, Session]):
    if isinstance(session, AsyncSession):
        query_result = await session.execute(stmt)
        return query_result
    else:
        query_result = session.execute(stmt)
        return query_result


async def get_db_session() -> Union[AsyncSession, Session]:
    if config.DB_ENCRYPTION:
        with session_maker() as sync_session:
            return sync_session
    else:
        async with session_maker() as async_session:
            return async_session


async def close_db_session(session: Union[AsyncSession, Session]) -> None:
    if isinstance(session, AsyncSession):
        await session.close()
    else:
        session.close()


async def session_commit(session: Union[AsyncSession, Session]) -> None:
    if isinstance(session, AsyncSession):
        await session.commit()
    else:
        session.commit()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def check_all_tables_exist(session: Union[AsyncSession, Session]):
    for table in Base.metadata.tables.values():
        sql_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table.name}';"
        if isinstance(session, AsyncSession):
            result = await session.execute(text(sql_query))
            if result.scalar() is None:
                await close_db_session(session)
                return False
        else:
            result = session.execute(text(sql_query))
            if result.scalar() is None:
                await close_db_session(session)
                return False
    await close_db_session(session)
    return True


async def create_db_and_tables():
    session = await get_db_session()
    if await check_all_tables_exist(session):
        pass
    else:
        if isinstance(session, AsyncSession):
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
        else:
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
