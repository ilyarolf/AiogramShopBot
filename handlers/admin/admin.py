# import asyncio
import inspect
# import logging
from aiogram import types, Router, F
# from aiogram.exceptions import TelegramForbiddenError
# from aiogram.filters import StateFilter
# from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
# import config
from callbacks import AdminMenuCallback, AdminAnnouncementCallback
from handlers.admin.announcement import admin_announcement_router
# from crypto_api.CryptoApiManager import CryptoApiManager
# from handlers.common.common import add_pagination_buttons
# from models.item import Item
# from services.buy import BuyService
# from services.category import CategoryService
# from services.deposit import DepositService
# from services.item import ItemService
# from services.subcategory import SubcategoryService
# from services.user import UserService
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator, BotEntity
# from utils.new_items_manager import NewItemsManager
# from utils.other_sql import OtherSQLQuery
# from utils.tags_remover import HTMLTagsRemover

admin_router = Router()
admin_router.include_router(admin_announcement_router)

class AdminConstants:
    back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
                                                                               "back_to_menu"),
                                                     callback_data=AdminMenuCallback(level=0).pack())
    # confirmation_builder = InlineKeyboardBuilder()
    # confirmation_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
    #                                                  callback_data=create_admin_callback(level=4, action="confirm"))
    # cancel_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
    #                                            callback_data=create_admin_callback(level=-1, action="cancel"))
    # confirmation_builder.add(cancel_button, confirmation_button)

    # @staticmethod
    # async def get_back_button(unpacked_callback: AdminCallback) -> types.InlineKeyboardButton:
    #     new_callback = unpacked_callback.model_copy(update={"level": unpacked_callback.level - 1})
    #     return types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
    #                                       callback_data=new_callback.pack())


@admin_router.message(F.text == Localizator.get_text(BotEntity.ADMIN, "menu"), AdminIdFilter())
async def admin_command_handler(message: types.message):
    await admin(message)


async def admin(message: Message | CallbackQuery):
    admin_menu_builder = InlineKeyboardBuilder()
    admin_menu_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "announcements"),
                              callback_data=AdminAnnouncementCallback.create(level=0))
    admin_menu_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "inventory_management"),
                              callback_data=AdminMenuCallback.create(level=5))
    admin_menu_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "user_management"),
                              callback_data=AdminMenuCallback.create(level=12))
    admin_menu_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "statistics"),
                              callback_data=AdminMenuCallback.create(level=18))
    admin_menu_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "crypto_withdraw"),
                              callback_data=AdminMenuCallback.create(level=22))
    admin_menu_builder.adjust(2)
    if isinstance(message, Message):
        await message.answer(Localizator.get_text(BotEntity.ADMIN, "menu"),
                             reply_markup=admin_menu_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "menu"),
                                         reply_markup=admin_menu_builder.as_markup())


class AdminStates(StatesGroup):
    message_to_send = State()
    new_items_file = State()
    btc_withdraw = State()
    ltc_withdraw = State()
    sol_withdraw = State()
    subcategory = State()
    category = State()
    price = State()
    description = State()
    private_data = State()
    user_entity = State()
    balance_value = State()




# async def send_everyone(callback: CallbackQuery, state: FSMContext):
#     await callback.answer()
#     await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "receive_msg_request"))
#     await state.set_state(AdminStates.message_to_send)


# @admin_router.message(AdminIdFilter(), StateFilter(AdminStates.message_to_send))
# async def get_message_to_sending(message: types.message, state: FSMContext):
#     await state.clear()
#     if message.text == "cancel":
#         await message.answer(text=Localizator.get_text(BotEntity.ADMIN, "canceled"))
#     else:
#         await message.copy_to(message.chat.id, reply_markup=AdminConstants.confirmation_builder.as_markup())


# async def send_generated_message(callback: CallbackQuery):
#     unpacked_cb = AdminCallback.unpack(callback.data)
#     await callback.answer()
#     if unpacked_cb.args_to_action == "new":
#         message = await NewItemsManager.generate_restocking_message()
#         await callback.message.answer(message, reply_markup=AdminConstants.confirmation_builder.as_markup())
#     else:
#         message = await NewItemsManager.generate_in_stock_message()
#         await callback.message.answer(message, reply_markup=AdminConstants.confirmation_builder.as_markup())


