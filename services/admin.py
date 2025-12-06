from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from callbacks import InventoryManagementCallback, EntityType, \
    MediaManagementCallback
from enums.bot_entity import BotEntity
from enums.language import Language
from enums.sort_property import SortProperty
from handlers.common.common import add_pagination_buttons, add_sorting_buttons, get_filters_settings, add_search_button
from repositories.category import CategoryRepository
from repositories.subcategory import SubcategoryRepository
from utils.utils import get_text


class AdminService:

    @staticmethod
    async def get_entity_picker(callback_data: InventoryManagementCallback | MediaManagementCallback | None,
                                session: AsyncSession, state: FSMContext, language: Language):
        kb_builder = InlineKeyboardBuilder()
        state_data = await state.get_data()
        if callback_data is None:
            if state_data.get('callback_prefix') == InventoryManagementCallback.__prefix__:
                callback_object = InventoryManagementCallback
                level = 2
            else:
                callback_object = MediaManagementCallback
                level = 1
            entity_type = EntityType(state_data.get("entity_type"))
            callback_data = callback_object.create(
                level=level,
                entity_type=entity_type
            )
        sort_pairs, filters = await get_filters_settings(state, callback_data)
        match callback_data.entity_type:
            case EntityType.CATEGORY:
                entities = await CategoryRepository.get_to_delete(sort_pairs, filters, callback_data.page, session)
                max_page_method = CategoryRepository.get_maximum_page(filters, session)
            case _:
                entities = await SubcategoryRepository.get_to_delete(sort_pairs, filters, callback_data.page, session)
                max_page_method = SubcategoryRepository.get_maximum_page(None, filters, session)
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
        kb_builder = await add_search_button(kb_builder,
                                             callback_data.entity_type,
                                             callback_data,
                                             filters, language)
        kb_builder = await add_sorting_buttons(kb_builder,
                                               [SortProperty.NAME],
                                               callback_data,
                                               sort_pairs, language)
        if isinstance(callback_data, InventoryManagementCallback):
            msg_text = get_text(language, BotEntity.ADMIN, "delete_entity").format(
                entity=callback_data.entity_type.get_localized(language)
            )
        else:
            msg_text = get_text(language, BotEntity.ADMIN, "edit_media").format(
                entity=callback_data.entity_type.get_localized(language)
            )
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  max_page_method,
                                                  callback_data.get_back_button(language, 0), language)
        return msg_text, kb_builder
