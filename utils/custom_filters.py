from aiogram import types
from aiogram.filters import BaseFilter

from config import ADMIN_ID_LIST
from models.user import User


class AdminIdFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return message.from_user.id in ADMIN_ID_LIST


class IsUserExistFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return User.is_exist(message.from_user.id)
