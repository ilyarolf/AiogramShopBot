from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from callbacks import InventoryManagementCallback
from db import session_commit
from enums.add_type import AddType
from enums.bot_entity import BotEntity
from enums.entity_type import EntityType
from handlers.admin.constants import AdminConstants, InventoryManagementStates
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from services.notification import NotificationService
from utils.localizator import Localizator


class InventoryManagementService:

    @staticmethod
    async def get_inventory_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items"),
                          callback_data=InventoryManagementCallback.create(level=1, entity_type=EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "delete_entity").format(
            entity=EntityType.CATEGORY.get_localized()
        ),
            callback_data=InventoryManagementCallback.create(level=2,
                                                             entity_type=EntityType.CATEGORY))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "delete_entity").format(
            entity=EntityType.SUBCATEGORY.get_localized()
        ),
            callback_data=InventoryManagementCallback.create(level=2,
                                                             entity_type=EntityType.SUBCATEGORY))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "inventory_management"), kb_builder

    @staticmethod
    async def get_add_items_type(callback_data: InventoryManagementCallback) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_json"),
                          callback_data=InventoryManagementCallback.create(1, AddType.JSON, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_txt"),
                          callback_data=InventoryManagementCallback.create(1, AddType.TXT, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_menu"),
                          callback_data=InventoryManagementCallback.create(1, AddType.MENU, EntityType.ITEM))
        kb_builder.adjust(1)
        kb_builder.row(callback_data.get_back_button())
        return Localizator.get_text(BotEntity.ADMIN, "add_items_msg"), kb_builder

    @staticmethod
    async def get_add_item_msg(callback_data: InventoryManagementCallback, state: FSMContext):
        kb_markup = InlineKeyboardBuilder()
        kb_markup.button(text=Localizator.get_text(BotEntity.COMMON, 'cancel'),
                         callback_data=InventoryManagementCallback.create(1))
        await state.update_data(add_type=callback_data.add_type.value)
        await state.set_state(InventoryManagementStates.document)
        match callback_data.add_type:
            case AddType.JSON:
                return Localizator.get_text(BotEntity.ADMIN, "add_items_json_msg"), kb_markup
            case AddType.TXT:
                return Localizator.get_text(BotEntity.ADMIN, "add_items_txt_msg"), kb_markup
            case AddType.MENU:
                await state.set_state(InventoryManagementStates.category)
                return Localizator.get_text(BotEntity.ADMIN, "add_items_category"), kb_markup

    @staticmethod
    async def delete_confirmation(callback_data: InventoryManagementCallback,
                                  session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        callback_data.confirmation = True
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=callback_data)
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=InventoryManagementCallback.create(0))
        match callback_data.entity_type:
            case EntityType.CATEGORY:
                category = await CategoryRepository.get_by_id(callback_data.entity_id, session)
                return Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
                    entity=callback_data.entity_type.name.capitalize(),
                    entity_name=category.name
                ), kb_builder
            case EntityType.SUBCATEGORY:
                subcategory = await SubcategoryRepository.get_by_id(callback_data.entity_id, session)
                return Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
                    entity=callback_data.entity_type.name.capitalize(),
                    entity_name=subcategory.name
                ), kb_builder

    @staticmethod
    async def delete_entity(callback_data: InventoryManagementCallback,
                            session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(AdminConstants.back_to_main_button)
        match callback_data.entity_type:
            case EntityType.CATEGORY:
                category = await CategoryRepository.get_by_id(callback_data.entity_id, session)
                await ItemRepository.delete_unsold_by_category_id(callback_data.entity_id, session)
                await session_commit(session)
                return Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
                    entity_name=category.name,
                    entity_to_delete=callback_data.entity_type.name.capitalize()), kb_builder
            case EntityType.SUBCATEGORY:
                subcategory = await SubcategoryRepository.get_by_id(callback_data.entity_id, session)
                await ItemRepository.delete_unsold_by_subcategory_id(callback_data.entity_id, session)
                await session_commit(session)
                return Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
                    entity_name=subcategory.name,
                    entity_to_delete=callback_data.entity_type.name.capitalize()), kb_builder

    @staticmethod
    async def add_item_menu(message: Message,
                            state: FSMContext,
                            session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        current_state = await state.get_state()
        state_data = await state.get_data()
        await NotificationService.edit_reply_markup(message.bot,
                                                    state_data['chat_id'],
                                                    state_data['msg_id'])
        kb_builder = InlineKeyboardBuilder()
        cancel_button = InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                                             callback_data=InventoryManagementCallback.create(1).pack())
        if current_state == InventoryManagementStates.category:
            await state.update_data(category_name=message.html_text)
            await state.set_state(InventoryManagementStates.subcategory)
            msg = Localizator.get_text(BotEntity.ADMIN, "add_items_subcategory")
        elif current_state == InventoryManagementStates.subcategory:
            await state.update_data(subcategory_name=message.html_text)
            await state.set_state(InventoryManagementStates.description)
            msg = Localizator.get_text(BotEntity.ADMIN, "add_items_description")
        elif current_state == InventoryManagementStates.description:
            await state.update_data(description=message.html_text)
            await state.set_state(InventoryManagementStates.private_data)
            msg = Localizator.get_text(BotEntity.ADMIN, "add_items_private_data")
        elif current_state == InventoryManagementStates.private_data:
            await state.update_data(private_data=message.html_text)
            await state.set_state(InventoryManagementStates.price)
            msg = Localizator.get_text(BotEntity.ADMIN, "add_items_price").format(
                currency_text=Localizator.get_currency_text())
        else:
            try:
                price = float(message.html_text)
                assert (price > 0)
                await state.update_data(price=message.html_text)
                state_data = await state.get_data()
                category = await CategoryRepository.get_or_create(state_data['category_name'], session)
                subcategory = await SubcategoryRepository.get_or_create(state_data['subcategory_name'], session)
                items_list = [ItemDTO(category_id=category.id,
                                      subcategory_id=subcategory.id,
                                      description=state_data['description'],
                                      price=float(state_data['price']),
                                      private_data=private_data) for private_data in
                              state_data['private_data'].split('\n')]
                await ItemRepository.add_many(items_list, session)
                await session_commit(session)
                await state.clear()
                msg = Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(adding_result=len(items_list))
                cancel_button.text = Localizator.get_text(BotEntity.COMMON, "back_button")
            except Exception as _:
                msg = Localizator.get_text(BotEntity.ADMIN, "add_items_price").format(
                    currency_text=Localizator.get_currency_text())
        kb_builder.row(cancel_button)
        return msg, kb_builder
