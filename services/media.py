from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, InputMediaAnimation
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import MediaManagementCallback, AdminMenuCallback
from db import session_commit
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from enums.keyboardbutton import KeyboardButton
from handlers.admin.constants import MediaManagementStates
from models.category import CategoryDTO
from repositories.button_media import ButtonMediaRepository
from repositories.category import CategoryRepository
from repositories.subcategory import SubcategoryRepository
from services.notification import NotificationService
from utils.localizator import Localizator


class MediaService:
    @staticmethod
    async def get_menu(callback_data: MediaManagementCallback):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=Localizator.get_text(BotEntity.ADMIN, "edit_media").format(
                entity=EntityType.CATEGORY.get_localized()
            ),
            callback_data=MediaManagementCallback.create(
                level=callback_data.level + 1,
                entity_type=EntityType.CATEGORY
            )
        )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.ADMIN, "edit_media").format(
                entity=EntityType.SUBCATEGORY.get_localized()
            ),
            callback_data=MediaManagementCallback.create(
                level=callback_data.level + 1,
                entity_type=EntityType.SUBCATEGORY
            )
        )
        for button in KeyboardButton:
            kb_builder.button(
                text=Localizator.get_text(BotEntity.ADMIN, "edit_media").format(
                    entity=Localizator.get_text(BotEntity.USER, button.value.lower())
                ),
                callback_data=MediaManagementCallback.create(
                    level=callback_data.level + 2,
                    keyboard_button=button
                )
            )
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "back_button"),
            callback_data=AdminMenuCallback.create(0)
        )
        kb_builder.adjust(1)
        return Localizator.get_text(BotEntity.ADMIN, "media_management"), kb_builder

    @staticmethod
    async def set_entity_media_edit(callback_data: MediaManagementCallback,
                                    state: FSMContext,
                                    session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        await state.update_data(entity_type=callback_data.entity_type,
                                entity_id=callback_data.entity_id,
                                keyboard_button=callback_data.keyboard_button.value)
        await state.set_state(MediaManagementStates.media)
        if callback_data.entity_type == EntityType.CATEGORY:
            entity = await CategoryRepository.get_by_id(callback_data.entity_id, session)
            entity_type_localized = callback_data.entity_type.get_localized()
        elif callback_data.entity_type == EntityType.SUBCATEGORY:
            entity = await SubcategoryRepository.get_by_id(callback_data.entity_id, session)
            entity_type_localized = callback_data.entity_type.get_localized()
        else:
            entity = CategoryDTO(name=Localizator.get_text(BotEntity.USER,
                                                           callback_data.keyboard_button.value.lower()))
            entity_type_localized = callback_data.keyboard_button.get_localized()
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "cancel"),
            callback_data=MediaManagementCallback.create(0)
        )
        return Localizator.get_text(BotEntity.ADMIN, "edit_media_request").format(
            entity=entity_type_localized,
            entity_name=entity.name
        ), kb_builder

    @staticmethod
    async def receive_new_entity_media(message: Message, state: FSMContext, session: AsyncSession):
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
            entity_dto = CategoryDTO(name=Localizator.get_text(BotEntity.USER, entity_type.value.lower()))
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
            text=Localizator.get_text(BotEntity.COMMON, "back_button"),
            callback_data=MediaManagementCallback.create(0)
        )
        return Localizator.get_text(BotEntity.ADMIN, "entity_media_successfully_edited").format(
            entity=entity_type.get_localized(),
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
