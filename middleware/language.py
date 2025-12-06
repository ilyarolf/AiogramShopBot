from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from db import get_db_session
from enums.language import Language
from repositories.user import UserRepository


class I18nMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Awaitable[Any]:
        async with get_db_session() as session:
            user_dto = await UserRepository.get_by_tgid(event.from_user.id, session)
            if user_dto:
                data["language"] = user_dto.language
            else:
                language = Language.from_locale(event.from_user.language_code)
                data["language"] = language
            return await handler(event, data)
