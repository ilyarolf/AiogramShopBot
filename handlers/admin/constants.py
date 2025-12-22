from aiogram.types import InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import AdminMenuCallback, AnnouncementCallback, AnnouncementType
from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class AdminConstants:
    @staticmethod
    def back_to_main_button(language: Language):
        return InlineKeyboardButton(text=get_text(language, BotEntity.ADMIN, "back_to_menu"),
                                    callback_data=AdminMenuCallback.create(level=0).pack())


class AnnouncementsConstants:
    @staticmethod
    def get_confirmation_builder(announcement_type: AnnouncementType, language: Language) -> InlineKeyboardBuilder:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "confirm"),
                          callback_data=AnnouncementCallback.create(level=3,
                                                                    announcement_type=announcement_type))
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
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
    coupon_name = State()
    coupon_value = State()


class ShippingManagementStates(StatesGroup):
    shipping_name = State()
    shipping_price = State()
    edit_property = State()


class BuysManagementStates(StatesGroup):
    update_track_number = State()
