from enum import IntEnum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class SortProperty(IntEnum):
    NAME = 1
    PRICE = 2
    QUANTITY = 3
    BUY_DATETIME = 4
    TOTAL_PRICE = 5

    def get_localized(self, language: Language):
        return f"{get_text(language, BotEntity.COMMON, "sort")}{get_text(language, BotEntity.COMMON, self.name.lower())}"

    def get_column(self, table):
        return getattr(table, self.name.lower())
