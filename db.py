from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import config
from config import DB_NAME
from models.base import Base
"""
Imports of these models are needed to correctly create tables in the database.
For more information see https://stackoverflow.com/questions/7478403/sqlalchemy-classes-across-files
"""
from models.item import Item
from models.user import User
from models.buy import Buy
from models.buyItem import BuyItem
url = f"sqlite+aiosqlite:///{DB_NAME}"

engine = create_async_engine(url, echo=True)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession)


async def create_db_and_tables():
    async with engine.begin() as conn:
        if Path(config.DB_NAME).exists():
            pass
        else:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

