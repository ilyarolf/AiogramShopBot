import json
from pathlib import Path

from enums.bot_entity import BotEntity
from enums.language import Language


class Localizator:
    _i18n_dir = Path("./i18n")
    _cache: dict[Language, dict] = {}

    @classmethod
    def _load_language(cls, language: Language) -> dict:
        cached = cls._cache.get(language)
        if cached is not None:
            return cached
        path = cls._i18n_dir / f"{language.value}.json"
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        cls._cache[language] = data
        return data

    @classmethod
    def get_text(cls, language: Language, entity: BotEntity, key: str) -> str:
        try:
            language_payload = cls._load_language(language)
            return language_payload[entity.name.lower()][key]
        except KeyError:
            if language == Language.EN:
                raise
            return cls.get_text(Language.EN, entity, key)

    @classmethod
    def get_all_texts(cls, entity: BotEntity, key: str) -> set[str]:
        localized_texts = set()
        for locale_file in cls._i18n_dir.glob("*.json"):
            try:
                language = Language(locale_file.stem)
            except ValueError:
                continue
            localized_texts.add(cls.get_text(language, entity, key))
        return localized_texts

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()
