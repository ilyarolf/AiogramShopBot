
import aiohttp
import grequests

import config


class CryptoApiManager:
    def __init__(self, btc_address, ltc_address, trx_address, eth_address):
        self.btc_address = btc_address.strip()
        self.ltc_address = ltc_address.strip()
        self.trx_address = trx_address.strip()
        self.eth_address = eth_address.strip()

    @staticmethod
    async def fetch_api_request(url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return 0.0

    async def get_btc_balance(self) -> float:
        url = f'https://blockchain.info/rawaddr/{self.btc_address}'
        data = await self.fetch_api_request(url)
        return float(data['total_received']) / 100_000_000

    async def get_ltc_balance(self) -> float:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{self.ltc_address}"
        data = await self.fetch_api_request(url)
        return float(data['total_received']) / 100_000_000

    async def get_trx_and_trc_20_balance(self) -> dict:
        url = f'https://apilist.tronscan.org/api/account?address={self.trx_address}&includeToken=true'
        data = await self.fetch_api_request(url)
        trx_account_data = {'trx_balance': float(data["balance"]) / 1_000_000,
                            'in_transactions': data["transactions_in"]}
        for token in data['trc20token_balances']:
            if token['tokenId'] == 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t':
                trx_account_data['usdt_balance'] = round(float(token['balance']) * pow(10, -token['tokenDecimal']), 6)
            elif token['tokenId'] == 'TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn':
                trx_account_data['usdd_balance'] = round(float(token['balance']) * pow(10, -token['tokenDecimal']), 6)
        return trx_account_data

    async def get_eth_and_erc_20_balance(self) -> dict:
        url = f'https://api.ethplorer.io/getAddressInfo/{self.eth_address}?apiKey={config.ETHPLORER_API_KEY}'
        data = await self.fetch_api_request(url)
        eth_account_data = {"eth_balance": data["ETH"]["balance"],
                            }

    async def get_top_ups(self):
        urls = {
            "btc_balance": f'https://blockchain.info/rawaddr/{self.btc_address}',
            "usdt_balance": f'https://apilist.tronscan.org/api/account?address={self.trx_address}&includeToken=true',
            "ltc_balance": f'https://api.blockcypher.com/v1/ltc/main/addrs/{self.ltc_address}',
            # "eth_balance": ""
        }
        balances = {}
        rs = (grequests.get(url) for url in urls.values())
        data_list = grequests.map(rs)

        for symbol, data in zip(urls.keys(), data_list):
            response_code = data.status_code
            if response_code != 200:
                balances[symbol] = 0
            else:
                data = data.json()
                if 'total_received' in data:
                    balance = float(data['total_received']) / 100000000
                    balances[symbol] = balance
                else:
                    usdt_balance = None
                    for token in data['trc20token_balances']:
                        if token['tokenName'] == 'Tether USD':
                            usdt_balance = round(float(token['balance']) * pow(10, -token['tokenDecimal']), 6)
                            break
                    if usdt_balance is not None:
                        balances[symbol] = usdt_balance
                    else:
                        balances[symbol] = 0.0

        return balances

    @staticmethod
    async def get_crypto_prices() -> dict[str, float]:
        # TODO("NEED API FOR USDD-TRC-20")
        usd_crypto_prices = {}
        urls = {
            "btc": 'https://api.kraken.com/0/public/Ticker?pair=BTCUSDT',
            "usdt": 'https://api.kraken.com/0/public/Ticker?pair=USDTUSD',
            "usdc": "https://api.kraken.com/0/public/Ticker?pair=USDCUSD",
            "ltc": 'https://api.kraken.com/0/public/Ticker?pair=LTCUSD',
            "eth": 'https://api.kraken.com/0/public/Ticker?pair=ETHUSD',
            "trx": "https://api.kraken.com/0/public/Ticker?pair=TRXUSD"
        }
        responses = (grequests.get(url) for url in urls.values())
        datas = grequests.map(responses)
        for symbol, data in zip(urls.keys(), datas):
            data = data.json()
            price = float(next(iter(data['result'].values()))['l'][1])
            usd_crypto_prices[symbol] = price
        usd_crypto_prices["usdd"] = 1  # 1USDD=1USD
        return usd_crypto_prices
