from aiogram import types
from aiogram.filters import BaseFilter

from config import ADMIN_ID_LIST
from services.user import UserService
from db import get_db_session, close_db_session


class AdminIdFilter(BaseFilter):

    async def __call__(self, message: types.message):
        return message.from_user.id in ADMIN_ID_LIST


class IsUserExistFilter(BaseFilter):

    async def __call__(self, message: types.message):
        session = await get_db_session()
        is_exist = UserService.is_exist(message.from_user.id, session)
        await close_db_session(session)
        return await is_exist