# async def confirm_and_send(callback: CallbackQuery):
#     await callback.answer(text=Localizator.get_text(BotEntity.ADMIN, "sending_started"))
#     confirmed = AdminCallback.unpack(callback.data).action == "confirm"
#     is_caption = callback.message.caption
#     new_items_header = HTMLTagsRemover.remove_html_tags(Localizator.get_text(BotEntity.ADMIN,
#                                                                              "restocking_message_header"))
#     is_restocking = callback.message.text and new_items_header in callback.message.text
#     if confirmed:
#         await callback.message.edit_reply_markup()
#         counter = 0
#         users_count = await UserService.get_all_users_count()
#         telegram_ids = await UserService.get_users_tg_ids_for_sending()
#         for telegram_id in telegram_ids:
#             try:
#                 await callback.message.copy_to(telegram_id, reply_markup=None)
#                 counter += 1
#                 await asyncio.sleep(1.5)
#             except TelegramForbiddenError as e:
#                 logging.error(f"TelegramForbiddenError: {e.message}")
#                 if "user is deactivated" in e.message.lower():
#                     await UserService.update_receive_messages(telegram_id, False)
#                 elif "bot was blocked by the user" in e.message.lower():
#                     await UserService.update_receive_messages(telegram_id, False)
#             except Exception as e:
#                 logging.error(e)
#             finally:
#                 if is_restocking is True:
#                     await ItemService.set_items_not_new()
#         message_text = Localizator.get_text(BotEntity.ADMIN, "sending_result").format(counter=counter,
#                                                                                       len=len(telegram_ids),
#                                                                                       users_count=users_count)
#         if is_caption:
#             await callback.message.delete()
#             await callback.message.answer(text=message_text)
#         elif callback.message.text:
#             await callback.message.edit_text(
#                 text=message_text)


# async def decline_action(callback: CallbackQuery):
#     await callback.message.delete()
#     await callback.message.answer(text=Localizator.get_text(BotEntity.COMMON, "cancelled"))


# async def inventory_management(callback: CallbackQuery):
#     cb_builder = InlineKeyboardBuilder()
#     cb_builder.row(types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
#                                                                         "add_items"),
#                                               callback_data=create_admin_callback(level=6)))
#     cb_builder.row(types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
#                                                                         "delete_category"),
#                                               callback_data=create_admin_callback(level=8)))
#     cb_builder.row(types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
#                                                                         "delete_subcategory"),
#                                               callback_data=create_admin_callback(level=9)))
#     cb_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "inventory_management"),
#                                      reply_markup=cb_builder.as_markup())


# async def add_items(callback: CallbackQuery):
#     keyboard_builder = InlineKeyboardBuilder()
#     keyboard_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_json"),
#                             callback_data=create_admin_callback(level=7, args_to_action="JSON"))
#     keyboard_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_txt"),
#                             callback_data=create_admin_callback(level=7, args_to_action="TXT"))
#     keyboard_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_menu"),
#                             callback_data=create_admin_callback(level=7, args_to_action="MENU"))
#     keyboard_builder.adjust(2)
#     keyboard_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "add_items_msg"),
#                                      reply_markup=keyboard_builder.as_markup())


# @admin_router.message(AdminIdFilter(), F.document | F.text, StateFilter(AdminStates.new_items_file))
# async def receive_new_items_file(message: types.message, state: FSMContext):
#     if message.document:
#         await state.clear()
#         file_name = message.document.file_name
#         file_id = message.document.file_id
#         file = await message.bot.get_file(file_id)
#         await message.bot.download_file(file.file_path, file_name)
#         adding_result = await NewItemsManager.add(file_name)
#         if isinstance(adding_result, BaseException):
#             await message.answer(
#                 text=Localizator.get_text(BotEntity.ADMIN, "add_items_err").format(
#                     adding_result=adding_result))
#             await state.clear()
#         elif type(adding_result) is int:
#             await message.answer(
#                 text=Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(
#                     adding_result=adding_result))
#             await state.clear()
#     elif message.text.lower() == "cancel":
#         await state.clear()
#         await message.answer(Localizator.get_text(BotEntity.COMMON, "cancelled"))
#     else:
#         await message.answer(text=Localizator.get_text(BotEntity.ADMIN, "add_items_msg"))


# async def delete_category(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     delete_category_builder = await create_delete_entity_buttons(
#         CategoryService.get_to_delete(unpacked_callback.page), "category")
#     delete_category_builder = await add_pagination_buttons(delete_category_builder, callback.data,
#                                                            CategoryService.get_maximum_page(),
#                                                            AdminCallback.unpack,
#                                                            AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "delete_category"),
#                                      reply_markup=delete_category_builder.as_markup())


