import asyncio
import inspect
import logging
from typing import Union

from aiogram import types, Router, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from bot import bot
from handlers.common.common import add_pagination_buttons
from services.buy import BuyService
from services.category import CategoryService
from services.item import ItemService
from services.subcategory import SubcategoryService
from services.user import UserService
from utils.custom_filters import AdminIdFilter
from utils.new_items_manager import NewItemsManager
from utils.notification_manager import NotificationManager
from utils.other_sql import OtherSQLQuery


class AdminCallback(CallbackData, prefix="admin"):
    level: int
    action: str
    args_to_action: Union[str, int]
    page: int


admin_router = Router()


def create_admin_callback(level: int, action: str = "", args_to_action: str = "", page: int = 0):
    return AdminCallback(level=level, action=action, args_to_action=args_to_action, page=page).pack()


class AdminConstants:
    confirmation_builder = InlineKeyboardBuilder()
    confirmation_button = types.InlineKeyboardButton(text="Confirm",
                                                     callback_data=create_admin_callback(level=2, action="confirm"))
    decline_button = types.InlineKeyboardButton(text="Decline",
                                                callback_data=create_admin_callback(level=3, action="decline"))
    confirmation_builder.add(decline_button, confirmation_button)
    back_to_main_button = types.InlineKeyboardButton(text="Back to admin menu",
                                                     callback_data=create_admin_callback(level=0))

    @staticmethod
    async def get_back_button(unpacked_callback: AdminCallback) -> types.InlineKeyboardButton:
        new_callback = unpacked_callback.model_copy(update={"level": unpacked_callback.level - 1})
        return types.InlineKeyboardButton(text="Back", callback_data=new_callback.pack())


@admin_router.message(Command("admin"), AdminIdFilter())
async def admin_command_handler(message: types.message):
    await admin(message)


