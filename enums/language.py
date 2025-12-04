from enum import Enum


class Language(str, Enum):
    EN = "en"
    FR = "fr"
    DE = "de"
    IT = "it"

    @staticmethod
    def from_locale(locale: str) -> 'Language':
        try:
            return Language(locale.lower())
        except ValueError:
            return Language.EN
