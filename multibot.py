import logging
import sys
from typing import Any, Dict
from aiohttp import web
import config
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.token import TokenValidationError, validate_token
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    TokenBasedRequestHandler,
    setup_application,
)
from db import create_db_and_tables
from utils.custom_filters import AdminIdFilter

main_router_multibot = Router()

BASE_URL = config.WEBHOOK_HOST
MAIN_BOT_TOKEN = config.TOKEN

WEB_SERVER_HOST = config.WEBAPP_HOST
WEB_SERVER_PORT = config.WEBAPP_PORT
MAIN_BOT_PATH = "/webhook/main"
OTHER_BOTS_PATH = "/webhook/bot/{bot_token}"

OTHER_BOTS_URL = f"{BASE_URL}{OTHER_BOTS_PATH}"


def is_bot_token(value: str) -> bool | Dict[str, Any]:
    try:
        validate_token(value)
    except TokenValidationError:
        return False
    return True


@main_router_multibot.message(AdminIdFilter(), Command("add", magic=F.args.func(is_bot_token)))
async def command_add_bot(message: Message, command: CommandObject, bot: Bot) -> Any:
    new_bot = Bot(token=command.args, session=bot.session)
    try:
        bot_user = await new_bot.get_me()
    except TelegramUnauthorizedError:
        return message.answer("Invalid token")
    await new_bot.delete_webhook(drop_pending_updates=True)
    await new_bot.set_webhook(OTHER_BOTS_URL.format(bot_token=command.args))
    return await message.answer(f"Bot @{bot_user.username} successful added")


async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await bot.set_webhook(f"{BASE_URL}{MAIN_BOT_PATH}")
    await create_db_and_tables()
    for admin in config.ADMIN_ID_LIST:
        try:
            await bot.send_message(admin, 'Bot is working')
        except Exception as e:
            logging.warning(e)


def main(main_router):
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    session = AiohttpSession()
    bot_settings = {"session": session, "parse_mode": ParseMode.HTML}
    bot = Bot(token=MAIN_BOT_TOKEN, **bot_settings)
    storage = MemoryStorage()

    main_dispatcher = Dispatcher(storage=storage)
    main_dispatcher.include_router(main_router_multibot)
    main_dispatcher.startup.register(on_startup)

    multibot_dispatcher = Dispatcher(storage=storage)
    multibot_dispatcher.include_router(main_router)

    app = web.Application()
    SimpleRequestHandler(dispatcher=main_dispatcher, bot=bot).register(app, path=MAIN_BOT_PATH)
    TokenBasedRequestHandler(
        dispatcher=multibot_dispatcher,
        bot_settings=bot_settings,
    ).register(app, path=OTHER_BOTS_PATH)

    setup_application(app, main_dispatcher, bot=bot)
    setup_application(app, multibot_dispatcher)

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

