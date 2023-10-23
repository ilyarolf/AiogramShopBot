from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import config
from config import DB_NAME
from models.base import Base

url = f"sqlite+aiosqlite:///{DB_NAME}"

engine = create_async_engine(url, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession)


async def create_db_and_tables():
    async with engine.begin() as conn:
        if Path(config.DB_NAME).exists():
            pass
        else:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

