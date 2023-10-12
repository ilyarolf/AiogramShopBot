import asyncio
import logging
from typing import Union

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.callback_data import CallbackData

from models.user import User
from utils.new_items_manager import NewItemsManager

admin_callback = CallbackData("admin", "level", "action", "args_to_action")


def create_admin_callback(level: int, action: str = "", args_to_action: str = ""):
    return admin_callback.new(level=level, action=action, args_to_action=args_to_action)


async def admin_command_handler(message: types.message):
    await admin(message)


async def admin(message: Union[Message, CallbackQuery]):
    current_level = 0
    admin_menu_buttons = types.InlineKeyboardMarkup(row_width=2)
    admin_send_to_everyone = types.InlineKeyboardButton("Send to everyone",
                                                        callback_data=create_admin_callback(level=current_level + 1,
                                                                                            action="send_to_everyone"))
    add_items_button = types.InlineKeyboardButton("Add items",
                                                  callback_data=create_admin_callback(level=current_level + 4,
                                                                                      action="add_items"))
    send_restocking_message_button = types.InlineKeyboardButton("Send restocking message",
                                                                callback_data=create_admin_callback(
                                                                    level=current_level + 5,
                                                                    action="send_to_everyone"))
    admin_menu_buttons.add(admin_send_to_everyone, add_items_button, send_restocking_message_button)
    if isinstance(message, Message):
        await message.answer("<b>Admin Menu:</b>", parse_mode='html',
                             reply_markup=admin_menu_buttons)
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text("<b>Admin Menu:</b>", parse_mode='html', reply_markup=admin_menu_buttons)


class AdminStates(StatesGroup):
    message_to_send = State()
    new_items_file = State()
    send_restocking_message = State()


async def send_to_everyone(callback: CallbackQuery):
    await callback.message.edit_text("<b>Send a message to the newsletter</b>:", parse_mode='html')
    await AdminStates.message_to_send.set()


async def get_message_to_sending(message: types.message, state: FSMContext):
    confirmation_markup = types.InlineKeyboardMarkup()
    confirm_button = types.InlineKeyboardButton(text="Confirm", callback_data=create_admin_callback(level=2,
                                                                                                    action="confirm"))
    decline_button = types.InlineKeyboardButton(text="Decline", callback_data=create_admin_callback(level=3,
                                                                                                    action="decline"))
    confirmation_markup.add(confirm_button, decline_button)
    await message.send_copy(message.chat.id, reply_markup=confirmation_markup)
    await state.finish()


async def confirm_and_send(callback: CallbackQuery):
    confirmed = admin_callback.parse(callback.data)['action'] == 'confirm'
    await callback.message.edit_reply_markup(None)
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
        await callback.message.answer(text=f"<b>Message sent to {counter} out of {len(telegram_ids)} people</b>",
                                      parse_mode='html')


async def decline_sending(callback: CallbackQuery):
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
    await callback.message.answer(message, parse_mode='html')


async def admin_menu_navigation(callback: CallbackQuery, callback_data: dict):
    current_level = callback_data.get("level")

    levels = {
        "0": admin,
        "1": send_to_everyone,
        "2": confirm_and_send,
        "3": decline_sending,
        "4": add_items,
        "5": send_restocking_message,
    }

    current_level_function = levels[current_level]
    await current_level_function(callback)
