from enum import Enum


class Cryptocurrency(Enum):
    BTC = "BTC"
    LTC = "LTC"
    SOL = "SOL"
    USDT_TRC20 = "USDT_TRC20"
    USDT_ERC20 = "USDT_ERC20"
    USDC_ERC20 = "USDC_ERC20"

    def get_balance_field(self) -> str:
        match self:
            case Cryptocurrency.BTC:
                return "btc_balance"
            case Cryptocurrency.LTC:
                return "ltc_balance"
            case Cryptocurrency.SOL:
                return "sol_balance"
            case Cryptocurrency.USDT_TRC20:
                return "usdt_trc20_balance"
            case Cryptocurrency.USDT_ERC20:
                return "usdt_erc20_balance"
            case Cryptocurrency.USDC_ERC20:
                return "usdc_erc20_balance"

    def get_address_field(self) -> str:
        match self:
            case Cryptocurrency.BTC:
                return "btc_address"
            case Cryptocurrency.LTC:
                return "ltc_address"
            case Cryptocurrency.SOL:
                return "sol_address"
            case Cryptocurrency.USDT_TRC20:
                return "trx_address"
            case _:
                return "eth_address"
