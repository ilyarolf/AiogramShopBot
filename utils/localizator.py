import json
import config
from enums.bot_entity import BotEntity


class Localizator:
    localization_filename = f"./l10n/{config.BOT_LANGUAGE}.json"

    @staticmethod
    def get_text(entity: BotEntity, key: str) -> str:
        with open(Localizator.localization_filename, "r", encoding="UTF-8") as f:
            if entity == BotEntity.ADMIN:
                return json.loads(f.read())["admin"][key]
            elif entity == BotEntity.USER:
                return json.loads(f.read())["user"][key]
            else:
                return json.loads(f.read())["common"][key]

    @staticmethod
    def get_currency_symbol():
        return Localizator.get_text(BotEntity.COMMON, f"{config.CURRENCY.value.lower()}_symbol")

    @staticmethod
    def get_currency_text():
        return Localizator.get_text(BotEntity.COMMON, f"{config.CURRENCY.value.lower()}_text")
