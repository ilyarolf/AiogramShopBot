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

    def get_receiver_addr(self):
        match self:
            case Cryptocurrency.BTC:
                return config.BTC_RECEIVER_ADDR
            case Cryptocurrency.LTC:
                return config.LTC_RECEIVER_ADDR
            case Cryptocurrency.ETH:
                return config.ETH_RECEIVER_ADDR
            case Cryptocurrency.BNB:
                return config.BNB_RECEIVER_ADDR
            case Cryptocurrency.SOL:
                return config.SOL_RECEIVER_ADDR
