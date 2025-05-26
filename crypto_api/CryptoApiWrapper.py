import aiohttp
import config
from enums.cryptocurrency import Cryptocurrency
from enums.withdraw_type import WithdrawType
from models.withdrawal import WithdrawalDTO


class CryptoApiWrapper:
    LTC_API_BASENAME_TX = "https://litecoinspace.org/tx/"
    BTC_API_BASENAME_TX = "https://mempool.space/tx/"
    SOL_API_BASENAME_TX = "https://solscan.io/tx/"
    ETH_API_BASENAME_TX = "https://etherscan.io/tx/"

    @staticmethod
    async def fetch_api_request(url: str, params: dict | None = None, method: str = "GET", data: str | None = None,
                                headers: dict | None = None) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, params=params, data=data, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data

    @staticmethod
    async def get_crypto_prices(cryptocurrency: Cryptocurrency) -> float:
        url = f"https://api.kraken.com/0/public/Ticker?pair={cryptocurrency.value}{config.CURRENCY.value}"
        response_json = await CryptoApiWrapper.fetch_api_request(url)
        return float(next(iter(response_json['result'].values()))['c'][0])

    @staticmethod
    async def get_wallet_balance() -> dict:
        url = f"{config.KRYPTO_EXPRESS_API_URL}/wallet"
        headers = {
            "X-Api-Key": config.KRYPTO_EXPRESS_API_KEY
        }
        response = await CryptoApiWrapper.fetch_api_request(
            url,
            headers=headers
        )
        return {k: v for k, v in response.items() if v > 0}

    @staticmethod
    async def withdrawal(cryptocurrency: Cryptocurrency, to_address: str, only_calculate: bool) -> WithdrawalDTO:
        url = f"{config.KRYPTO_EXPRESS_API_URL}/wallet/withdrawal"
        headers = {
            "X-Api-Key": config.KRYPTO_EXPRESS_API_KEY,
            "Content-Type": "application/json"
        }
        body = WithdrawalDTO(
            withdrawType=WithdrawType.ALL,
            cryptoCurrency=cryptocurrency.name,
            toAddress=to_address,
            onlyCalculate=only_calculate
        )
        response = await CryptoApiWrapper.fetch_api_request(
            url,
            method="POST",
            data=body.model_dump_json(),
            headers=headers
        )
        return WithdrawalDTO.model_validate(response)