async def admin(message: Union[Message, CallbackQuery]):
    admin_menu_builder = InlineKeyboardBuilder()
    admin_menu_builder.button(text="Send to everyone",
                              callback_data=create_admin_callback(level=1,
                                                                  action="send_to_everyone"))
    admin_menu_builder.button(text="Add items",
                              callback_data=create_admin_callback(level=4,
                                                                  action="add_items"))
    admin_menu_builder.button(text="Send restocking message",
                              callback_data=create_admin_callback(
                                  level=5,
                                  action="send_to_everyone"))
    admin_menu_builder.button(text="Get database file",
                              callback_data=create_admin_callback(
                                  level=6,
                                  action="get_db_file"
                              ))
    admin_menu_builder.button(text="Delete category",
                              callback_data=create_admin_callback(
                                  level=7
                              ))
    admin_menu_builder.button(text="Delete subcategory",
                              callback_data=create_admin_callback(
                                  level=8
                              ))
    admin_menu_builder.button(text="Make refund",
                              callback_data=create_admin_callback(
                                  level=11
                              ))
    admin_menu_builder.button(text="Statistics",
                              callback_data=create_admin_callback(level=14))
    admin_menu_builder.adjust(2)
    if isinstance(message, Message):
        await message.answer("<b>Admin Menu:</b>", parse_mode=ParseMode.HTML,
                             reply_markup=admin_menu_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text("<b>Admin Menu:</b>", parse_mode=ParseMode.HTML,
                                         reply_markup=admin_menu_builder.as_markup())


class AdminStates(StatesGroup):
    message_to_send = State()
    new_items_file = State()


async def send_to_everyone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("<b>Send a message to the newsletter</b>:", parse_mode=ParseMode.HTML)
    await state.set_state(AdminStates.message_to_send)


@admin_router.message(AdminIdFilter(), StateFilter(AdminStates.message_to_send))
async def get_message_to_sending(message: types.message, state: FSMContext):
    await message.copy_to(message.chat.id, reply_markup=AdminConstants.confirmation_builder.as_markup())
    await state.clear()


async def confirm_and_send(callback: CallbackQuery):
    await callback.answer(text="Sending started")
    confirmed = AdminCallback.unpack(callback.data).action == "confirm"
    is_caption = callback.message.caption
    is_restocking = callback.message.text and callback.message.text.__contains__("📅 Update")
    if confirmed:
        counter = 0
        users_count = await UserService.get_all_users_count()
        telegram_ids = await UserService.get_users_tg_ids_for_sending()
        for telegram_id in telegram_ids:
            try:
                await callback.message.copy_to(telegram_id, reply_markup=None)
                counter += 1
                await asyncio.sleep(1.5)
            except TelegramForbiddenError as e:
                logging.error(f"TelegramForbiddenError: {e.message}")
                if "user is deactivated" in e.message.lower():
                    await UserService.update_receive_messages(telegram_id, False)
                elif "bot was blocked by the user" in e.message.lower():
                    await UserService.update_receive_messages(telegram_id, False)
            except Exception as e:
                logging.error(e)
        message_text = (f"<b>Message sent to {counter} out of {len(telegram_ids)} active users.\n"
                        f"Total users:{users_count}</b>")
        if is_caption:
            await callback.message.delete()
            await callback.message.answer(text=message_text, parse_mode=ParseMode.HTML)
        elif callback.message.text:
            await callback.message.edit_text(
                text=message_text,
                parse_mode=ParseMode.HTML)
    if is_restocking:
        await ItemService.set_items_not_new()


async def decline_action(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(text="<b>Declined!</b>", parse_mode=ParseMode.HTML)


async def add_items(callback: CallbackQuery, state: FSMContext):
    unpacked_callback = AdminCallback.unpack(callback.data)
    if unpacked_callback.level == 4 and unpacked_callback.action == "add_items":
        await callback.message.edit_text(text="<b>Send .json file with new items or type \"cancel\" for cancel.</b>",
                                         parse_mode=ParseMode.HTML)
        await state.set_state(AdminStates.new_items_file)


@admin_router.message(AdminIdFilter(), F.document | F.text, StateFilter(AdminStates.new_items_file))
async def receive_new_items_file(message: types.message, state: FSMContext):
    if message.document:
        await state.clear()
        file_name = "new_items.json"
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, file_name)
        adding_result = await NewItemsManager.add(file_name)
        if isinstance(adding_result, BaseException):
            await message.answer(text=f"<b>Exception:</b>\n<code>{adding_result}</code>", parse_mode=ParseMode.HTML)
        elif type(adding_result) is int:
            await message.answer(text=f"<b>Successfully added {adding_result} items!</b>", parse_mode=ParseMode.HTML)
    elif message.text and message.text.lower() == "cancel":
        await state.clear()
        await message.answer("<b>Adding items successfully cancelled!</b>", parse_mode=ParseMode.HTML)
    else:
        await message.answer(text="<b>Send .json file with new items or type \"cancel\" for cancel.</b>",
                             parse_mode=ParseMode.HTML)


async def send_restocking_message(callback: CallbackQuery):
    message = await NewItemsManager.generate_restocking_message()
    await callback.message.answer(message, parse_mode=ParseMode.HTML,
                                  reply_markup=AdminConstants.confirmation_builder.as_markup())


async def delete_category(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    delete_category_builder = await create_delete_entity_buttons(
        CategoryService.get_all_categories(
            unpacked_callback.page),
        "category")
    delete_category_builder = await add_pagination_buttons(delete_category_builder, callback.data,
                                                           CategoryService.get_maximum_page(), AdminCallback.unpack,
                                                           AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>Categories:</b>", parse_mode=ParseMode.HTML,
                                     reply_markup=delete_category_builder.as_markup())


async def create_delete_entity_buttons(get_all_entities_function,
                                       entity_name):
    entities = await get_all_entities_function
    delete_entity_builder = InlineKeyboardBuilder()
    for entity in entities:
        delete_entity_callback = create_admin_callback(level=9,
                                                       action=f"delete_{entity_name}",
                                                       args_to_action=entity.id)
        delete_entity_button = types.InlineKeyboardButton(text=entity.name, callback_data=delete_entity_callback)
        delete_entity_builder.add(delete_entity_button)
    delete_entity_builder.adjust(1)
    return delete_entity_builder


async def delete_subcategory(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    delete_subcategory_builder = await create_delete_entity_buttons(
        SubcategoryService.get_all(unpacked_callback.page),
        "subcategory")
    delete_subcategory_builder = await add_pagination_buttons(delete_subcategory_builder, callback.data,
                                                              SubcategoryService.get_maximum_page(),
                                                              AdminCallback.unpack,
                                                              AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>Subcategories:</b>", parse_mode=ParseMode.HTML,
                                     reply_markup=delete_subcategory_builder.as_markup())


async def delete_confirmation(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    current_level = unpacked_callback.level
    action = unpacked_callback.action
    args_to_action = unpacked_callback.args_to_action
    delete_markup = InlineKeyboardBuilder()
    confirm_callback = create_admin_callback(level=current_level + 1,
                                             action=f"confirmed_{action}",
                                             args_to_action=args_to_action)
    confirm_button = types.InlineKeyboardButton(text="Confirm", callback_data=confirm_callback)
    decline_callback = create_admin_callback(level=current_level - 6)
    decline_button = types.InlineKeyboardButton(text="Decline", callback_data=decline_callback)
    delete_markup.add(confirm_button, decline_button)
    entity_to_delete = action.split('_')[-1]
    if entity_to_delete == "category":
        category_id = args_to_action
        category = await CategoryService.get_by_primary_key(category_id)
        await callback.message.edit_text(text=f"<b>Do you really want to delete the category {category.name}?</b>",
                                         parse_mode=ParseMode.HTML,
                                         reply_markup=delete_markup.as_markup())
    elif entity_to_delete == "subcategory":
        subcategory_id = args_to_action
        subcategory = await SubcategoryService.get_by_primary_key(subcategory_id)
        await callback.message.edit_text(
            text=f"<b>Do you really want to delete the subcategory {subcategory.name}?</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=delete_markup.as_markup())


async def confirm_and_delete(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    args_to_action = unpacked_callback.args_to_action
    entity_to_delete = unpacked_callback.action.split('_')[-1]
    back_to_main_builder = InlineKeyboardBuilder()
    back_to_main_builder.add(AdminConstants.back_to_main_button)
    if entity_to_delete == "category":
        # TODO("Implement cascade delete subcategories, items with subcategories by category")
        category = await CategoryService.get_by_primary_key(args_to_action)
        message_text = f"<b>Successfully deleted {category.name} {entity_to_delete}!</b>"
        await ItemService.delete_unsold_with_category_id(args_to_action)
        await callback.message.edit_text(text=message_text,
                                         parse_mode=ParseMode.HTML, reply_markup=back_to_main_builder.as_markup())
    elif entity_to_delete == "subcategory":
        subcategory = await SubcategoryService.get_by_primary_key(args_to_action)
        message_text = f"<b>Successfully deleted {subcategory.name} {entity_to_delete}!</b>"
        await ItemService.delete_with_subcategory_id(args_to_action)
        await SubcategoryService.delete_if_not_used(args_to_action)
        await callback.message.edit_text(text=message_text,
                                         parse_mode=ParseMode.HTML, reply_markup=back_to_main_builder.as_markup())


async def make_refund_markup(page):
    refund_builder = InlineKeyboardBuilder()
    not_refunded_buy_ids = await BuyService.get_not_refunded_buy_ids(page)
    refund_data = await OtherSQLQuery.get_refund_data(not_refunded_buy_ids)
    for buy in refund_data:
        if buy.telegram_username:
            refund_buy_button = types.InlineKeyboardButton(
                text=f"@{buy.telegram_username}|${buy.total_price}|{buy.subcategory}",
                callback_data=create_admin_callback(level=12,
                                                    action="make_refund",
                                                    args_to_action=buy.buy_id))
        else:
            refund_buy_button = types.InlineKeyboardButton(
                text=f"ID:{buy.telegram_id}|${buy.total_price}|{buy.subcategory}",
                callback_data=create_admin_callback(level=12,
                                                    action="make_refund",
                                                    args_to_action=buy.buy_id))
        refund_builder.add(refund_buy_button)
    refund_builder.adjust(1)
    return refund_builder


async def send_refund_menu(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    refund_builder = await make_refund_markup(unpacked_callback.page)
    refund_builder = await add_pagination_buttons(refund_builder, callback.data, BuyService.get_max_refund_pages(),
                                                  AdminCallback.unpack, AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>Refund menu:</b>", reply_markup=refund_builder.as_markup(),
                                     parse_mode=ParseMode.HTML)


async def refund_confirmation(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    current_level = unpacked_callback.level
    buy_id = int(unpacked_callback.args_to_action)
    back_button = await AdminConstants.get_back_button(unpacked_callback)
    confirm_button = types.InlineKeyboardButton(text="Confirm",
                                                callback_data=create_admin_callback(level=current_level + 1,
                                                                                    action="confirm_refund",
                                                                                    args_to_action=str(buy_id)))

    confirmation_builder = InlineKeyboardBuilder()
    confirmation_builder.add(confirm_button, AdminConstants.decline_button, back_button)
    refund_data = await OtherSQLQuery.get_refund_data_single(buy_id)
    if refund_data.telegram_username:
        await callback.message.edit_text(
            text=f"<b>Do you really want to refund user @{refund_data.telegram_username} "
                 f"for purchasing {refund_data.quantity} {refund_data.subcategory} "
                 f"in the amount of ${refund_data.total_price}</b>", parse_mode=ParseMode.HTML,
            reply_markup=confirmation_builder.as_markup())
    else:
        await callback.message.edit_text(
            text=f"<b>Do you really want to refund user with ID:{refund_data.telegram_id} "
                 f"for purchasing {refund_data.quantity} {refund_data.subcategory} "
                 f"in the amount of ${refund_data.total_price}</b>", parse_mode=ParseMode.HTML,
            reply_markup=confirmation_builder.as_markup())


async def pick_statistics_entity(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    users_statistics_callback = create_admin_callback(unpacked_callback.level + 1, "users")
    buys_statistics_callback = create_admin_callback(unpacked_callback.level + 1, "buys")
    buttons_builder = InlineKeyboardBuilder()
    buttons_builder.add(types.InlineKeyboardButton(text="📊Users statistics", callback_data=users_statistics_callback))
    buttons_builder.add(types.InlineKeyboardButton(text="📊Buys statistics", callback_data=buys_statistics_callback))
    buttons_builder.row(AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>📊 Pick statistics entity</b>", reply_markup=buttons_builder.as_markup(),
                                     parse_mode=ParseMode.HTML)


async def pick_statistics_timedelta(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    one_day_cb = unpacked_callback.model_copy(
        update={"args_to_action": '1', 'level': unpacked_callback.level + 1}).pack()
    seven_days_cb = unpacked_callback.model_copy(
        update={"args_to_action": '7', 'level': unpacked_callback.level + 1}).pack()
    one_month_cb = unpacked_callback.model_copy(
        update={"args_to_action": '30', 'level': unpacked_callback.level + 1}).pack()
    timedelta_buttons_builder = InlineKeyboardBuilder()
    timedelta_buttons_builder.add(types.InlineKeyboardButton(text="1 Day", callback_data=one_day_cb))
    timedelta_buttons_builder.add(types.InlineKeyboardButton(text="7 Days", callback_data=seven_days_cb))
    timedelta_buttons_builder.add(types.InlineKeyboardButton(text="30 Days", callback_data=one_month_cb))
    timedelta_buttons_builder.row(await AdminConstants.get_back_button(unpacked_callback))
    await callback.message.edit_text(text="<b>🗓 Pick timedelta to statistics</b>",
                                     reply_markup=timedelta_buttons_builder.as_markup(), parse_mode=ParseMode.HTML)


async def get_statistics(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    statistics_keyboard_builder = InlineKeyboardBuilder()
    if unpacked_callback.action == "users":
        users, users_count = await UserService.get_new_users_by_timedelta(unpacked_callback.args_to_action,
                                                                          unpacked_callback.page)
        for user in users:
            if user.telegram_username:
                user_button = types.InlineKeyboardButton(text=user.telegram_username,
                                                         url=f"t.me/{user.telegram_username}")
                statistics_keyboard_builder.add(user_button)
        statistics_keyboard_builder.adjust(1)
        statistics_keyboard_builder = await add_pagination_buttons(statistics_keyboard_builder, callback.data,
                                                                   UserService.get_max_page_for_users_by_timedelta(
                                                                       unpacked_callback.args_to_action),
                                                                   AdminCallback.unpack, None)
        statistics_keyboard_builder.row(
            *[AdminConstants.back_to_main_button, await AdminConstants.get_back_button(unpacked_callback)])
        await callback.message.edit_text(
            text=f"<b>{users_count} new users in the last {unpacked_callback.args_to_action} days:</b>",
            reply_markup=statistics_keyboard_builder.as_markup(), parse_mode=ParseMode.HTML)

    elif unpacked_callback.action == "buys":
        back_button = await AdminConstants.get_back_button(unpacked_callback)
        buttons = [back_button,
                   AdminConstants.back_to_main_button]
        statistics_keyboard_builder.add(*buttons)
        buys = await BuyService.get_new_buys_by_timedelta(unpacked_callback.args_to_action)
        total_profit = 0
        items_sold = 0
        for buy in buys:
            total_profit += buy.total_price
            items_sold += buy.quantity
        await callback.message.edit_text(
            text=f"<b>📊 Sales statistics for the last {unpacked_callback.args_to_action} days.\n"
                 f"💰 Total profit: ${total_profit}\n"
                 f"🛍️ Items sold: {items_sold}\n"
                 f"💼 Total buys: {len(buys)}</b>", reply_markup=statistics_keyboard_builder.as_markup(),
            parse_mode=ParseMode.HTML)


async def make_refund(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    buy_id = int(unpacked_callback.args_to_action)
    is_confirmed = unpacked_callback.action == "confirm_refund"
    if is_confirmed:
        refund_data = await OtherSQLQuery.get_refund_data_single(buy_id)
        await BuyService.refund(buy_id, refund_data)
        await NotificationManager.send_refund_message(refund_data)
        if refund_data.telegram_username:
            await callback.message.edit_text(text=f"<b>Successfully refunded ${refund_data.total_price} "
                                                  f"to user {refund_data.telegram_username} "
                                                  f"for purchasing {refund_data.quantity} "
                                                  f"{refund_data.subcategory}</b>", parse_mode=ParseMode.HTML)
        else:
            await callback.message.edit_text(text=f"<b>Successfully refunded ${refund_data.total_price} "
                                                  f"to user with ID{refund_data.telegram_id} "
                                                  f"for purchasing {refund_data.quantity} "
                                                  f"{refund_data.subcategory}</b>", parse_mode=ParseMode.HTML)


async def send_db_file(callback: CallbackQuery):
    with open(f"./data/{config.DB_NAME}", "rb") as f:
        await callback.message.bot.send_document(callback.from_user.id,
                                                 types.BufferedInputFile(file=f.read(), filename="database.db"))
    await callback.answer()


@admin_router.callback_query(AdminIdFilter(), AdminCallback.filter())
async def admin_menu_navigation(callback: CallbackQuery, state: FSMContext, callback_data: AdminCallback):
    current_level = callback_data.level

    levels = {
        0: admin,
        1: send_to_everyone,
        2: confirm_and_send,
        3: decline_action,
        4: add_items,
        6: send_db_file,
        5: send_restocking_message,
        7: delete_category,
        8: delete_subcategory,
        9: delete_confirmation,
        10: confirm_and_delete,
        11: send_refund_menu,
        12: refund_confirmation,
        13: make_refund,
        14: pick_statistics_entity,
        15: pick_statistics_timedelta,
        16: get_statistics
    }

    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
