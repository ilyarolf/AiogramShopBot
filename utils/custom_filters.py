from aiogram import types
from aiogram.filters import BaseFilter
from aiogram.types import Message

import config
from db import get_db_session
from models.user import UserDTO
from services.user import UserService


class AdminIdFilter(BaseFilter):

    async def __call__(self, message: types.Message):
        return message.from_user.id in config.ADMIN_ID_LIST


class IsUserExistFilter(BaseFilter):
    """
    Filter that checks if user exists and is not banned.
    Blocks banned users from accessing protected routes (shopping, cart, etc.).
    Admins with EXEMPT_ADMINS_FROM_BAN=true can bypass ban.

    If user is banned, shows informative message with unban instructions.
    """
    async def __call__(self, message: Message) -> bool:
        async with get_db_session() as session:
            user = await UserService.get(UserDTO(telegram_id=message.from_user.id), session)

            if user is None:
                return False

            # Check if user is banned (unless admin is exempt)
            if user.is_blocked:
                is_admin = message.from_user.id in config.ADMIN_ID_LIST
                admin_exempt = is_admin and config.EXEMPT_ADMINS_FROM_BAN

                if not admin_exempt:
                    # User is banned - show informative message
                    from utils.localizator import Localizator
                    from enums.bot_entity import BotEntity
                    from repositories.user_strike import UserStrikeRepository

                    # Get actual strike count from DB
                    strikes = await UserStrikeRepository.get_by_user_id(user.id, session)
                    strike_count = len(strikes)

                    ban_message = Localizator.get_text(BotEntity.USER, "account_banned_access_denied").format(
                        strike_count=strike_count,
                        unban_amount=config.UNBAN_TOP_UP_AMOUNT,
                        currency_sym=Localizator.get_currency_symbol()
                    )

                    await message.answer(ban_message)
                    return False

            return True


class IsUserExistFilterIncludingBanned(BaseFilter):
    """
    Filter that checks if user exists, but allows banned users.
    Used for protected routes that banned users should still access:
    - My Profile (for wallet top-up)
    - Support
    - FAQ/Terms
    """
    async def __call__(self, message: Message) -> bool:
        async with get_db_session() as session:
            user = await UserService.get(UserDTO(telegram_id=message.from_user.id), session)
            return user is not None
