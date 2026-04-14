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
from enums.bot_entity import BotEntity
from enums.language import Language
from services.multibot import MultibotService
from utils.custom_filters import AdminIdFilter
from utils.utils import get_text

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


@main_router_multibot.message(AdminIdFilter(), Command("add"))
async def command_add_bot(message: Message, command: CommandObject, bot: Bot) -> Any:
    if not command.args or not is_bot_token(command.args):
        return await message.answer(get_text(Language.EN, BotEntity.ADMIN, "multibot_invalid_token"))
    if command.args == config.TOKEN:
        return await message.answer(get_text(Language.EN, BotEntity.ADMIN, "multibot_main_token_not_allowed"))
    if await MultibotService.has_token(command.args):
        return await message.answer(get_text(Language.EN, BotEntity.ADMIN, "multibot_bot_already_added"))

    new_bot = Bot(token=command.args, session=bot.session)
    try:
        bot_user = await new_bot.get_me()
    except TelegramUnauthorizedError:
        return await message.answer(get_text(Language.EN, BotEntity.ADMIN, "multibot_invalid_token"))
    await new_bot.delete_webhook(drop_pending_updates=True)
    await new_bot.set_webhook(OTHER_BOTS_URL.format(bot_token=command.args))
    await MultibotService.add_token(command.args)
    return await message.answer(
        get_text(Language.EN, BotEntity.ADMIN, "multibot_bot_added").format(
            bot_username=bot_user.username
        )
    )


async def on_startup(dispatcher: Dispatcher, bot: Bot):
    await bot.set_webhook(f"{BASE_URL}{MAIN_BOT_PATH}")
    await create_db_and_tables()
    await MultibotService.restore_child_bot_webhooks(OTHER_BOTS_URL)
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

