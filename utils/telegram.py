from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

import config


def create_telegram_session() -> AiohttpSession:
    if config.TELEGRAM_PROXY_URL:
        return AiohttpSession(proxy=config.TELEGRAM_PROXY_URL)
    return AiohttpSession()


def create_bot(token: str, session: AiohttpSession | None = None) -> Bot:
    session = session or create_telegram_session()
    return Bot(
        token=token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
