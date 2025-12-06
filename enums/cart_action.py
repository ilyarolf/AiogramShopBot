from enum import IntEnum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class CartAction(IntEnum):
    MINUS_ONE = -1
    PLUS_ONE = 1
    REMOVE_ALL = 2
    MAX = 3

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, self.name.lower())
