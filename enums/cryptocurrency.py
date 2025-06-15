from enum import Enum

import config


class Cryptocurrency(str, Enum):
    BNB = "BNB"
    BTC = "BTC"
    LTC = "LTC"
    ETH = "ETH"
    SOL = "SOL"

    def get_divider(self):
        match self:
            case Cryptocurrency.BTC:
                return 8
            case Cryptocurrency.LTC:
                return 8
            case Cryptocurrency.ETH:
                return 18
            case Cryptocurrency.SOL:
                return 9
            case Cryptocurrency.BNB:
                return 18

    def get_coingecko_name(self) -> str:
        match self:
            case Cryptocurrency.BTC:
                return "bitcoin"
            case Cryptocurrency.LTC:
                return "litecoin"
            case Cryptocurrency.ETH:
                return "ethereum"
            case Cryptocurrency.BNB:
                return "binancecoin"
            case Cryptocurrency.SOL:
                return "solana"
