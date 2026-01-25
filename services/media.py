from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import MediaManagementCallback, AdminMenuCallback
from db import session_commit, get_db_session
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from handlers.admin.constants import MediaManagementStates
from models.category import CategoryDTO
from repositories.button_media import ButtonMediaRepository
from repositories.category import CategoryRepository
from repositories.subcategory import SubcategoryRepository
from services.notification import NotificationService
from utils.utils import get_text, get_bot_photo_id


class MediaService:
    @staticmethod
    async def get_menu(callback_data: MediaManagementCallback, language: Language):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "edit_media").format(
                entity=EntityType.CATEGORY.get_localized(language)
            ),
            callback_data=MediaManagementCallback.create(
                level=callback_data.level + 1,
                entity_type=EntityType.CATEGORY
            )
        )
        kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "edit_media").format(
                entity=EntityType.SUBCATEGORY.get_localized(language)
            ),
            callback_data=MediaManagementCallback.create(
                level=callback_data.level + 1,
                entity_type=EntityType.SUBCATEGORY
            )
        )
        buttons = [button for button in KeyboardButton]
        buttons.remove(KeyboardButton.ADMIN_MENU)
        for button in buttons:
            kb_builder.button(
                text=get_text(language, BotEntity.ADMIN, "edit_media").format(
                    entity=get_text(language, BotEntity.USER, button.value.lower())
                ),
                callback_data=MediaManagementCallback.create(
                    level=callback_data.level + 2,
                    keyboard_button=button
                )
            )
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=AdminMenuCallback.create(0)
        )
        kb_builder.adjust(1)
        return get_text(language, BotEntity.ADMIN, "media_management"), kb_builder

    @staticmethod
    async def set_entity_media_edit(callback_data: MediaManagementCallback,
                                    state: FSMContext,
                                    session: AsyncSession,
                                    language: Language) -> tuple[str, InlineKeyboardBuilder]:
        await state.update_data(
            entity_type=callback_data.entity_type,
            entity_id=callback_data.entity_id,
            keyboard_button=callback_data.keyboard_button.value if callback_data.keyboard_button else None)
        await state.set_state(MediaManagementStates.media)
        if callback_data.entity_type == EntityType.CATEGORY:
            entity = await CategoryRepository.get_by_id(callback_data.entity_id, session)
            entity_type_localized = callback_data.entity_type.get_localized(language)
        elif callback_data.entity_type == EntityType.SUBCATEGORY:
            entity = await SubcategoryRepository.get_by_id(callback_data.entity_id, session)
            entity_type_localized = callback_data.entity_type.get_localized(language)
        else:
            entity = CategoryDTO(name=get_text(language, BotEntity.USER,
                                               callback_data.keyboard_button.value.lower()))
            entity_type_localized = callback_data.keyboard_button.get_localized(language)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "cancel"),
            callback_data=MediaManagementCallback.create(0)
        )
        return get_text(language, BotEntity.ADMIN, "edit_media_request").format(
            entity=entity_type_localized,
            entity_name=entity.name
        ), kb_builder

    @staticmethod
    async def receive_new_entity_media(message: Message,
                                       state: FSMContext,
                                       session: AsyncSession,
                                       language: Language):
        state_data = await state.get_data()
        kb_builder = InlineKeyboardBuilder()
        await NotificationService.edit_reply_markup(message.bot,
                                                    state_data['chat_id'],
                                                    state_data['msg_id'],
                                                    kb_builder.as_markup())
        if message.photo:
            file_id = message.photo[-1].file_id
            prefix = "0"
        elif message.video:
            file_id = message.video.file_id
            prefix = "1"
        else:
            file_id = message.animation.file_id
            prefix = "2"
        state_data = await state.get_data()
        media = f"{prefix}{file_id}"
        entity_type = state_data.get("entity_type")
        if entity_type is None:
            entity_type = KeyboardButton(state_data.get("keyboard_button"))
            button_media_dto = await ButtonMediaRepository.get_by_button(entity_type, session)
            button_media_dto.media_id = media
            await ButtonMediaRepository.update(button_media_dto, session)
            entity_dto = CategoryDTO(name=get_text(language, BotEntity.USER, entity_type.value.lower()))
        else:
            entity_type = EntityType(entity_type)
            if entity_type == EntityType.CATEGORY:
                entity_dto = await CategoryRepository.get_by_id(state_data['entity_id'], session)
                entity_dto.media_id = media
                await CategoryRepository.update(entity_dto, session)
            else:
                entity_dto = await SubcategoryRepository.get_by_id(state_data['entity_id'], session)
                entity_dto.media_id = media
                await SubcategoryRepository.update(entity_dto, session)
        await session_commit(session)
        await state.clear()
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=MediaManagementCallback.create(0)
        )
        return get_text(language, BotEntity.ADMIN, "entity_media_successfully_edited").format(
            entity=entity_type.get_localized(language),
            entity_name=entity_dto.name
        ), kb_builder

    @staticmethod
    def convert_to_media(media_id: str, caption: str) -> InputMediaPhoto | InputMediaVideo | InputMediaAnimation:
        category_media_type = media_id[0]
        category_media_id = media_id[1:]
        if category_media_type == "0":
            media = InputMediaPhoto(media=category_media_id, caption=caption)
        elif category_media_type == "1":
            media = InputMediaVideo(media=category_media_id, caption=caption)
        else:
            media = InputMediaAnimation(media=category_media_id, caption=caption)
        return media

    @staticmethod
    async def update_inaccessible_media(bot: Bot):
        bot_photo_id = f"0{get_bot_photo_id()}"
        async with get_db_session() as session:
            unique_file_ids = await ButtonMediaRepository.get_all_file_ids(session)
            inaccessible_media_list = []
            for unique_id in unique_file_ids:
                parsed_unique_id = unique_id
                if parsed_unique_id[0] in ["0", "1", "2"]:
                    parsed_unique_id = unique_id[1:]
                try:
                    await bot.get_file(parsed_unique_id)
                except TelegramBadRequest as _:
                    inaccessible_media_list.append(unique_id)
            for media_id in inaccessible_media_list:
                await ButtonMediaRepository.update_media_id(media_id, bot_photo_id, session)
            await session_commit(session)
