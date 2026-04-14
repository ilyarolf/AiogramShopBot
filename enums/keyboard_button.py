from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.localizator import Localizator
from utils.utils import get_text


class KeyboardButton(Enum):
    ALL_CATEGORIES = "ALL_CATEGORIES"
    MY_PROFILE = "MY_PROFILE"
    FAQ = "FAQ"
    HELP = "HELP"
    REVIEWS = "REVIEWS"
    CART = "CART"
    ADMIN_MENU = "MENU"

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, "button")

    @staticmethod
    def get_localized_set(button: 'KeyboardButton') -> set[str]:
        bot_entity = BotEntity.ADMIN if button == KeyboardButton.ADMIN_MENU else BotEntity.USER
        return Localizator.get_all_texts(bot_entity, button.value.lower())
