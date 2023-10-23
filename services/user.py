from sqlalchemy import exists
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_async_session
from models.user import User


class UserService:
    @staticmethod
    async def is_exist(telegram_id: int) -> bool:
        async with get_async_session() as session:
            result = await session.execute(exists().where(User.telegram_id == telegram_id))
            return result


