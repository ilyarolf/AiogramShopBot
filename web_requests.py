import grequests
from requests import get
from db_requests import RequestToDB
RequestToDB = RequestToDB('items.db')


class WebRequest:
    """Класс для работы с запросами"""
    async def parse_balances(self, telegram_id: str) -> list:
        """
        Функция:
        1)Отправляет запросы к API
        2)Извлекает баланс и Json файла
        3)Обновляет баланс в коинах в БД
        """
        wallets = RequestToDB.get_user_wallets(telegram_id)
        urls = [f'https://blockchain.info/rawaddr/{wallets[0]}',
                f'https://apilist.tronscan.org/api/account?address={wallets[1]}&includeToken=true',
                f'https://api.blockcypher.com/v1/ltc/main/addrs/{wallets[2]}']
        balances = []
        rs = (grequests.get(url) for url in urls)
        data_list = grequests.map(rs)
        for data in data_list:
            response_code = data.status_code
            if response_code != 200:
                balances.append(0)
            else:
                data = data.json()
                if 'total_received' in data:
                    balance = float(data['total_received']) / 100000000
                    balances.append(balance)
                else:
                    usdt_balance = None
                    for token in data['trc20token_balances']:
                        if token['tokenName'] == 'Tether USD':
                            usdt_balance = round(float(token['balance']) * pow(10, -token['tokenDecimal']), 6)
                            break
                    if usdt_balance is not None:
                        balances.append(usdt_balance)
                    else:
                        balances.append(0.0)
        RequestToDB.update_balances(balances, telegram_id)
        return balances

    async def refresh_balance_in_usd(self, balances: list, telegram_id: int) -> None:
        """
        Функция:
        1)Получает текущую цену крипты в долларах,
        2)Перемножает балансы на цену
        3)Обновляет баланс в USD в БД
        """
        usd_balance_list = []
        urls = [f'https://api.coinbase.com/v2/prices/BTC-USD/buy',
                'https://api.coinbase.com/v2/prices/USDT-USD/buy',
                'https://api.coinbase.com/v2/prices/LTC-USD/buy']
        responses = (grequests.get(url) for url in urls)
        datas = grequests.map(responses)
        for i in range(len(datas)):
            data = datas[i].json()
            price = float(data['data']['amount'])
            if i != 1:
                usd_balance_list.append(balances[i] * price * 0.9)
            else:
                usd_balance_list.append(balances[i] * price)
        RequestToDB.update_balance_usd(usd_balance_list, telegram_id)

    async def get_admin_file(self, url, filename):
        """
        Подфункция принимает url и filename и создаёт файл, который отправил админ в бота для добавления нового товара
        """
        r = get(url)
        with open(filename, 'wb') as file:
            file.write(r.content)
