from enum import Enum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class CouponNumberOfUses(str, Enum):
    INFINITY = "INFINITY"
    SINGLE = "SINGLE"

    def get_localized(self):
        return Localizator.get_text(BotEntity.ADMIN, f"{self.value.lower()}_usage")

    def __str__(self):
        return self.value
