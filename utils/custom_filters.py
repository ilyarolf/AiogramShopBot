from aiogram import types
from aiogram.filters import BaseFilter
from config import ADMIN_ID_LIST
from models.user import UserDTO
from services.user import UserService


class AdminIdFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return message.from_user.id in ADMIN_ID_LIST


class IsUserExistFilter(BaseFilter):

    async def __call__(self, message: types.message):
        is_exist = await UserService.get(UserDTO(telegram_id=message.from_user.id))
        return is_exist is not None
