from aiogram import types
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import AdminMenuCallback, AdminAnnouncementCallback, AnnouncementType
from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class AdminConstants:
    back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
                                                                               "back_to_menu"),
                                                     callback_data=AdminMenuCallback.create(level=0).pack())


class AdminAnnouncementsConstants:
    @staticmethod
    def get_confirmation_builder(announcement_type: AnnouncementType) -> InlineKeyboardBuilder:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=AdminAnnouncementCallback.create(3, announcement_type))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=AdminAnnouncementCallback.create(0))
        return kb_builder


class AdminInventoryManagementStates(StatesGroup):
    document = State()


class AdminAnnouncementStates(StatesGroup):
    announcement_msg = State()


class UserManagementStates(StatesGroup):
    balance_amount = State()
    user_entity = State()
