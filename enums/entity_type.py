from enum import IntEnum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class EntityType(IntEnum):
    CATEGORY = 1
    SUBCATEGORY = 2
    ITEM = 3
    USER = 4

    def get_localized(self):
        match self:
            case EntityType.CATEGORY:
                return Localizator.get_text(BotEntity.COMMON, "category")
            case EntityType.SUBCATEGORY:
                return Localizator.get_text(BotEntity.COMMON, "subcategory")
            case EntityType.ITEM:
                return Localizator.get_text(BotEntity.COMMON, "item")
            case EntityType.USER:
                return Localizator.get_text(BotEntity.COMMON, "user")
