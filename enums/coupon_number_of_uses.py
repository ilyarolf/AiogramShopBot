from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class CouponNumberOfUses(str, Enum):
    INFINITY = "INFINITY"
    SINGLE = "SINGLE"

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.ADMIN, f"{self.value.lower()}_usage")

    def __str__(self):
        return self.value
