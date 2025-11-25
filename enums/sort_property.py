from enum import IntEnum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class SortProperty(IntEnum):
    NAME = 1
    PRICE = 2
    QUANTITY = 3
    BUY_DATETIME = 4
    TOTAL_PRICE = 5

    def get_localized(self):
        return f"{Localizator.get_text(BotEntity.COMMON, "sort")}{Localizator.get_text(BotEntity.COMMON, self.name.lower())}"

    def get_column(self, table):
        return getattr(table, self.name.lower())
