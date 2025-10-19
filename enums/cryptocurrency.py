from enum import Enum

import config


class Cryptocurrency(str, Enum):
    BNB = "BNB"
    BTC = "BTC"
    LTC = "LTC"
    ETH = "ETH"
    SOL = "SOL"
    USDT_TRC20 = "USDT_TRC20"
    USDT_ERC20 = "USDT_ERC20"
    USDC_ERC20 = "USDC_ERC20"

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
            case Cryptocurrency.USDT_TRC20:
                return 6
            case Cryptocurrency.USDT_ERC20:
                return 6
            case Cryptocurrency.USDC_ERC20:
                return 6

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
            case Cryptocurrency.USDT_TRC20 | Cryptocurrency.USDT_ERC20:
                return "tether"
            case Cryptocurrency.USDC_ERC20:
                return "usd-coin"
