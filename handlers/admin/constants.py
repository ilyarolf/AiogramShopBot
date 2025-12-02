from aiogram.types import InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import AdminMenuCallback, AnnouncementCallback, AnnouncementType
from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class AdminConstants:
    back_to_main_button = InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
                                                                         "back_to_menu"),
                                               callback_data=AdminMenuCallback.create(level=0).pack())


class AnnouncementsConstants:
    @staticmethod
    def get_confirmation_builder(announcement_type: AnnouncementType) -> InlineKeyboardBuilder:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=AnnouncementCallback.create(level=3,
                                                                    announcement_type=announcement_type))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=AnnouncementCallback.create(level=0))
        return kb_builder


class InventoryManagementStates(StatesGroup):
    document = State()
    category = State()
    subcategory = State()
    description = State()
    price = State()
    private_data = State()
    filter_entity = State()


class AnnouncementStates(StatesGroup):
    announcement_msg = State()


class UserManagementStates(StatesGroup):
    balance_amount = State()
    user_entity = State()
    filter_username = State()


class WalletStates(StatesGroup):
    crypto_address = State()


class MediaManagementStates(StatesGroup):
    media = State()
    filter_entity = State()


class CouponsManagementStates(StatesGroup):
    coupon_value = State()
