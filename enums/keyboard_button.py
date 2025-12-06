import json
from enum import Enum
from pathlib import Path

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class KeyboardButton(Enum):
    ALL_CATEGORIES = "ALL_CATEGORIES"
    MY_PROFILE = "MY_PROFILE"
    FAQ = "FAQ"
    HELP = "HELP"
    CART = "CART"
    ADMIN_MENU = "MENU"

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, "button")

    @staticmethod
    def get_localized_set(button: 'KeyboardButton') -> set[str]:
        locale_files = list(Path("./i18n").glob("*.json"))
        localized = []
        bot_entity = BotEntity.ADMIN if button == KeyboardButton.ADMIN_MENU else BotEntity.USER
        for locale_file in locale_files:
            with locale_file.open("r", encoding="utf-8") as f:
                localized.append(json.loads(f.read())[bot_entity.name.lower()][button.value.lower()])
        return set(localized)
