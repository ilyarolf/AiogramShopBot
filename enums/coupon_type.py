from enum import Enum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class CouponType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"

    def get_localized(self) -> str:
        return Localizator.get_text(BotEntity.ADMIN, f"{self.value.lower()}_coupon")

    def __str__(self):
        return self.value
