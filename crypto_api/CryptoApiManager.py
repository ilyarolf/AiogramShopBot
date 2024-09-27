from datetime import datetime, timedelta

import aiohttp
import grequests

import config
from services.deposit import DepositService


class CryptoApiManager:
    def __init__(self, btc_address, ltc_address, trx_address, eth_address, user_id):
        self.btc_address = btc_address.strip()
        self.ltc_address = ltc_address.strip()
        self.trx_address = trx_address.strip()
        self.eth_address = eth_address.strip()
        self.user_id = user_id

    @staticmethod
    async def fetch_api_request(url: str) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data

    async def get_btc_balance(self, deposits) -> float:
        url = f'https://mempool.space/api/address/{self.btc_address}/utxo'
        data = await self.fetch_api_request(url)
        deposits = [deposit.tx_id for deposit in deposits if deposit.network == "BTC"]
        deposit_sum = 0.0
        for deposit in data:
            if deposit["txid"] not in deposits and deposit['status']['confirmed']:
                await DepositService.create(deposit['txid'], self.user_id, "BTC", None, deposit["value"])
                deposit_sum += float(deposit["value"]) / 100_000_000
        return deposit_sum

    async def get_ltc_balance(self, deposits) -> float:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{self.ltc_address}?unspendOnly=true"
        data = await self.fetch_api_request(url)
        deposits = [deposit.tx_id for deposit in deposits if deposit.network == "LTC"]
        deposits_sum = 0.0
        if data['n_tx'] > 0:
            for deposit in data['txrefs']:
                if deposit["confirmations"] > 0 and deposit['tx_hash'] not in deposits:
                    await DepositService.create(deposit['tx_hash'], self.user_id, "LTC", None, deposit["value"])
                    deposits_sum += float(deposit['value']) / 100_000_000
        return deposits_sum

    async def get_usdt_trc20_balance(self, deposits) -> float:
        now = datetime.now()
        earlier_time = now - timedelta(hours=6)
        min_timestamp = int(earlier_time.timestamp() * 1000)
        url = f"https://api.trongrid.io/v1/accounts/{self.trx_address}/transactions/trc20?only_confirmed=true&min_timestamp={min_timestamp}&contract_address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t&only_to=true"
        data = await self.fetch_api_request(url)
        deposits = [deposits.tx_id for deposit in deposits if
                    deposit.network == "TRX" and deposit.token_name == "USDT_TRC20"]
        deposits_sum = 0.0
        for deposit in data['data']:
            if deposit['transaction_id'] not in deposits:
                await DepositService.create(deposit['transaction_id'], self.user_id, "TRX",
                                            "USDT_TRC20", deposit['value'])
                deposits_sum += float(deposit['value']) / pow(10, deposit['token_info']['decimals'])
        return deposits_sum

    async def get_usdd_trc20_balance(self, deposits) -> float:
        now = datetime.now()
        earlier_time = now - timedelta(hours=6)
        min_timestamp = int(earlier_time.timestamp() * 1000)
        url = f"https://api.trongrid.io/v1/accounts/{self.trx_address}/transactions/trc20?only_confirmed=true&min_timestamp={min_timestamp}&contract_address=TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn&only_to=true"
        data = await self.fetch_api_request(url)
        deposits = [deposits.tx_id for deposit in deposits if
                    deposit.network == "TRX" and deposit.token_name == "USDT_TRC20"]
        deposits_sum = 0.0
        for deposit in data['data']:
            if deposit['transaction_id'] not in deposits:
                await DepositService.create(deposit['transaction_id'], self.user_id, "TRX",
                                            "USDD_TRC20", deposit['value'])
                deposits_sum += float(deposit['value']) / pow(10, deposit['token_info']['decimals'])
        return deposits_sum

    async def get_trx_balance(self, deposits) -> float:
        url = f'https://apilist.tronscanapi.com/api/new/transfer?sort=-timestamp&count=true&limit=100&start=0&address={self.trx_address}'
        data = await self.fetch_api_request(url)
        deposits = [deposits.tx_id for deposit in deposits if deposit.network == "TRX" and deposit.token_name is None]
        deposit_sum = 0.0
        for deposit in data['data']:
            if deposit['confirmed'] and deposit['transactionHash'] not in deposits and deposit[
                'transferToAddress'] == self.trx_address:
                await DepositService.create(deposit['transactionHash'], self.user_id, "TRX", None, deposit['amount'])
                deposit_sum += float(deposit['amount'] / pow(10, deposit['tokenInfo']['tokenDecimal']))
        return deposit_sum

    async def get_eth_and_erc_20_balance(self) -> dict:
        url = f'https://api.ethplorer.io/getAddressInfo/{self.eth_address}?apiKey={config.ETHPLORER_API_KEY}'
        data = await self.fetch_api_request(url)
        eth_account_data = {"eth_balance": data["ETH"]["balance"],
                            }

    async def get_top_ups(self):
        user_deposits = await DepositService.get_by_user_id(self.user_id)
        balances = {"btc_deposit": await self.get_btc_balance(user_deposits),
                    "ltc_deposit": await self.get_ltc_balance(user_deposits),
                    "usdt_trc20_deposit": await self.get_usdt_trc20_balance(user_deposits),
                    "usdd_trc20_deposit": await self.get_usdd_trc20_balance(user_deposits),
                    "trx_deposit": await self.get_trx_balance(user_deposits)}
        print(balances)
        # urls = {
        #     "btc_balance": f'https://blockchain.info/rawaddr/{self.btc_address}',
        #     "usdt_balance": f'https://apilist.tronscan.org/api/account?address={self.trx_address}&includeToken=true',
        #     "ltc_balance": f'https://api.blockcypher.com/v1/ltc/main/addrs/{self.ltc_address}',
        #     # "eth_balance": ""
        # }
        # balances = {}
        # rs = (grequests.get(url) for url in urls.values())
        # data_list = grequests.map(rs)
        #
        # for symbol, data in zip(urls.keys(), data_list):
        #     response_code = data.status_code
        #     if response_code != 200:
        #         balances[symbol] = 0
        #     else:
        #         data = data.json()
        #         if 'total_received' in data:
        #             balance = float(data['total_received']) / 100000000
        #             balances[symbol] = balance
        #         else:
        #             usdt_balance = None
        #             for token in data['trc20token_balances']:
        #                 if token['tokenName'] == 'Tether USD':
        #                     usdt_balance = round(float(token['balance']) * pow(10, -token['tokenDecimal']), 6)
        #                     break
        #             if usdt_balance is not None:
        #                 balances[symbol] = usdt_balance
        #             else:
        #                 balances[symbol] = 0.0
        #
        # return balances

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
