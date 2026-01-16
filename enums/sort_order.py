from enum import IntEnum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class SortOrder(IntEnum):
    ASC = 0
    DESC = 1
    DISABLE = 2

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, self.name.lower())

    def next(self):
        next_value = (self.value + 1) % len(SortOrder)
        return SortOrder(next_value)
