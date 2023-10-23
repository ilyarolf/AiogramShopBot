from aiogram import types
from aiogram.filters import BaseFilter

from config import ADMIN_ID_LIST
from services.user import UserService


class AdminIdFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return message.from_user.id in ADMIN_ID_LIST


class IsUserExistFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return await UserService.is_exist(message.from_user.id)
