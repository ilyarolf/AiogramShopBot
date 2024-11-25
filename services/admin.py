import asyncio
import logging
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import AdminAnnouncementCallback, AnnouncementType, AdminInventoryManagementCallback, EntityType, AddType
from handlers.admin.constants import AdminConstants
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.category import CategoryService
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

    @staticmethod
    async def get_inventory_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items"),
                          callback_data=AdminInventoryManagementCallback.create(level=1, entity_type=EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "delete_category"),
                          callback_data=AdminInventoryManagementCallback.create(level=2,
                                                                                entity_type=EntityType.CATEGORY))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "delete_subcategory"),
                          callback_data=AdminInventoryManagementCallback.create(level=2,
                                                                                entity_type=EntityType.CATEGORY))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "inventory_management"), kb_builder

    @staticmethod
    async def get_add_items_type() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_json"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.JSON, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_txt"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.TXT, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_menu"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.MENU, EntityType.ITEM))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "add_items_msg"), kb_builder

    @staticmethod
    async def get_delete_entity_menu(callback: CallbackQuery):
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        match unpacked_cb.entity_type:
            case EntityType.CATEGORY:
                categories = await CategoryRepository.get_to_delete(unpacked_cb.page)
                [kb_builder.button(text=category.name, callback_data=AdminInventoryManagementCallback.create(
                    level=3,
                    entity_type=unpacked_cb.entity_type,
                    entity_id=category.id
                )) for category in categories]
                return Localizator.get_text(BotEntity.ADMIN, "delete_category"), kb_builder
            case EntityType.SUBCATEGORY:
                subcategories = await SubcategoryRepository.get_to_delete(unpacked_cb.page)
                [kb_builder.button(text=subcategory.name, callback_data=AdminInventoryManagementCallback.create(
                    level=3,
                    entity_type=unpacked_cb.entity_type,
                    entity_id=subcategory.id
                )) for subcategory in subcategories]
                return Localizator.get_text(BotEntity.ADMIN, "delete_subcategory"), kb_builder
