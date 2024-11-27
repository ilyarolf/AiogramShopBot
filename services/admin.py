import asyncio
import logging
from typing import Tuple

from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import AdminAnnouncementCallback, AnnouncementType, AdminInventoryManagementCallback, EntityType, \
    AddType, UserManagementCallback, UserManagementOperation
from handlers.admin.constants import AdminConstants, AdminInventoryManagementStates, UserManagementStates
from handlers.common.common import add_pagination_buttons
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
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
                                                                                entity_type=EntityType.SUBCATEGORY))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "inventory_management"), kb_builder

    @staticmethod
    async def get_add_items_type(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_json"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.JSON, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_txt"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.TXT, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_menu"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.MENU, EntityType.ITEM))
        kb_builder.adjust(1)
        kb_builder.row(unpacked_cb.get_back_button())
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
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                          CategoryRepository.get_maximum_page(),
                                                          unpacked_cb.get_back_button(0))
                return Localizator.get_text(BotEntity.ADMIN, "delete_category"), kb_builder
            case EntityType.SUBCATEGORY:
                subcategories = await SubcategoryRepository.get_to_delete(unpacked_cb.page)
                [kb_builder.button(text=subcategory.name, callback_data=AdminInventoryManagementCallback.create(
                    level=3,
                    entity_type=unpacked_cb.entity_type,
                    entity_id=subcategory.id
                )) for subcategory in subcategories]
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                          SubcategoryRepository.get_maximum_page_to_delete(),
                                                          unpacked_cb.get_back_button(0))
                return Localizator.get_text(BotEntity.ADMIN, "delete_subcategory"), kb_builder

    @staticmethod
    async def delete_confirmation(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        unpacked_cb.confirmation = True
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=unpacked_cb)
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=AdminInventoryManagementCallback.create(0))
        match unpacked_cb.entity_type:
            case EntityType.CATEGORY:
                category = await CategoryRepository.get_by_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
                    entity=unpacked_cb.entity_type.name.capitalize(),
                    entity_name=category.name
                ), kb_builder
            case EntityType.SUBCATEGORY:
                subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
                    entity=unpacked_cb.entity_type.name.capitalize(),
                    entity_name=subcategory.name
                ), kb_builder

    @staticmethod
    async def delete_entity(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(AdminConstants.back_to_main_button)
        match unpacked_cb.entity_type:
            case EntityType.CATEGORY:
                category = await CategoryRepository.get_by_id(unpacked_cb.entity_id)
                await ItemRepository.delete_unsold_by_category_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
                    entity_name=category.name,
                    entity_to_delete=unpacked_cb.entity_type.name.capitalize()), kb_builder
            case EntityType.SUBCATEGORY:
                subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.entity_id)
                await ItemRepository.delete_unsold_by_subcategory_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
                    entity_name=subcategory.name,
                    entity_to_delete=unpacked_cb.entity_type.name.capitalize()), kb_builder

    @staticmethod
    async def get_add_item_msg(callback: CallbackQuery, state: FSMContext):
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_markup = InlineKeyboardBuilder()
        kb_markup.button(text=Localizator.get_text(BotEntity.COMMON, 'cancel'),
                         callback_data=AdminInventoryManagementCallback.create(0))
        await state.update_data(add_type=unpacked_cb.add_type.value)
        await state.set_state()
        match unpacked_cb.add_type:
            case AddType.JSON:
                await state.set_state(AdminInventoryManagementStates.document)
                return Localizator.get_text(BotEntity.ADMIN, "add_items_json_msg"), kb_markup
            case AddType.TXT:
                await state.set_state(AdminInventoryManagementStates.document)
                return Localizator.get_text(BotEntity.ADMIN, "add_items_txt_msg"), kb_markup
            case AddType.MENU:
                await state.set_state(AdminInventoryManagementStates.category)
                return Localizator.get_text(BotEntity.ADMIN, "add_items_category"), kb_markup

    @staticmethod
    async def add_item_menu(message: Message, state: FSMContext):
        current_state = await state.get_state()
        if message.text == 'cancel':
            await state.clear()
            return Localizator.get_text(BotEntity.COMMON, "cancelled")
        elif current_state == AdminInventoryManagementStates.category:
            await state.update_data(category_name=message.text)
            await state.set_state(AdminInventoryManagementStates.subcategory)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_subcategory")
        elif current_state == AdminInventoryManagementStates.subcategory:
            await state.update_data(subcategory_name=message.text)
            await state.set_state(AdminInventoryManagementStates.description)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_description")
        elif current_state == AdminInventoryManagementStates.description:
            await state.update_data(description=message.text)
            await state.set_state(AdminInventoryManagementStates.private_data)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_private_data")
        elif current_state == AdminInventoryManagementStates.private_data:
            await state.update_data(private_data=message.text)
            await state.set_state(AdminInventoryManagementStates.price)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_price").format(
                currency_text=Localizator.get_currency_text())
        elif current_state == AdminInventoryManagementStates.price:
            await state.update_data(price=message.text)
            state_data = await state.get_data()
            category = await CategoryRepository.get_or_create(state_data['category_name'])
            subcategory = await SubcategoryRepository.get_or_create(state_data['subcategory_name'])
            items_list = [ItemDTO(category_id=category.id,
                                  subcategory_id=subcategory.id,
                                  description=state_data['description'],
                                  price=float(state_data['price']),
                                  private_data=private_data) for private_data in state_data['private_data'].split('\n')]
            await ItemRepository.add_many(items_list)
            await state.clear()
            return Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(adding_result=len(items_list))

    @staticmethod
    async def get_user_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management"),
                          callback_data=UserManagementCallback.create(1))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "make_refund"),
                          callback_data=UserManagementCallback.create(2))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "user_management"), kb_builder

    @staticmethod
    async def get_credit_management_menu(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = UserManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_add_balance"),
                          callback_data=UserManagementCallback.create(1, UserManagementOperation.ADD_BALANCE))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_reduce_balance"),
                          callback_data=UserManagementCallback.create(1, UserManagementOperation.REDUCE_BALANCE))
        kb_builder.row(unpacked_cb.get_back_button())
        return Localizator.get_text(BotEntity.ADMIN, "credit_management"), kb_builder

    @staticmethod
    async def request_user_entity(callback: CallbackQuery, state: FSMContext):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        await state.set_state(UserManagementStates.user_entity)
        unpacked_cb = UserManagementCallback.unpack(callback.data)
        await state.update_data(operation=unpacked_cb.operation.value)
        return Localizator.get_text(BotEntity.ADMIN, "credit_management_request_user_entity"), kb_builder

    @staticmethod
    async def request_balance_amount(message: Message, state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        await state.update_data(user_entity=message.text)
        await state.set_state(UserManagementStates.balance_amount)
        data = await state.get_data()
        operation = UserManagementOperation(int(data['operation']))
        match operation:
            case UserManagementOperation.ADD_BALANCE:
                return Localizator.get_text(BotEntity.ADMIN, "credit_management_plus_operation").format(
                    currency_text=Localizator.get_currency_text()), kb_builder
            case UserManagementOperation.REDUCE_BALANCE:
                return Localizator.get_text(BotEntity.ADMIN, "credit_management_minus_operation").format(
                    currency_text=Localizator.get_currency_text()), kb_builder

    @staticmethod
    async def balance_management(message: Message, state: FSMContext) -> str:
        data = await state.get_data()
        await state.clear()
        user = await UserRepository.get_user_entity(data['user_entity'])
        operation = UserManagementOperation(int(data['operation']))
        if user is None:
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_user_not_found")
        elif operation == UserManagementOperation.ADD_BALANCE:
            user.top_up_amount += float(message.text)
            await UserRepository.update(user)
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_added_success").format(
                            amount=message.text,
                            telegram_id=user.telegram_id,
                            currency_text=Localizator.get_currency_text())
        else:
            user.consume_records += float(message.text)
            await UserRepository.update(user)
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_reduced_success").format(
                            amount=message.text,
                            telegram_id=user.telegram_id,
                            currency_text=Localizator.get_currency_text())

