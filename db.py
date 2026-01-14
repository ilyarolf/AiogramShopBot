from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text, Result, CursorResult
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

import config
from models.base import Base

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
from models.button_media import ButtonMedia
from models.payment import Payment
from models.coupon import Coupon
from models.shipping_option import ShippingOption
from models.review import Review
from models.referral import ReferralBonus

url = f"postgresql+asyncpg://{config.DB_USER}:{config.DB_PASS}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
engine = create_async_engine(url, echo=True)
session_maker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_db_session() -> AsyncSession | Session:
    session = None
    try:
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


async def session_flush(session: AsyncSession | Session) -> None:
    if isinstance(session, AsyncSession):
        await session.flush()
    else:
        session.flush()


async def session_commit(session: AsyncSession | Session) -> None:
    if isinstance(session, AsyncSession):
        await session.commit()
    else:
        session.commit()


async def check_all_tables_exist(session: AsyncSession | Session, schema: str = "public"):
    for table in Base.metadata.tables.values():
        sql_query = text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_name = :table_name
            LIMIT 1;
        """)

        params = {
            "schema": schema,
            "table_name": table.name,
        }

        if isinstance(session, AsyncSession):
            result = await session.execute(sql_query, params)
            if result.scalar() is None:
                return False
        else:
            result = session.execute(sql_query, params)
            if result.scalar() is None:
                return False

    return True


async def create_db_and_tables():
    async with get_db_session() as session:
        if await check_all_tables_exist(session):
            pass
        else:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
