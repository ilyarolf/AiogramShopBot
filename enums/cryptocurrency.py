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
