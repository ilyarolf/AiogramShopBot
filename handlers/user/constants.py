from aiogram import types

from callbacks import AllCategoriesCallback, MyProfileCallback, BaseCallback
from utils.localizator import Localizator, BotEntity


class UserConstants:
    ALL_CATEGORIES_BUTTON = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.USER,
                                                                                 "all_categories"),
                                                       callback_data=AllCategoriesCallback.create(0).pack())

    @staticmethod
    def get_back_button(unpacked_callback: BaseCallback, lvl: int | None = None):
        if lvl is None:
            unpacked_callback.level = unpacked_callback.level - 1
        else:
            unpacked_callback.level = lvl
        return types.InlineKeyboardButton(
            text=Localizator.get_text(BotEntity.COMMON, "back_button"),
            callback_data=unpacked_callback.create(**unpacked_callback.model_dump()))
