import asyncio
import logging
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.callback_data import CallbackData

from models.buy import Buy
from models.item import Item
from models.user import User
from utils.new_items_manager import NewItemsManager
from utils.notification_manager import NotificationManager
from utils.other_sql import OtherSQLQuery

admin_callback = CallbackData("admin", "level", "action", "args_to_action")


def create_admin_callback(level: int, action: str = "", args_to_action: str = ""):
    return admin_callback.new(level=level, action=action, args_to_action=args_to_action)


class AdminConstants:
    confirmation_markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text="Confirm", callback_data=create_admin_callback(level=2,
                                                                                                    action="confirm"))
    decline_button = types.InlineKeyboardButton(text="Decline", callback_data=create_admin_callback(level=3,
                                                                                                    action="decline"))
    confirmation_markup.add(confirm_button, decline_button)
    back_to_main_button = types.InlineKeyboardButton(text="Back to admin menu",
                                                     callback_data=create_admin_callback(level=0))

    @staticmethod
    async def get_back_button(current_level: int) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton("Back", callback_data=create_admin_callback(level=current_level - 1))


async def admin_command_handler(message: types.message):
    await admin(message)


async def admin(message: Union[Message, CallbackQuery]):
    current_level = 0
    admin_menu_buttons = types.InlineKeyboardMarkup(row_width=2)
    admin_send_to_everyone = types.InlineKeyboardButton("Send to everyone",
                                                        callback_data=create_admin_callback(level=1,
                                                                                            action="send_to_everyone"))
    add_items_button = types.InlineKeyboardButton("Add items",
                                                  callback_data=create_admin_callback(level=4,
                                                                                      action="add_items"))
    send_restocking_message_button = types.InlineKeyboardButton("Send restocking message",
                                                                callback_data=create_admin_callback(
                                                                    level=5,
                                                                    action="send_to_everyone"))
    get_new_users_button = types.InlineKeyboardButton("Get new users",
                                                      callback_data=create_admin_callback(
                                                          level=6,
                                                          action="get_new_users"
                                                      ))
    delete_category_button = types.InlineKeyboardButton("Delete category",
                                                        callback_data=create_admin_callback(
                                                            level=7
                                                        ))
    delete_subcategory_button = types.InlineKeyboardButton("Delete subcategory",
                                                           callback_data=create_admin_callback(
                                                               level=8
                                                           ))
    refund_button = types.InlineKeyboardButton("Make refund",
                                               callback_data=create_admin_callback(
                                                   level=11
                                               ))
    admin_menu_buttons.add(admin_send_to_everyone, add_items_button, send_restocking_message_button,
                           get_new_users_button, delete_category_button, delete_subcategory_button,
                           refund_button)
    if isinstance(message, Message):
        await message.answer("<b>Admin Menu:</b>", parse_mode='html',
                             reply_markup=admin_menu_buttons)
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text("<b>Admin Menu:</b>", parse_mode='html', reply_markup=admin_menu_buttons)


class AdminStates(StatesGroup):
    message_to_send = State()
    new_items_file = State()


async def send_to_everyone(callback: CallbackQuery):
    await callback.message.edit_text("<b>Send a message to the newsletter</b>:", parse_mode='html')
    await AdminStates.message_to_send.set()


async def get_message_to_sending(message: types.message, state: FSMContext):
    await message.send_copy(message.chat.id, reply_markup=AdminConstants.confirmation_markup)
    await state.finish()


async def confirm_and_send(callback: CallbackQuery):
    await callback.answer(text="Sending started")
    confirmed = admin_callback.parse(callback.data)['action'] == 'confirm'
    is_caption = callback.message.caption
    is_restocking = callback.message.text and callback.message.text.__contains__("📅 Update")
    if confirmed:
        counter = 0
        telegram_ids = User.get_users_tg_ids()
        for telegram_id in telegram_ids:
            telegram_id = telegram_id['telegram_id']
            try:
                await callback.message.copy_to(telegram_id, reply_markup=None)
                counter += 1
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(e)
        message_text = f"<b>Message sent to {counter} out of {len(telegram_ids)} people</b>"
        if is_caption:
            # TODO("Fix bug with messages with images")
            await callback.message.delete()
            await callback.message.answer(text=message_text, parse_mode='html')
        await callback.message.edit_text(
            text=message_text,
            parse_mode='html')
    if is_restocking:
        Item.set_items_not_new()


