from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    CAD = "CAD"
    GBP = "GBP"

    def get_localized_symbol(self):
        return get_text(Language.EN, BotEntity.COMMON, f"{self.value.lower()}_symbol")

    def get_localized_text(self):
        return get_text(Language.EN, BotEntity.COMMON, f"{self.value.lower()}_text")
