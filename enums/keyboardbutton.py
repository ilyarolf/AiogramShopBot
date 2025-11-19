from enum import Enum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class KeyboardButton(Enum):
    ALL_CATEGORIES = "ALL_CATEGORIES"
    MY_PROFILE = "MY_PROFILE"
    FAQ = "FAQ"
    HELP = "HELP"
    CART = "CART"

    def get_localized(self):
        return Localizator.get_text(BotEntity.COMMON, "button")
