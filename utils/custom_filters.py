from aiogram import types
from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import ADMIN_ID_LIST
from db import get_db_session
from models.user import UserDTO
from repositories.user import UserRepository
from services.user import UserService


class AdminIdFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return message.from_user.id in ADMIN_ID_LIST


class IsUserExistFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        async with get_db_session() as session:
            is_exist = await UserService.get(UserDTO(telegram_id=message.from_user.id), session)
            return is_exist is not None


class IsUserBannedFilter(BaseFilter):
    async def __call__(self, message: Message):
        async with get_db_session() as session:
            user = await UserRepository.get_by_tgid(message.from_user.id, session)
            if user:
                return user.is_banned and user.is_admin is False
            else:
                return False
