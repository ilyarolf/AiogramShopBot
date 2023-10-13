from aiogram import types
from aiogram.dispatcher.filters import Command

from config import ADMIN_ID_LIST


class AdminIdFilter(Command):
    async def check(self, message: types.message):
        return message.from_id in ADMIN_ID_LIST
