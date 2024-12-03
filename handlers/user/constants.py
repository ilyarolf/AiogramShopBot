from aiogram import types

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class UserConstants:
    ALL_CATEGORIES_BUTTON = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.USER,
                                                                                 "all_categories"),
                                                       callback_data=AllCategoriesCallback.create(0).pack())
