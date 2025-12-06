from enum import IntEnum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class EntityType(IntEnum):
    CATEGORY = 1
    SUBCATEGORY = 2
    ITEM = 3
    USER = 4

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, self.name.lower())
