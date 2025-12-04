from enum import Enum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    CAD = "CAD"
    GBP = "GBP"

    def get_localized_symbol(self):
        return Localizator.get_text(BotEntity.COMMON, f"{self.value.lower()}_symbol")

    def get_localized_text(self):
        return Localizator.get_text(BotEntity.COMMON, f"{self.value.lower()}_text")
