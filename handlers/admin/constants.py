from aiogram import types

from callbacks import AdminMenuCallback, AdminInventoryManagementCallback
from utils.localizator import Localizator, BotEntity


class AdminConstants:
    back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
                                                                               "back_to_menu"),
                                                     callback_data=AdminMenuCallback.create(level=0).pack())


class InventoryManagementConstants:
    back_to_inventory_management = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.ADMIN,
                                                                                        "inventory_management"),
                                                              callback_data=AdminInventoryManagementCallback.create(
                                                                  level=0).pack())
