import asyncio
import inspect
import logging
from typing import Union

from aiogram import types, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import bot
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


admin_router = Router()


def create_admin_callback(level: int, action: str = "", args_to_action: str = ""):
    return AdminCallback(level=level, action=action, args_to_action=args_to_action).pack()


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
    async def get_back_button(current_level: int) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton(text="Back", callback_data=create_admin_callback(level=current_level - 1))


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
    admin_menu_builder.button(text="Get new users",
                              callback_data=create_admin_callback(
                                  level=6,
                                  action="get_new_users"
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
        telegram_ids = await UserService.get_users_tg_ids()
        for telegram_id in telegram_ids:
            try:
                await callback.message.copy_to(telegram_id, reply_markup=None)
                counter += 1
                await asyncio.sleep(1.5)
            except Exception as e:
                logging.error(e)
        message_text = f"<b>Message sent to {counter} out of {len(telegram_ids)} people</b>"
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


async def get_new_users(callback: CallbackQuery):
    users_builder = InlineKeyboardBuilder()
    new_users = await UserService.get_new_users()
    for user in new_users:
        if user.telegram_username:
            user_button = types.InlineKeyboardButton(text=user.telegram_username, url=f"t.me/{user.telegram_username}")
            users_builder.add(user_button)
    users_builder.add(AdminConstants.back_to_main_button)
    users_builder.adjust(1)
    await callback.message.edit_text(text=f"{len(new_users)} new users:", reply_markup=users_builder.as_markup())


async def delete_category(callback: CallbackQuery):
    current_level = AdminCallback.unpack(callback.data).level
    categories = await CategoryService.get_all_categories()
    delete_category_builder = InlineKeyboardBuilder()
    for category in categories:
        category_name = category.name
        delete_category_callback = create_admin_callback(level=current_level + 2, action="delete_category",
                                                         args_to_action=category.id)
        delete_category_button = types.InlineKeyboardButton(text=category_name, callback_data=delete_category_callback)
        delete_category_builder.add(delete_category_button)
    delete_category_builder.add(AdminConstants.back_to_main_button)
    delete_category_builder.adjust(1)
    await callback.message.edit_text(text="<b>Categories:</b>", parse_mode=ParseMode.HTML,
                                     reply_markup=delete_category_builder.as_markup())


async def delete_subcategory(callback: CallbackQuery):
    current_level = AdminCallback.unpack(callback.data).level
    subcategories = await SubcategoryService.get_all()
    delete_subcategory_builder = InlineKeyboardBuilder()
    for subcategory in subcategories:
        delete_category_callback = create_admin_callback(level=current_level + 1, action="delete_subcategory",
                                                         args_to_action=subcategory.id)
        delete_category_button = types.InlineKeyboardButton(text=subcategory.name,
                                                            callback_data=delete_category_callback)
        delete_subcategory_builder.add(delete_category_button)
    delete_subcategory_builder.add(AdminConstants.back_to_main_button)
    delete_subcategory_builder.adjust(1)
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
        #TODO("Implement cascade delete subcategories, items with subcategories by category")
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


async def make_refund_markup():
    refund_builder = InlineKeyboardBuilder()
    not_refunded_buy_ids = await BuyService.get_not_refunded_buy_ids()
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
    refund_builder.add(AdminConstants.back_to_main_button)
    refund_builder.adjust(1)
    return refund_builder.as_markup()


async def send_refund_menu(callback: CallbackQuery):
    refund_markup = await make_refund_markup()
    await callback.message.edit_text(text="<b>Refund menu:</b>", reply_markup=refund_markup, parse_mode=ParseMode.HTML)


async def refund_confirmation(callback: CallbackQuery):
    unpacked_callback = AdminCallback.unpack(callback.data)
    current_level = unpacked_callback.level
    buy_id = int(unpacked_callback.args_to_action)
    back_button = await AdminConstants.get_back_button(current_level)
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


@admin_router.callback_query(AdminIdFilter(), AdminCallback.filter())
async def admin_menu_navigation(callback: CallbackQuery, state: FSMContext, callback_data: AdminCallback):
    current_level = callback_data.level

    levels = {
        0: admin,
        1: send_to_everyone,
        2: confirm_and_send,
        3: decline_action,
        4: add_items,
        5: send_restocking_message,
        6: get_new_users,
        7: delete_category,
        8: delete_subcategory,
        9: delete_confirmation,
        10: confirm_and_delete,
        11: send_refund_menu,
        12: refund_confirmation,
        13: make_refund,
    }

    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
