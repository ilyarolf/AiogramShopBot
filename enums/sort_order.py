from enum import Enum, IntEnum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class SortOrder(IntEnum):
    ASC = 0
    DESC = 1

    def get_localized(self):
        return Localizator.get_text(BotEntity.COMMON, self.name.lower())

