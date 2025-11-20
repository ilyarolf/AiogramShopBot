from enum import IntEnum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class SortProperty(IntEnum):
    NAME = 1
    PRICE = 2

    def get_localized(self):
        return f"{Localizator.get_text(BotEntity.COMMON, "sort")}{Localizator.get_text(BotEntity.COMMON, self.name.lower())}"
