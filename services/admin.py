from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from callbacks import InventoryManagementCallback, EntityType, \
    MediaManagementCallback
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from repositories.category import CategoryRepository
from repositories.subcategory import SubcategoryRepository
from utils.localizator import Localizator


class AdminService:

    @staticmethod
    async def get_entity_picker(callback_data: InventoryManagementCallback | MediaManagementCallback,
                                session: AsyncSession | Session):
        kb_builder = InlineKeyboardBuilder()
        match callback_data.entity_type:
            case EntityType.CATEGORY:
                entities = await CategoryRepository.get_to_delete(callback_data.page, session)
            case _:
                entities = await SubcategoryRepository.get_to_delete(callback_data.page, session)
        for entity in entities:
            if isinstance(callback_data, InventoryManagementCallback):
                kb_builder.button(text=entity.name, callback_data=InventoryManagementCallback.create(
                    level=3,
                    entity_type=callback_data.entity_type,
                    entity_id=entity.id,
                    page=callback_data.page
                ))
            else:
                kb_builder.button(text=entity.name, callback_data=MediaManagementCallback.create(
                    level=2,
                    entity_type=callback_data.entity_type,
                    entity_id=entity.id,
                    page=callback_data.page
                ))
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  SubcategoryRepository.get_maximum_page_to_delete(session),
                                                  callback_data.get_back_button(0))
        if isinstance(callback_data, InventoryManagementCallback):
            msg_text = Localizator.get_text(BotEntity.ADMIN, "delete_entity").format(
                entity=callback_data.entity_type.get_localized()
            )
        else:
            msg_text = Localizator.get_text(BotEntity.ADMIN, "edit_media").format(
                entity=callback_data.entity_type.get_localized()
            )
        return msg_text, kb_builder
