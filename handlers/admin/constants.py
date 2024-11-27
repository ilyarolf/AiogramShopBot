from aiogram import types
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import AdminMenuCallback, AdminInventoryManagementCallback, AdminAnnouncementCallback
from utils.localizator import Localizator, BotEntity


class AdminConstants:
    back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
                                                                               "back_to_menu"),
                                                     callback_data=AdminMenuCallback.create(level=0).pack())


class AdminAnnouncementsConstants:
    # TODO(move to constants)
    confirmation_builder = InlineKeyboardBuilder()
    confirmation_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                                callback_data=AdminAnnouncementCallback.create(3))
    confirmation_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                                callback_data=AdminAnnouncementCallback.create(0))


class AdminInventoryManagementStates(StatesGroup):
    document = State()
    category = State()
    subcategory = State()
    price = State()
    description = State()
    private_data = State()


class AdminAnnouncementStates(StatesGroup):
    announcement_msg = State()


class UserManagementStates(StatesGroup):
    balance_amount = State()
    user_entity = State()