from enums.bot_entity import BotEntity
from enums.language import Language
from utils.localizator import Localizator


def test_localizator_returns_text_from_json():
    assert Localizator.get_text(Language.EN, BotEntity.COMMON, "cancel") == "❌ Cancel"


def test_localizator_collects_all_localized_values():
    localized = Localizator.get_all_texts(BotEntity.COMMON, "cancel")
    assert "❌ Cancel" in localized
    assert len(localized) >= 2
