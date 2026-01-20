from enum import Enum

import config
from enums.bot_entity import BotEntity
from enums.language import Language
from utils.utils import get_text


class Cryptocurrency(str, Enum):
    BNB = "BNB"
    BTC = "BTC"
    LTC = "LTC"
    ETH = "ETH"
    SOL = "SOL"
    USDT_SOL = "USDT_SOL"
    USDC_SOL = "USDT_SOL"
    USDT_ERC20 = "USDT_ERC20"
    USDC_ERC20 = "USDC_ERC20"
    USDT_BEP20 = "USDT_BEP20"
    USDC_BEP20 = "USDC_BEP20"

    def get_decimals(self):
        match self:
            case Cryptocurrency.BTC | Cryptocurrency.LTC:
                return 8
            case Cryptocurrency.ETH | Cryptocurrency.BNB | Cryptocurrency.USDT_BEP20 | Cryptocurrency.USDC_BEP20:
                return 18
            case Cryptocurrency.SOL:
                return 9
            case _:
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
            case Cryptocurrency.USDT_SOL | Cryptocurrency.USDT_ERC20 | Cryptocurrency.USDT_BEP20:
                return "tether"
            case Cryptocurrency.USDC_SOL | Cryptocurrency.USDC_ERC20 | Cryptocurrency.USDC_BEP20:
                return "usd-coin"

    def get_explorer_base_url(self) -> str:
        match self:
            case Cryptocurrency.BTC:
                return "https://mempool.space"
            case Cryptocurrency.LTC:
                return "https://litecoinspace.org"
            case Cryptocurrency.ETH | Cryptocurrency.USDT_ERC20 | Cryptocurrency.USDC_ERC20:
                return "https://etherscan.io"
            case Cryptocurrency.BNB | Cryptocurrency.USDT_BEP20 | Cryptocurrency.USDC_BEP20:
                return "https://bscscan.com"
            case Cryptocurrency.SOL | Cryptocurrency.USDT_SOL | Cryptocurrency.USDC_SOL:
                return "https://solscan.io"

    def __str__(self):
        return self.name

    def get_localized(self, language: Language):
        return get_text(language, BotEntity.COMMON, f"{self.name.lower()}_top_up")

    def get_forwarding_address(self):
        match self:
            case Cryptocurrency.BTC:
                return config.BTC_FORWARDING_ADDRESS
            case Cryptocurrency.LTC:
                return config.LTC_FORWARDING_ADDRESS
            case Cryptocurrency.ETH | Cryptocurrency.USDT_ERC20 | Cryptocurrency.USDC_ERC20:
                return config.ETH_FORWARDING_ADDRESS
            case Cryptocurrency.BNB | Cryptocurrency.USDT_BEP20 | Cryptocurrency.USDC_BEP20:
                return config.BNB_FORWARDING_ADDRESS
            case Cryptocurrency.SOL | Cryptocurrency.USDT_SOL | Cryptocurrency.USDC_SOL:
                return config.SOL_FORWARDING_ADDRESS