# async def create_delete_entity_buttons(get_all_entities_function,
#                                        entity_name):
#     entities = await get_all_entities_function
#     delete_entity_builder = InlineKeyboardBuilder()
#     for entity in entities:
#         delete_entity_builder.button(text=entity.name,
#                                      callback_data=create_admin_callback(level=10,
#                                                                          action=f"delete_{entity_name}",
#                                                                          args_to_action=entity.id))
#     delete_entity_builder.adjust(1)
#     return delete_entity_builder


# async def delete_subcategory(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     delete_subcategory_builder = await create_delete_entity_buttons(
#         SubcategoryService.get_to_delete(unpacked_callback.page),
#         "subcategory")
#     delete_subcategory_builder = await add_pagination_buttons(delete_subcategory_builder, callback.data,
#                                                               SubcategoryService.get_maximum_page_to_delete(),
#                                                               AdminCallback.unpack,
#                                                               AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "delete_subcategory"),
#                                      reply_markup=delete_subcategory_builder.as_markup())


# async def delete_confirmation(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     action = unpacked_callback.action
#     args_to_action = unpacked_callback.args_to_action
#     delete_markup = InlineKeyboardBuilder()
#     delete_markup.button(
#         text=Localizator.get_text(BotEntity.COMMON, "confirm"),
#         callback_data=create_admin_callback(level=11,
#                                             action=f"confirmed_{action}",
#                                             args_to_action=args_to_action)
#     )
#     delete_markup.add(AdminConstants.cancel_button)
#     entity_to_delete = action.split('_')[-1]
#     if entity_to_delete == "category":
#         category_id = args_to_action
#         category = await CategoryService.get_by_primary_key(category_id)
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
#                 entity=entity_to_delete,
#                 entity_name=category.name),
#             reply_markup=delete_markup.as_markup())
#     elif entity_to_delete == "subcategory":
#         subcategory_id = args_to_action
#         subcategory = await SubcategoryService.get_by_primary_key(subcategory_id)
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
#                 entity=entity_to_delete,
#                 entity_name=subcategory.name),
#             reply_markup=delete_markup.as_markup())


# async def confirm_and_delete(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     args_to_action = unpacked_callback.args_to_action
#     entity_to_delete = unpacked_callback.action.split('_')[-1]
#     back_to_main_builder = InlineKeyboardBuilder()
#     back_to_main_builder.add(AdminConstants.back_to_main_button)
#     if entity_to_delete == "category":
#         # TODO("Implement cascade delete subcategories, items with subcategories by category")
#         category = await CategoryService.get_by_primary_key(args_to_action)
#         message_text = Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
#             entity_name=category.name,
#             entity_to_delete=entity_to_delete)
#         await ItemService.delete_unsold_with_category_id(args_to_action)
#         await callback.message.edit_text(text=message_text, reply_markup=back_to_main_builder.as_markup())
#     elif entity_to_delete == "subcategory":
#         subcategory = await SubcategoryService.get_by_primary_key(args_to_action)
#         message_text = Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
#             entity_name=subcategory.name,
#             entity_to_delete=entity_to_delete)
#         await ItemService.delete_with_subcategory_id(args_to_action)
#         await SubcategoryService.delete_if_not_used(args_to_action)
#         await callback.message.edit_text(text=message_text, reply_markup=back_to_main_builder.as_markup())


# async def users_management(callback: CallbackQuery):
#     cb_builder = InlineKeyboardBuilder()
#     cb_builder.row(types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "credit_management"),
#                                               callback_data=create_admin_callback(level=13)))
#     cb_builder.row(types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "make_refund"),
#                                               callback_data=create_admin_callback(level=15)))
#     cb_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "user_management"),
#                                      reply_markup=cb_builder.as_markup())


# async def credit_management(callback: CallbackQuery):
#     cb_builder = InlineKeyboardBuilder()
#     cb_builder.row(
#         types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_add_balance"),
#                                    callback_data=create_admin_callback(level=14, action="plus")))
#     cb_builder.row(types.InlineKeyboardButton(
#         text=Localizator.get_text(BotEntity.ADMIN, "credit_management_reduce_balance"),
#         callback_data=create_admin_callback(level=14, action="minus")))
#     cb_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "credit_management"),
#                                      reply_markup=cb_builder.as_markup())


