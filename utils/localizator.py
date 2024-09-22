import json
import config


class Localizator:
    localization_filename = f"./l10n/{config.LANGUAGE}.json"

    @staticmethod
    def get_text_from_key(key: str) -> str:
        with open(Localizator.localization_filename, "r", encoding="UTF-8") as f:
            return json.loads(f.read())[key]
