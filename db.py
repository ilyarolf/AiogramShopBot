from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import event, Engine, text, create_engine, Result, CursorResult
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

import config
from config import DB_NAME
from models.base import Base

if config.DB_ENCRYPTION:
    # Installing sqlcipher3 on windows has some difficulties,
    # so if you want to test the version with database encryption use Linux.
    from sqlcipher3 import dbapi2 as sqlcipher
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
    url += f"sqlite+pysqlcipher://:{config.DB_PASS}@/data/{DB_NAME}"
    engine = create_engine(url, echo=True, module=sqlcipher)
    session_maker = sessionmaker(engine, expire_on_commit=False)
else:
    url += f"sqlite+aiosqlite:///data/{DB_NAME}"
    engine = create_async_engine(url, echo=True)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

data_folder = Path("data")
if data_folder.exists() is False:
    data_folder.mkdir()


@asynccontextmanager
async def get_db_session() -> AsyncSession | Session:
    session = None
    try:
        if config.DB_ENCRYPTION:
            with session_maker() as sync_session:
                session = sync_session
                yield session
        else:
            async with session_maker() as async_session:
                session = async_session
                yield session
    finally:
        if isinstance(session, AsyncSession):
            await session.close()
        elif isinstance(session, Session):
            session.close()


async def session_execute(stmt, session: AsyncSession | Session) -> Result[Any] | CursorResult[Any]:
    if isinstance(session, AsyncSession):
        query_result = await session.execute(stmt)
        return query_result
    else:
        query_result = session.execute(stmt)
        return query_result


async def session_refresh(session: AsyncSession | Session, instance: object) -> None:
    if isinstance(session, AsyncSession):
        await session.refresh(instance)
    else:
        session.refresh(instance)


async def session_commit(session: AsyncSession | Session) -> None:
    if isinstance(session, AsyncSession):
        await session.commit()
    else:
        session.commit()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async def check_all_tables_exist(session: AsyncSession | Session):
    for table in Base.metadata.tables.values():
        sql_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table.name}';"
        if isinstance(session, AsyncSession):
            result = await session.execute(text(sql_query))
            if result.scalar() is None:
                return False
        else:
            result = session.execute(text(sql_query))
            if result.scalar() is None:
                return False
    return True


async def create_db_and_tables():
    async with get_db_session() as session:
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
