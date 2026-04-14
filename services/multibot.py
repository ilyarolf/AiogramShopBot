import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramUnauthorizedError
from redis.asyncio import Redis

import config


class MultibotService:
    TOKENS_REDIS_KEY = "multibot:tokens"
    SEND_DELAY_SECONDS = 0.3

    @staticmethod
    def _build_redis_client() -> Redis:
        return Redis(host=config.REDIS_HOST, password=config.REDIS_PASSWORD)

    @staticmethod
    async def _get_redis_client(redis_client: Redis | None = None) -> tuple[Redis, bool]:
        if redis_client is not None:
            return redis_client, False
        return MultibotService._build_redis_client(), True

    @staticmethod
    async def _close_redis_client(redis_client: Redis, should_close: bool) -> None:
        if should_close:
            await redis_client.close()

    @staticmethod
    def build_bot(token: str) -> Bot:
        return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    @staticmethod
    async def get_child_tokens(redis_client: Redis | None = None) -> list[str]:
        redis_client, should_close = await MultibotService._get_redis_client(redis_client)
        try:
            tokens = await redis_client.smembers(MultibotService.TOKENS_REDIS_KEY)
            return sorted(
                token.decode() if isinstance(token, bytes) else token
                for token in tokens
            )
        finally:
            await MultibotService._close_redis_client(redis_client, should_close)

    @staticmethod
    async def get_all_tokens_with_main(redis_client: Redis | None = None) -> list[str]:
        tokens = [config.TOKEN]
        if config.MULTIBOT:
            tokens.extend(await MultibotService.get_child_tokens(redis_client))
        return list(dict.fromkeys(tokens))

    @staticmethod
    async def has_token(token: str, redis_client: Redis | None = None) -> bool:
        if token == config.TOKEN:
            return True
        redis_client, should_close = await MultibotService._get_redis_client(redis_client)
        try:
            return bool(await redis_client.sismember(MultibotService.TOKENS_REDIS_KEY, token))
        finally:
            await MultibotService._close_redis_client(redis_client, should_close)

    @staticmethod
    async def add_token(token: str, redis_client: Redis | None = None) -> bool:
        if token == config.TOKEN:
            return False
        redis_client, should_close = await MultibotService._get_redis_client(redis_client)
        try:
            added = await redis_client.sadd(MultibotService.TOKENS_REDIS_KEY, token)
            return bool(added)
        finally:
            await MultibotService._close_redis_client(redis_client, should_close)

    @staticmethod
    async def remove_token(token: str, redis_client: Redis | None = None) -> None:
        if token == config.TOKEN:
            return
        redis_client, should_close = await MultibotService._get_redis_client(redis_client)
        try:
            await redis_client.srem(MultibotService.TOKENS_REDIS_KEY, token)
        finally:
            await MultibotService._close_redis_client(redis_client, should_close)

    @staticmethod
    async def restore_child_bot_webhooks(webhook_url_template: str,
                                         redis_client: Redis | None = None) -> None:
        for token in await MultibotService.get_child_tokens(redis_client):
            bot = MultibotService.build_bot(token)
            try:
                await bot.get_me()
                await bot.set_webhook(webhook_url_template.format(bot_token=token))
            except TelegramUnauthorizedError:
                logging.warning("Removing unauthorized child bot token during startup recovery")
                await MultibotService.remove_token(token, redis_client)
            except Exception as exception:
                logging.error(exception)
            finally:
                await bot.session.close()

    @staticmethod
    async def send_message_to_user(text: str,
                                   telegram_id: int,
                                   reply_markup=None,
                                   redis_client: Redis | None = None) -> int:
        success_count = 0
        tokens = await MultibotService.get_all_tokens_with_main(redis_client)
        for index, token in enumerate(tokens):
            bot = MultibotService.build_bot(token)
            try:
                await bot.send_message(telegram_id, text, reply_markup=reply_markup)
                success_count += 1
            except TelegramUnauthorizedError:
                logging.warning("Removing unauthorized child bot token during send_message_to_user")
                await MultibotService.remove_token(token, redis_client)
            except Exception as exception:
                logging.error(exception)
            finally:
                await bot.session.close()
            if index < len(tokens) - 1:
                await asyncio.sleep(MultibotService.SEND_DELAY_SECONDS)
        return success_count

    @staticmethod
    async def copy_message_to_user(from_chat_id: int,
                                   message_id: int,
                                   telegram_id: int,
                                   redis_client: Redis | None = None) -> tuple[int, bool]:
        success_count = 0
        had_only_forbidden_errors = True
        tokens = await MultibotService.get_all_tokens_with_main(redis_client)
        for index, token in enumerate(tokens):
            bot = MultibotService.build_bot(token)
            try:
                await bot.copy_message(
                    chat_id=telegram_id,
                    from_chat_id=from_chat_id,
                    message_id=message_id
                )
                success_count += 1
                had_only_forbidden_errors = False
            except TelegramForbiddenError as exception:
                logging.error(f"TelegramForbiddenError: {exception.message}")
            except TelegramUnauthorizedError:
                logging.warning("Removing unauthorized child bot token during copy_message_to_user")
                await MultibotService.remove_token(token, redis_client)
                had_only_forbidden_errors = False
            except Exception as exception:
                logging.error(exception)
                had_only_forbidden_errors = False
            finally:
                await bot.session.close()
            if index < len(tokens) - 1:
                await asyncio.sleep(MultibotService.SEND_DELAY_SECONDS)
        return success_count, had_only_forbidden_errors
