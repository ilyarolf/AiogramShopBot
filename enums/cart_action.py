from enum import IntEnum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class CartAction(IntEnum):
    MINUS_ONE = -1
    PLUS_ONE = 1
    REMOVE_ALL = 2
    MAX = 3

    def get_localized(self):
        return Localizator.get_text(BotEntity.COMMON, self.name.lower())
