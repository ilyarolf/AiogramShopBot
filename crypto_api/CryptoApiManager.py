from typing import Any

import grequests


class CryptoApiManager:
    def __init__(self, btc_address, ltc_address, trx_address):
        self.btc_address = btc_address.strip()
        self.ltc_address = ltc_address.strip()
        self.trx_address = trx_address.strip()

    async def get_top_ups(self):
        urls = {
            "btc_balance": f'https://blockchain.info/rawaddr/{self.btc_address}',
            "usdt_balance": f'https://apilist.tronscan.org/api/account?address={self.trx_address}&includeToken=true',
            "ltc_balance": f'https://api.blockcypher.com/v1/ltc/main/addrs/{self.ltc_address}'
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
    async def get_crypto_prices() -> dict[Any, float]:
        usd_crypto_prices = {}
        urls = {"btc": f'https://api.coinbase.com/v2/prices/BTC-USD/buy',
                "usdt": 'https://api.coinbase.com/v2/prices/USDT-USD/buy',
                "ltc": 'https://api.coinbase.com/v2/prices/LTC-USD/buy'}
        responses = (grequests.get(url) for url in urls.values())
        datas = grequests.map(responses)
        for symbol, data in zip(urls.keys(), datas):
            data = data.json()
            price = float(data['data']['amount'])
            usd_crypto_prices[symbol] = price
        return usd_crypto_prices

