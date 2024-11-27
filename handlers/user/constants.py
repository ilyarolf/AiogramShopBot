from aiogram import types

from callbacks import AllCategoriesCallback
from utils.localizator import Localizator, BotEntity


class UserConstants:
    ALL_CATEGORIES_BUTTON = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.USER,
                                                                                 "all_categories"),
                                                       callback_data=AllCategoriesCallback.create(0).pack())
