from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import DB_NAME


from models.user import Base


url = f"sqlite+aiosqlite:///{DB_NAME}"

engine = create_async_engine(url, echo=True)
async_session_maker = async_sessionmaker(engine)


async def create_db_and_tables():
    async with engine.begin() as conn:
        pass
        # await conn.run_sync(Base.metadata.drop_all)
        # await conn.run_sync(Base.metadata.create_all)

