import asyncio
import logging

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import AdminAnnouncementCallback, AnnouncementType
from handlers.admin.constants import AdminConstants
from repositories.item import ItemRepository
from repositories.user import UserRepository
from utils.localizator import Localizator, BotEntity


class AdminService:

    @staticmethod
    async def get_announcement_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "send_everyone"),
                          callback_data=AdminAnnouncementCallback.create(level=1))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "restocking"),
                          callback_data=AdminAnnouncementCallback.create(level=2))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "stock"),
                          callback_data=AdminAnnouncementCallback.create(level=3))
        kb_builder.row(AdminConstants.back_to_main_button)
        kb_builder.adjust(1)
        return Localizator.get_text(BotEntity.ADMIN, "announcements"), kb_builder

    @staticmethod
    async def send_announcement(callback: CallbackQuery):
        unpacked_cb = AdminAnnouncementCallback.unpack(callback.data)
        await callback.message.edit_reply_markup()
        active_users = await UserRepository.get_active()
        all_users_count = await UserRepository.get_all_count()
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
                    await UserRepository.update(user)
            except Exception as e:
                logging.error(e)
            finally:
                if unpacked_cb.announcement_type == AnnouncementType.RESTOCKING:
                    await ItemRepository.set_not_new()
        return Localizator.get_text(BotEntity.ADMIN, "sending_result").format(counter=counter,
                                                                                      len=len(active_users),
                                                                                      users_count=all_users_count)
