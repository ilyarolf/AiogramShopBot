from enum import Enum


class Currency(Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    CAD = "CAD"
    GBP = "GBP"

    @classmethod
    def from_string(cls, currency_str):
        try:
            return cls(currency_str.upper())
        except KeyError:
            raise ValueError(f"Not supported currency: {currency_str}")
