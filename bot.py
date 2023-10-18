from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares import logging
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from config import TOKEN, WEBHOOK_URL, ADMIN_ID_LIST
from db import db

bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

dp.middleware.setup(LoggingMiddleware())


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    for admin in ADMIN_ID_LIST:
        try:
            await bot.send_message(admin, 'Bot is working')
        except:
            pass


async def on_shutdown(dp):
    logging.warning('Shutting down..')
    db.close()
    # insert code here to run it before shutdown

    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()

    logging.warning('Bye!')