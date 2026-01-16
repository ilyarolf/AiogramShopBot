import asyncio
import logging

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import AnnouncementCallback
from db import session_commit
from enums.announcement_type import AnnouncementType
from enums.bot_entity import BotEntity
from enums.language import Language
from handlers.admin.constants import AdminConstants
from repositories.item import ItemRepository
from repositories.user import UserRepository
from utils.utils import get_text


class AnnouncementService:
    @staticmethod
    async def get_announcement_menu(language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "send_everyone"),
                          callback_data=AnnouncementCallback.create(1))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "restocking"),
                          callback_data=AnnouncementCallback.create(2, AnnouncementType.RESTOCKING))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "stock"),
                          callback_data=AnnouncementCallback.create(2, AnnouncementType.CURRENT_STOCK))
        kb_builder.row(AdminConstants.back_to_main_button(language))
        kb_builder.adjust(1)
        return get_text(language, BotEntity.ADMIN, "announcements"), kb_builder

    @staticmethod
    async def send_announcement(callback: CallbackQuery,
                                callback_data: AnnouncementCallback,
                                session: AsyncSession,
                                language: Language):
        await callback.message.edit_reply_markup()
        active_users = await UserRepository.get_active(session)
        all_users_count = await UserRepository.get_all_count(session)
        counter = 0
        for user in active_users:
            try:
                await callback.message.copy_to(user.telegram_id, reply_markup=None)
                counter += 1
                await asyncio.sleep(1.5)
            except TelegramForbiddenError as e:
                logging.error(f"TelegramForbiddenError: {e.message}")
                if "user is deactivated" in e.message.lower():
                    user.can_receive_messages = False
                elif "bot was blocked by the user" in e.message.lower():
                    user.can_receive_messages = False
                    await UserRepository.update(user, session)
            except Exception as e:
                logging.error(e)
            finally:
                if callback_data.announcement_type == AnnouncementType.RESTOCKING:
                    await ItemRepository.set_not_new(session)
                await session_commit(session)
        return get_text(language, BotEntity.ADMIN, "sending_result").format(counter=counter,
                                                                            len=len(active_users),
                                                                            users_count=all_users_count)
