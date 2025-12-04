import json
import config
from enums.bot_entity import BotEntity


class Localizator:
    localization_filename = f"./l10n/{config.BOT_LANGUAGE}.json"

    @staticmethod
    def get_text(entity: BotEntity, key: str) -> str:
        with open(Localizator.localization_filename, "r", encoding="UTF-8") as f:
            return json.loads(f.read())[entity.name.lower()][key]