async def decline_action(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(text="<b>Declined!</b>", parse_mode='html')


async def add_items(callback: CallbackQuery):
    await callback.message.edit_text(text="<b>Send .json file with new items or type \"cancel\" for cancel.</b>",
                                     parse_mode="html")
    await AdminStates.new_items_file.set()


async def receive_new_items_file(message: types.message, state: FSMContext):
    if message.document:
        await state.finish()
        file_name = "new_items.json"
        await message.document.download(destination_file=file_name)
        adding_result = NewItemsManager.add(file_name)
        if isinstance(adding_result, BaseException):
            await message.answer(text=f"<b>Exception:</b>\n<code>{adding_result}</code>", parse_mode='html')
        elif type(adding_result) is int:
            await message.answer(text=f"<b>Successfully added {adding_result} items!</b>", parse_mode='html')
    elif message.text and message.text.lower() == "cancel":
        await state.finish()
        await message.answer("<b>Adding items successfully cancelled!</b>", parse_mode='html')
    else:
        await message.answer(text="<b>Send .json file with new items or type \"cancel\" for cancel.</b>",
                             parse_mode="html")


async def send_restocking_message(callback: CallbackQuery):
    message = NewItemsManager.generate_restocking_message()
    await callback.message.answer(message, parse_mode='html', reply_markup=AdminConstants.confirmation_markup)


async def get_new_users(callback: CallbackQuery):
    users_markup = types.InlineKeyboardMarkup()
    new_users = User.get_new_users()
    for user in new_users:
        if user.telegram_username:
            user_button = types.InlineKeyboardButton(user.telegram_username, url=f"t.me/{user.telegram_username}")
            users_markup.add(user_button)
    users_markup.add(AdminConstants.back_to_main_button)
    await callback.message.edit_text(text=f"{len(new_users)} new users:", reply_markup=users_markup)


async def delete_category(callback: CallbackQuery):
    current_level = int(admin_callback.parse(callback.data)['level'])
    categories = Item.get_categories()
    delete_category_markup = types.InlineKeyboardMarkup()
    for category in categories:
        category_name = category['category']
        delete_category_callback = create_admin_callback(level=current_level + 2, action="delete_category",
                                                         args_to_action=category_name)
        delete_category_button = types.InlineKeyboardButton(text=category_name, callback_data=delete_category_callback)
        delete_category_markup.add(delete_category_button)
    delete_category_markup.add(AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>Categories:</b>", parse_mode='html', reply_markup=delete_category_markup)


async def delete_subcategory(callback: CallbackQuery):
    current_level = int(admin_callback.parse(callback.data)['level'])
    subcategories = Item.get_all_subcategories()
    delete_subcategory_markup = types.InlineKeyboardMarkup()
    for subcategory in subcategories:
        subcategory_name = subcategory['subcategory']
        delete_category_callback = create_admin_callback(level=current_level + 1, action="delete_subcategory",
                                                         args_to_action=subcategory_name)
        delete_category_button = types.InlineKeyboardButton(text=subcategory_name,
                                                            callback_data=delete_category_callback)
        delete_subcategory_markup.add(delete_category_button)
    delete_subcategory_markup.add(AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>Subcategories:</b>", parse_mode='html',
                                     reply_markup=delete_subcategory_markup)


async def delete_confirmation(callback: CallbackQuery):
    current_level = int(admin_callback.parse(callback.data)['level'])
    action = admin_callback.parse(callback.data)['action']
    args_to_action = admin_callback.parse(callback.data)['args_to_action']
    delete_markup = types.InlineKeyboardMarkup()
    confirm_callback = create_admin_callback(level=current_level + 1,
                                             action=f"confirmed_{action}",
                                             args_to_action=args_to_action)
    confirm_button = types.InlineKeyboardButton(text="Confirm", callback_data=confirm_callback)
    decline_callback = create_admin_callback(level=current_level - 6)
    decline_button = types.InlineKeyboardButton(text="Decline", callback_data=decline_callback)
    delete_markup.add(confirm_button, decline_button)
    entity_to_delete = action.split('_')[-1]
    if entity_to_delete == "category":
        category_name = args_to_action
        await callback.message.edit_text(text=f"<b>Do you really want to delete the category {category_name}?</b>",
                                         parse_mode='html',
                                         reply_markup=delete_markup)
    elif entity_to_delete == "subcategory":
        subcategory_name = args_to_action
        await callback.message.edit_text(
            text=f"<b>Do you really want to delete the subcategory {subcategory_name}?</b>",
            parse_mode='html',
            reply_markup=delete_markup)


async def confirm_and_delete(callback: CallbackQuery):
    args_to_action = admin_callback.parse(callback.data)['args_to_action']
    entity_to_delete = admin_callback.parse(callback.data)['action'].split('_')[-1]
    back_to_main_markup = types.InlineKeyboardMarkup()
    back_to_main_markup.add(AdminConstants.back_to_main_button)
    message_text = f"<b>Successfully deleted {args_to_action} {entity_to_delete}!</b>"
    if entity_to_delete == "category":
        Item.delete_category(args_to_action)
        await callback.message.edit_text(text=message_text,
                                         parse_mode='html', reply_markup=back_to_main_markup)
    elif entity_to_delete == "subcategory":
        Item.delete_subcategory(args_to_action)
        await callback.message.edit_text(text=message_text,
                                         parse_mode='html', reply_markup=back_to_main_markup)


async def make_refund_markup():
    refund_markup = types.InlineKeyboardMarkup()
    not_refunded_buy_ids = Buy.get_not_refunded_buy_ids()
    refund_data = OtherSQLQuery.get_refund_data(not_refunded_buy_ids)
    for buy in refund_data:
        refund_buy_button = types.InlineKeyboardButton(
            text=f"{buy.telegram_username}|${buy.total_price}|{buy.subcategory}",
            callback_data=create_admin_callback(level=12,
                                                action="make_refund",
                                                args_to_action=buy.buy_id))
        refund_markup.add(refund_buy_button)
    return refund_markup


async def send_refund_menu(callback: CallbackQuery):
    refund_markup = await make_refund_markup()
    refund_markup.add(AdminConstants.back_to_main_button)
    await callback.message.edit_text(text="<b>Refund menu:</b>", reply_markup=refund_markup, parse_mode='html')


async def refund_confirmation(callback: CallbackQuery):
    current_level = int(admin_callback.parse(callback.data)['level'])
    buy_id = int(admin_callback.parse(callback.data)['args_to_action'])
    back_button = await AdminConstants.get_back_button(current_level)
    confirm_button = types.InlineKeyboardButton(text="Confirm",
                                                callback_data=create_admin_callback(level=current_level + 1,
                                                                                    action="confirm_refund",
                                                                                    args_to_action=str(buy_id)))

    confirmation_markup = types.InlineKeyboardMarkup()
    confirmation_markup.add(confirm_button, AdminConstants.decline_button, back_button)
    refund_data = OtherSQLQuery.get_refund_data_single(buy_id)
    if refund_data.telegram_username:
        await callback.message.edit_text(
            text=f"<b>Do you really want to refund user @{refund_data.telegram_username} "
                 f"for purchasing {refund_data.quantity} {refund_data.subcategory} "
                 f"in the amount of ${refund_data.total_price}</b>", parse_mode='html',
            reply_markup=confirmation_markup)
    else:
        await callback.message.edit_text(
            text=f"<b>Do you really want to refund user with ID:{refund_data.telegram_id} "
                 f"for purchasing {refund_data.quantity} {refund_data.subcategory} "
                 f"in the amount of ${refund_data.total_price}</b>", parse_mode='html',
            reply_markup=confirmation_markup)


async def make_refund(callback: CallbackQuery):
    buy_id = int(admin_callback.parse(callback.data)['args_to_action'])
    is_confirmed = admin_callback.parse(callback.data)['action'] == "confirm_refund"
    if is_confirmed:
        refund_data = OtherSQLQuery.get_refund_data_single(buy_id)
        Buy.refund(buy_id, refund_data)
        await NotificationManager.send_refund_message(refund_data)
        if refund_data.telegram_username:
            await callback.message.edit_text(text=f"<b>Successfully refunded ${refund_data.total_price} "
                                                  f"to user {refund_data.telegram_username} "
                                                  f"for purchasing {refund_data.quantity} "
                                                  f"{refund_data.subcategory}</b>", parse_mode='html')
        else:
            await callback.message.edit_text(text=f"<b>Successfully refunded ${refund_data.total_price} "
                                                  f"to user with ID{refund_data.telegram_id} "
                                                  f"for purchasing {refund_data.quantity} "
                                                  f"{refund_data.subcategory}</b>", parse_mode='html')


async def admin_menu_navigation(callback: CallbackQuery, callback_data: dict):
    current_level = callback_data.get("level")

    levels = {
        "0": admin,
        "1": send_to_everyone,
        "2": confirm_and_send,
        "3": decline_action,
        "4": add_items,
        "5": send_restocking_message,
        "6": get_new_users,
        "7": delete_category,
        "8": delete_subcategory,
        "9": delete_confirmation,
        "10": confirm_and_delete,
        "11": send_refund_menu,
        "12": refund_confirmation,
        "13": make_refund,
    }

    current_level_function = levels[current_level]
    await current_level_function(callback)
