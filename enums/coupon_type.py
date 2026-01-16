from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class CouponType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"

    def get_localized(self, language: Language) -> str:
        return get_text(language, BotEntity.ADMIN, f"{self.value.lower()}_coupon")

    def __str__(self):
        return self.value