# async def balance_operation(callback: CallbackQuery, state: FSMContext):
#     unpacked_cb = AdminCallback.unpack(callback.data)
#     await state.update_data(operation=unpacked_cb.action)
#     await state.set_state(AdminStates.user_entity)
#     await callback.message.edit_text(
#         Localizator.get_text(BotEntity.ADMIN, "credit_management_request_user_entity"))


# @admin_router.message(AdminIdFilter(), F.text, StateFilter(AdminStates.user_entity, AdminStates.balance_value))
# async def balance_management(message: types.message, state: FSMContext):
#     current_state = await state.get_state()
#     if message.text == "cancel":
#         await state.clear()
#         await message.answer(Localizator.get_text(BotEntity.COMMON, "cancelled"))
#     elif current_state == AdminStates.user_entity:
#         await state.update_data(user_entity=message.text)
#         await state.set_state(AdminStates.balance_value)
#         operation = await state.get_data()
#         operation = operation['operation']
#         if operation == 'plus':
#             await message.answer(Localizator.get_text(BotEntity.ADMIN, "credit_management_plus_operation").format(
#                 currency_text=Localizator.get_currency_text()
#             ))
#         elif operation == 'minus':
#             await message.answer(Localizator.get_text(BotEntity.ADMIN, "credit_management_minus_operation").format(
#                 currency_text=Localizator.get_currency_text()
#             ))
#     elif current_state == AdminStates.balance_value:
#         await state.update_data(balance_value=message.text)
#         state_data = await state.get_data()
#         msg = await UserService.balance_management(state_data)
#         await state.clear()
#         await message.answer(text=msg)


# async def make_refund_markup(page):
#     refund_builder = InlineKeyboardBuilder()
#     not_refunded_buy_ids = await BuyService.get_not_refunded_buy_ids(page)
#     refund_data = await OtherSQLQuery.get_refund_data(not_refunded_buy_ids)
#     for buy in refund_data:
#         if buy.telegram_username:
#             refund_buy_button = types.InlineKeyboardButton(
#                 text=Localizator.get_text(BotEntity.ADMIN, "refund_by_username").format(
#                     telegram_username=buy.telegram_username,
#                     total_price=buy.total_price,
#                     subcategory=buy.subcategory,
#                     currency_sym=Localizator.get_currency_symbol()),
#                 callback_data=create_admin_callback(level=16,
#                                                     action="make_refund",
#                                                     args_to_action=buy.buy_id))
#         else:
#             refund_buy_button = types.InlineKeyboardButton(
#                 text=Localizator.get_text(BotEntity.ADMIN, "refund_by_tgid").format(
#                     telegram_id=buy.telegram_id,
#                     total_price=buy.total_price,
#                     subcategory=buy.subcategory,
#                     currency_sym=Localizator.get_currency_symbol()),
#                 callback_data=create_admin_callback(level=16,
#                                                     action="make_refund",
#                                                     args_to_action=buy.buy_id))
#         refund_builder.add(refund_buy_button)
#     refund_builder.adjust(1)
#     return refund_builder


# async def send_refund_menu(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     refund_builder = await make_refund_markup(unpacked_callback.page)
#     refund_builder = await add_pagination_buttons(refund_builder, callback.data,
#                                                   BuyService.get_max_refund_pages(),
#                                                   AdminCallback.unpack, AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "refund_menu"),
#                                      reply_markup=refund_builder.as_markup())


