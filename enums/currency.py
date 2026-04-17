from enum import Enum

from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    CNY = "CNY"
    HKD = "HKD"
    SGD = "SGD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    PLN = "PLN"
    CZK = "CZK"
    HUF = "HUF"
    TRY = "TRY"
    INR = "INR"
    KRW = "KRW"
    THB = "THB"
    IDR = "IDR"
    MYR = "MYR"
    PHP = "PHP"
    VND = "VND"
    AED = "AED"
    SAR = "SAR"
    ZAR = "ZAR"
    NGN = "NGN"
    KES = "KES"
    GHS = "GHS"
    BRL = "BRL"
    MXN = "MXN"
    ARS = "ARS"
    CLP = "CLP"
    COP = "COP"
    PEN = "PEN"
    RUB = "RUB"
    UAH = "UAH"
    ILS = "ILS"
    PKR = "PKR"
    BDT = "BDT"
    LKR = "LKR"
    TWD = "TWD"
    BHD = "BHD"
    KWD = "KWD"
    RON = "RON"
    NZD = "NZD"

    def get_localized_symbol(self):
        return get_text(Language.EN, BotEntity.COMMON, f"{self.value.lower()}_symbol")

    def get_localized_text(self):
        return get_text(Language.EN, BotEntity.COMMON, f"{self.value.lower()}_text")
