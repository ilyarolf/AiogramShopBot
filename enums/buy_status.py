from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class BuyStatus(Enum):
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    REFUNDED = "REFUNDED"

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, self.value.lower())
