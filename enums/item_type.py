from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class ItemType(Enum):
    DIGITAL = "DIGITAL"
    PHYSICAL = "PHYSICAL"

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, self.value.lower())

    @staticmethod
    def _normalize_input(value: str) -> str:
        return "".join(char for char in value.casefold().strip() if char.isalnum())

    @classmethod
    def from_input(cls, value: str, language: Language) -> 'ItemType':
        normalized_value = cls._normalize_input(value)
        for item_type in cls:
            candidates = {
                cls._normalize_input(item_type.value),
                cls._normalize_input(item_type.get_localized(language)),
            }
            if normalized_value in candidates:
                return item_type

        raise ValueError(f"{value!r} is not a valid ItemType")
