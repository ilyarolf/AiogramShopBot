import asyncio
import logging

import config
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
from services.item import ItemService
from services.notification import NotificationService
from services.multibot import MultibotService
from utils.utils import get_text


class AnnouncementService:
    @staticmethod
    async def _send_generated_announcement_to_user(callback: CallbackQuery,
                                                   telegram_id: int,
                                                   messages: list[str]) -> tuple[bool, bool]:
        if config.MULTIBOT:
            had_only_forbidden_errors = False
            for message_text in messages:
                sent_count, chunk_had_only_forbidden_errors = await MultibotService.send_message_to_user_verbose(
                    text=message_text,
                    telegram_id=telegram_id
                )
                if sent_count == 0:
                    return False, chunk_had_only_forbidden_errors
                had_only_forbidden_errors = had_only_forbidden_errors or chunk_had_only_forbidden_errors
            return True, had_only_forbidden_errors
        try:
            for message_text in messages:
                await callback.bot.send_message(telegram_id, message_text)
            return True, False
        except TelegramForbiddenError as exception:
            logging.error(f"TelegramForbiddenError: {exception.message}")
            return False, True
        except Exception as exception:
            logging.error(exception)
            return False, False

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
        message_template = get_text(language, BotEntity.ADMIN, "sending_result")
        message = await callback.message.answer(
            text=message_template.format(
                counter=counter,
                len=len(active_users),
                users_count=all_users_count,
                status=get_text(language, BotEntity.ADMIN, "in_progress")
            )
        )
        generated_messages = None
        is_generated_announcement = callback_data.announcement_type in (
            AnnouncementType.RESTOCKING,
            AnnouncementType.CURRENT_STOCK
        )
        if is_generated_announcement:
            generated_messages = await ItemService.create_announcement_message(
                callback_data.announcement_type,
                session,
                language
            )
        for user in active_users:
            try:
                if is_generated_announcement:
                    is_sent, had_only_forbidden_errors = await AnnouncementService._send_generated_announcement_to_user(
                        callback,
                        user.telegram_id,
                        generated_messages
                    )
                    if is_sent:
                        counter += 1
                    elif had_only_forbidden_errors:
                        user.can_receive_messages = False
                        await UserRepository.update(user, session)
                elif config.MULTIBOT:
                    sent_count, had_only_forbidden_errors = await MultibotService.copy_message_to_user(
                        from_chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id,
                        telegram_id=user.telegram_id
                    )
                    if sent_count > 0:
                        counter += 1
                    elif had_only_forbidden_errors:
                        user.can_receive_messages = False
                        await UserRepository.update(user, session)
                else:
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
                if counter % 5 == 0:
                    msg = message_template.format(
                        counter=counter,
                        len=len(active_users),
                        users_count=all_users_count,
                        status=get_text(language, BotEntity.ADMIN, "in_progress")
                    )
                    await NotificationService.edit_message(message=msg,
                                                           source_message_id=message.message_id,
                                                           chat_id=message.chat.id)
                await session_commit(session)
        if callback_data.announcement_type == AnnouncementType.RESTOCKING:
            await ItemRepository.set_not_new(session)
            await session_commit(session)
        await NotificationService.edit_message(
            message=message_template.format(
                counter=counter,
                len=len(active_users),
                users_count=all_users_count,
                status=get_text(language, BotEntity.ADMIN, "finished")
            ),
            source_message_id=message.message_id,
            chat_id=message.chat.id)
