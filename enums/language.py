from enum import Enum


class Language(str, Enum):
    EN = "en"
    FR = "fr"
    DE = "de"
    IT = "it"
    ZH = "zh"

    @staticmethod
    def from_locale(locale: str) -> 'Language':
        try:
            return Language(locale.lower())
        except ValueError:
            return Language.EN

    def get_country_code(self):
        match self:
            case Language.EN:
                return "US"
            case Language.ZH:
                return "CN"
            case _:
                return self.name

    def get_flag_emoji(self):
        if len(self) != 2:
            return "❓"
        regional_A = 0x1F1E6
        flag_chars = []
        for char in self.get_country_code():
            if 'A' <= char <= 'Z':
                flag_char = chr(regional_A + ord(char) - ord('A'))
                flag_chars.append(flag_char)
            else:
                return "❓"
        return ''.join(flag_chars)