# async def refund_confirmation(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     current_level = unpacked_callback.level
#     buy_id = int(unpacked_callback.args_to_action)
#     back_button = await AdminConstants.get_back_button(unpacked_callback)
#     confirm_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
#                                                 callback_data=create_admin_callback(level=current_level + 1,
#                                                                                     action="confirm_refund",
#                                                                                     args_to_action=str(buy_id)))
#
#     confirmation_builder = InlineKeyboardBuilder()
#     confirmation_builder.add(confirm_button, AdminConstants.cancel_button, back_button)
#     refund_data = await OtherSQLQuery.get_refund_data_single(buy_id)
#     if refund_data.telegram_username:
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "refund_confirmation_by_username").format(
#                 telegram_username=refund_data.telegram_username,
#                 quantity=refund_data.quantity,
#                 subcategory=refund_data.subcategory,
#                 total_price=refund_data.total_price,
#                 currency_sym=Localizator.get_currency_symbol()),
#             reply_markup=confirmation_builder.as_markup())
#     else:
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "refund_confirmation_by_tgid").format(
#                 telegram_id=refund_data.telegram_id,
#                 quantity=refund_data.quantity,
#                 subcategory=refund_data.subcategory,
#                 total_price=refund_data.total_price,
#                 currency_sym=Localizator.get_currency_symbol()), reply_markup=confirmation_builder.as_markup())


# async def pick_statistics_entity(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     users_statistics_callback = create_admin_callback(unpacked_callback.level + 1, "users")
#     buys_statistics_callback = create_admin_callback(unpacked_callback.level + 1, "buys")
#     deposits_statistics_callback = create_admin_callback(unpacked_callback.level + 1, "deposits")
#     buttons_builder = InlineKeyboardBuilder()
#     buttons_builder.row(
#         types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "users_statistics"),
#                                    callback_data=users_statistics_callback))
#     buttons_builder.row(
#         types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "buys_statistics"),
#                                    callback_data=buys_statistics_callback))
#     buttons_builder.row(
#         types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "deposits_statistics"),
#                                    callback_data=deposits_statistics_callback))
#     buttons_builder.row(
#         types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "get_database_file"),
#                                    callback_data=create_admin_callback(level=21)))
#     buttons_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "pick_statistics_entity"),
#                                      reply_markup=buttons_builder.as_markup())


# async def pick_statistics_timedelta(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     timedelta_buttons_builder = InlineKeyboardBuilder()
#     timedelta_buttons_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "1_day"),
#                                      callback_data=unpacked_callback.model_copy(
#                                          update={"args_to_action": '1', 'level': unpacked_callback.level + 1}).pack())
#     timedelta_buttons_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "7_day"),
#                                      callback_data=unpacked_callback.model_copy(
#                                          update={"args_to_action": '7', 'level': unpacked_callback.level + 1}).pack())
#     timedelta_buttons_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "30_day"),
#                                      callback_data=unpacked_callback.model_copy(
#                                          update={"args_to_action": '30', 'level': unpacked_callback.level + 1}).pack())
#     timedelta_buttons_builder.row(await AdminConstants.get_back_button(unpacked_callback))
#     await callback.message.edit_text(text=Localizator.get_text(BotEntity.ADMIN, "statistics_timedelta"),
#                                      reply_markup=timedelta_buttons_builder.as_markup())


# async def get_statistics(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     statistics_keyboard_builder = InlineKeyboardBuilder()
#     if unpacked_callback.action == "users":
#         users, users_count = await UserService.get_new_users_by_timedelta(unpacked_callback.args_to_action,
#                                                                           unpacked_callback.page)
#         for user in users:
#             if user.telegram_username:
#                 statistics_keyboard_builder.button(text=user.telegram_username,
#                                                    url=f"t.me/{user.telegram_username}")
#         statistics_keyboard_builder.adjust(1)
#         statistics_keyboard_builder = await add_pagination_buttons(statistics_keyboard_builder, callback.data,
#                                                                    UserService.get_max_page_for_users_by_timedelta(
#                                                                        unpacked_callback.args_to_action),
#                                                                    AdminCallback.unpack, None)
#         statistics_keyboard_builder.row(
#             *[AdminConstants.back_to_main_button, await AdminConstants.get_back_button(unpacked_callback)])
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "new_users_msg").format(
#                 users_count=users_count,
#                 timedelta=unpacked_callback.args_to_action),
#             reply_markup=statistics_keyboard_builder.as_markup())
#     elif unpacked_callback.action == "buys":
#         back_button = await AdminConstants.get_back_button(unpacked_callback)
#         buttons = [back_button,
#                    AdminConstants.back_to_main_button]
#         statistics_keyboard_builder.add(*buttons)
#         buys = await BuyService.get_new_buys_by_timedelta(unpacked_callback.args_to_action)
#         total_profit = 0
#         items_sold = 0
#         for buy in buys:
#             total_profit += buy.total_price
#             items_sold += buy.quantity
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "sales_statistics").format(
#                 timedelta=unpacked_callback.args_to_action,
#                 total_profit=total_profit, items_sold=items_sold,
#                 buys_count=len(buys), currency_sym=Localizator.get_currency_symbol()),
#             reply_markup=statistics_keyboard_builder.as_markup())
#     elif unpacked_callback.action == "deposits":
#         back_button = await AdminConstants.get_back_button(unpacked_callback)
#         buttons = [back_button,
#                    AdminConstants.back_to_main_button]
#         statistics_keyboard_builder.add(*buttons)
#         deposits = await DepositService.get_by_timedelta(unpacked_callback.args_to_action)
#         btc_amount = 0.0
#         ltc_amount = 0.0
#         sol_amount = 0.0
#         fiat_amount = 0.0
#         usdt_trc20_amount = 0.0
#         usdt_erc20_amount = 0.0
#         usdc_erc20_amount = 0.0
#         for deposit in deposits:
#             if deposit.network == "BTC":
#                 btc_amount += deposit.amount / pow(10, 8)
#             elif deposit.network == "LTC":
#                 ltc_amount += deposit.amount / pow(10, 8)
#             elif deposit.network == "SOL":
#                 sol_amount += deposit.amount / pow(10, 9)
#             elif deposit.token_name == "USDT_TRC20":
#                 divided_amount = deposit.amount / pow(10, 6)
#                 fiat_amount += divided_amount
#                 usdt_trc20_amount += divided_amount
#             elif deposit.token_name == "USDT_ERC20":
#                 divided_amount = deposit.amount / pow(10, 6)
#                 fiat_amount += divided_amount
#                 usdt_erc20_amount += divided_amount
#             elif deposit.token_name == "USDC_ERC20":
#                 divided_amount = deposit.amount / pow(10, 6)
#                 fiat_amount += divided_amount
#                 usdc_erc20_amount += divided_amount
#         crypto_prices = await CryptoApiManager.get_crypto_prices()
#         fiat_amount += (btc_amount * crypto_prices['btc']) + (ltc_amount * crypto_prices['ltc']) + (
#                 sol_amount * crypto_prices['sol'])
#         await callback.message.edit_text(
#             text=Localizator.get_text(BotEntity.ADMIN, "deposits_statistics_msg").format(
#                 timedelta=unpacked_callback.args_to_action, deposits_count=len(deposits),
#                 btc_amount=btc_amount, ltc_amount=ltc_amount,
#                 sol_amount=sol_amount, usdt_trc20_amount=usdt_trc20_amount,
#                 usdt_erc20_amount=usdt_erc20_amount, usdc_erc20_amount=usdc_erc20_amount, fiat_amount=fiat_amount,
#                 currency_text=Localizator.get_currency_text()),
#             reply_markup=statistics_keyboard_builder.as_markup())


# async def make_refund(callback: CallbackQuery):
#     unpacked_callback = AdminCallback.unpack(callback.data)
#     buy_id = int(unpacked_callback.args_to_action)
#     is_confirmed = unpacked_callback.action == "confirm_refund"
#     if is_confirmed:
#         refund_data = await OtherSQLQuery.get_refund_data_single(buy_id)
#         await BuyService.refund(buy_id, refund_data)
#         bot = callback.bot
#         await NotificationManager.send_refund_message(refund_data, bot)
#         if refund_data.telegram_username:
#             await callback.message.edit_text(
#                 text=Localizator.get_text(BotEntity.ADMIN, "successfully_refunded_with_username").format(
#                     total_price=refund_data.total_price,
#                     telegram_username=refund_data.telegram_username,
#                     quantity=refund_data.quantity,
#                     subcategory=refund_data.subcategory,
#                     currency_sym=Localizator.get_currency_symbol()))
#         else:
#             await callback.message.edit_text(
#                 text=Localizator.get_text(BotEntity.ADMIN, "successfully_refunded_with_tgid").format(
#                     total_price=refund_data.total_price,
#                     telegram_id=refund_data.telegram_id,
#                     quantity=refund_data.quantity,
#                     subcategory=refund_data.subcategory,
#                     currency_sym=Localizator.get_currency_symbol()))


# async def send_db_file(callback: CallbackQuery):
#     with open(f"./data/{config.DB_NAME}", "rb") as f:
#         await callback.message.bot.send_document(callback.from_user.id,
#                                                  types.BufferedInputFile(file=f.read(), filename="database.db"))
#     await callback.answer()


# async def wallet(callback: CallbackQuery):
#     cb_builder = InlineKeyboardBuilder()
#     cb_builder.row(
#         types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN, "withdraw_funds"),
#                                    callback_data=create_admin_callback(level=23)))
#     cb_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "crypto_withdraw"),
#                                      reply_markup=cb_builder.as_markup())


# async def send_withdraw_crypto_menu(callback: CallbackQuery):
#     cb_builder = InlineKeyboardBuilder()
#     cb_builder.row(AdminConstants.back_to_main_button)
#     await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, 'choose_crypto_to_withdraw'),
#                                      reply_markup=cb_builder.as_markup())


# async def add_items_menu(callback: CallbackQuery, state: FSMContext):
#     unpacked_cb = AdminCallback.unpack(callback.data)
#     method = unpacked_cb.args_to_action
#     if method == "JSON":
#         await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "add_items_json_msg"))
#         await state.set_state(AdminStates.new_items_file)
#     elif method == "TXT":
#         await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "add_items_txt_msg"))
#         await state.set_state(AdminStates.new_items_file)
#     elif method == "MENU":
#         await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "add_items_category"))
#         await state.set_state(AdminStates.category)


# @admin_router.message(AdminIdFilter(), F.text, StateFilter(AdminStates.subcategory, AdminStates.category,
#                                                            AdminStates.description, AdminStates.price,
#                                                            AdminStates.private_data))
# async def add_item_txt_menu(message: Message, state: FSMContext):
#     current_state = await state.get_state()
#     if message.text == "cancel":
#         await state.clear()
#         await message.answer(Localizator.get_text(BotEntity.COMMON, "cancelled"))
#     elif current_state == AdminStates.category:
#         await state.update_data(category_name=message.text)
#         await state.set_state(AdminStates.subcategory)
#         await message.answer(Localizator.get_text(BotEntity.ADMIN, "add_items_subcategory"))
#     elif current_state == AdminStates.subcategory:
#         await state.update_data(subcategory_name=message.text)
#         await state.set_state(AdminStates.description)
#         await message.answer(Localizator.get_text(BotEntity.ADMIN, "add_items_description"))
#     elif current_state == AdminStates.description:
#         await state.update_data(description=message.text)
#         await state.set_state(AdminStates.private_data)
#         await message.answer(Localizator.get_text(BotEntity.ADMIN, "add_items_private_data"))
#     elif current_state == AdminStates.private_data:
#         await state.update_data(private_data=message.text)
#         await state.set_state(AdminStates.price)
#         await message.answer(Localizator.get_text(BotEntity.ADMIN, "add_items_price").format(
#             currency_text=Localizator.get_currency_text()))
#     elif current_state == AdminStates.price:
#         await state.update_data(price=message.text)
#         state_data = await state.get_data()
#         category = await CategoryService.get_or_create_one(state_data['category_name'])
#         subcategory = await SubcategoryService.get_or_create_one(state_data['subcategory_name'])
#         items_list = []
#         if (len(state_data['private_data'].split("\n"))) > 1:
#             splitted_private_data = state_data['private_data'].split("\n")
#             for private_data in splitted_private_data:
#                 items_list.append(Item(
#                     category_id=category.id,
#                     subcategory_id=subcategory.id,
#                     description=state_data['description'],
#                     price=float(state_data['price']),
#                     private_data=private_data
#                 ))
#         else:
#             items_list.append(Item(
#                 category_id=category.id,
#                 subcategory_id=subcategory.id,
#                 description=state_data['description'],
#                 price=float(state_data['price']),
#                 private_data=state_data['private_data']
#             ))
#         await ItemService.add_many(items_list)
#         await state.clear()
#         await message.answer(
#             Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(adding_result=len(items_list)))


@admin_router.callback_query(AdminIdFilter(), AdminMenuCallback.filter())
async def admin_menu_navigation(callback: CallbackQuery, state: FSMContext, callback_data: AdminMenuCallback):
    current_level = callback_data.level

    levels = {
        # -1: decline_action,
        0: admin,
        # 1: announcements,
        # 2: send_everyone,
        # 3: send_generated_message,
        # 4: confirm_and_send,
        # 5: inventory_management,
        # 6: add_items,
        # 7: add_items_menu,
        # 8: delete_category,
        # 9: delete_subcategory,
        # 10: delete_confirmation,
        # 11: confirm_and_delete,
        # 12: users_management,
        # 13: credit_management,
        # 14: balance_operation,
        # 15: send_refund_menu,
        # 16: refund_confirmation,
        # 17: make_refund,
        # 18: pick_statistics_entity,
        # 19: pick_statistics_timedelta,
        # 20: get_statistics,
        # 21: send_db_file,
        # 22: wallet,
        # 23: send_withdraw_crypto_menu
    }

    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
