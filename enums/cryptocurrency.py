from enum import Enum

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class Cryptocurrency(Enum):
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

    def get_explorer_base_url(self) -> str:
        match self:
            case Cryptocurrency.BTC:
                return "https://mempool.space"
            case Cryptocurrency.LTC:
                return "https://litecoinspace.org"
            case Cryptocurrency.ETH:
                return "https://etherscan.io"
            case Cryptocurrency.BNB:
                return "https://bscscan.com"
            case Cryptocurrency.SOL:
                return "https://solscan.io"

    def __str__(self):
        return self.name

    def get_localized(self):
        return Localizator.get_text(BotEntity.COMMON, f"{self.name.lower()}_top_up")
