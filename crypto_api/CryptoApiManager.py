from datetime import datetime, timedelta
import aiohttp
import config
from enums.cryptocurrency import Cryptocurrency
from models.deposit import DepositDTO
from models.user import UserDTO
from services.deposit import DepositService


class CryptoApiManager:
    min_timestamp = int((datetime.now() - timedelta(hours=24)).timestamp()) * 1000

    @staticmethod
    async def fetch_api_request(url: str, params: dict | None = None) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data

    @staticmethod
    async def get_new_btc_deposits(user_dto: UserDTO, deposits) -> float:
        url = f'https://mempool.space/api/address/{user_dto.btc_address}/utxo'
        data = await CryptoApiManager.fetch_api_request(url)
        deposits = [deposit.tx_id for deposit in deposits if deposit.network == "BTC"]
        deposit_sum = 0.0
        for deposit in data:
            if deposit["txid"] not in deposits and deposit['status']['confirmed']:
                deposit_dto = DepositDTO(
                    tx_id=deposit['txid'],
                    user_id=user_dto.id,
                    network="BTC",
                    amount=deposit['value'],
                    vout=deposit['vout']
                )
                await DepositService.create(deposit_dto)
                deposit_sum += float(deposit["value"]) / 100_000_000
        return deposit_sum

    @staticmethod
    async def get_new_ltc_deposits(user_dto: UserDTO, deposits) -> float:
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{user_dto.ltc_address}"
        params = {"unspentOnly": "true"}
        data = await CryptoApiManager.fetch_api_request(url, params=params)
        deposits = [deposit.tx_id for deposit in deposits if deposit.network == "LTC"]
        deposits_sum = 0.0
        if data['n_tx'] > 0:
            for deposit in data['txrefs']:
                if deposit["confirmations"] > 0 and deposit['tx_hash'] not in deposits:
                    deposit_dto = DepositDTO(
                        tx_id=deposit['tx_hash'],
                        user_id=user_dto.id,
                        network='LTC',
                        amount=deposit['value'],
                        vout=deposit['tx_output_n']
                    )
                    await DepositService.create(deposit_dto)
                    deposits_sum += float(deposit['value']) / 100_000_000
        return deposits_sum

    @staticmethod
    async def get_sol_balance(user_dto: UserDTO, deposits) -> float:
        url = f"https://api.solana.fm/v0/accounts/{user_dto.sol_address}/transfers"
        data = await CryptoApiManager.fetch_api_request(url)
        deposits = [deposit.tx_id for deposit in deposits if deposit.network == "SOL"]
        deposits_sum = 0.0
        if len(data['results']) > 0:
            for deposit in data['results']:
                if deposit['transactionHash'] not in deposits:
                    for transfer in deposit['data']:
                        if transfer['action'] == 'transfer' and transfer['destination'] == user_dto.sol_address and \
                                transfer[
                                    'status'] == 'Successful' and transfer['token'] == '':
                            deposit_dto = DepositDTO(
                                tx_id=deposit['transactionHash'],
                                user_id=user_dto.id,
                                network='SOL',
                                amount=transfer['amount'],
                                vout=transfer['instructionIndex']
                            )
                            await DepositService.create(deposit_dto)
                            deposits_sum += float(transfer['amount'] / 1_000_000_000)
        return deposits_sum

    @staticmethod
    async def get_usdt_trc20_balance(user_dto: UserDTO, deposits) -> float:
        url = f"https://api.trongrid.io/v1/accounts/{user_dto.trx_address}/transactions/trc20"
        params = {"only_confirmed": "true",
                  "min_timestamp": CryptoApiManager.min_timestamp,
                  "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                  "only_to": "true"}
        data = await CryptoApiManager.fetch_api_request(url, params=params)
        deposits = [deposit.tx_id for deposit in deposits if
                    deposit.network == "TRX" and deposit.token_name == "USDT_TRC20"]
        deposits_sum = 0.0
        for deposit in data['data']:
            if deposit['transaction_id'] not in deposits:
                deposit_dto = DepositDTO(
                    tx_id=deposit['transaction_id'],
                    user_id=user_dto.id,
                    network='TRX',
                    token_name='USDT_TRC20',
                    amount=deposit['value'],
                )
                await DepositService.create(deposit_dto)
                deposits_sum += float(deposit['value']) / pow(10, deposit['token_info']['decimals'])
        return deposits_sum

    @staticmethod
    async def get_usdt_erc20_balance(user_dto: UserDTO, deposits) -> float:
        # TODO(Combine the function to obtain erc20 tokens.)
        url = f'https://api.ethplorer.io/getAddressHistory/{user_dto.eth_address}'
        params = {
            "type": "transfer",
            "token": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "apiKey": config.ETHPLORER_API_KEY,
            "limit": 1000
        }
        data = await CryptoApiManager.fetch_api_request(url, params)
        deposits = [deposit.tx_id for deposit in deposits if
                    deposit.network == "ETH" and deposit.token_name == "USDT_ERC20"]
        deposits_sum = 0.0
        for deposit in data['operations']:
            if deposit['transactionHash'] not in deposits and deposit['to'] == user_dto.eth_address.lower():
                deposit_dto = DepositDTO(
                    tx_id=deposit['transactionHash'],
                    user_id=user_dto.id,
                    network='ETH',
                    token_name='USDT_ERC20',
                    amount=deposit['value']
                )
                await DepositService.create(deposit_dto)
                deposits_sum += float(deposit['value']) / pow(10, 6)
        return deposits_sum

    @staticmethod
    async def get_usdc_erc20_balance(user_dto: UserDTO, deposits):
        # TODO(Combine the function to obtain erc20 tokens.)
        url = f'https://api.ethplorer.io/getAddressHistory/{user_dto.eth_address}'
        params = {
            "type": "transfer",
            "token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "apiKey": config.ETHPLORER_API_KEY,
            "limit": 1000
        }
        data = await CryptoApiManager.fetch_api_request(url, params)
        deposits = [deposit.tx_id for deposit in deposits if
                    deposit.network == "ETH" and deposit.token_name == "USDC_ERC20"]
        deposits_sum = 0.0
        for deposit in data['operations']:
            if deposit['transactionHash'] not in deposits and deposit['to'] == user_dto.eth_address.lower():
                deposit_dto = DepositDTO(
                    tx_id=deposit['transactionHash'],
                    user_id=user_dto.id,
                    network='ETH',
                    token_name='USDC_ERC20',
                    amount=deposit['value']
                )
                await DepositService.create(deposit_dto)
                deposits_sum += float(deposit['value']) / pow(10, 6)
        return deposits_sum

    @staticmethod
    async def get_crypto_prices(cryptocurrency: Cryptocurrency) -> float:
        match cryptocurrency:
            case cryptocurrency.USDT_TRC20 | cryptocurrency.USDT_ERC20:
                url = f'https://api.kraken.com/0/public/Ticker?pair=USDT{config.CURRENCY.value}'
                response_json = await CryptoApiManager.fetch_api_request(url)
            case cryptocurrency.USDC_ERC20:
                url = f"https://api.kraken.com/0/public/Ticker?pair=USDC{config.CURRENCY.value}"
                response_json = await CryptoApiManager.fetch_api_request(url)
            case _:
                url = f"https://api.kraken.com/0/public/Ticker?pair={cryptocurrency.value}{config.CURRENCY.value}"
                response_json = await CryptoApiManager.fetch_api_request(url)
        return float(next(iter(response_json['result'].values()))['c'][0])

    @staticmethod
    async def get_new_deposits_amount(user_dto: UserDTO, cryptocurrency: Cryptocurrency):
        deposits = await DepositService.get_by_user_dto(user_dto)
        match cryptocurrency:
            case Cryptocurrency.BTC:
                return await CryptoApiManager.get_new_btc_deposits(user_dto, deposits)
            case Cryptocurrency.LTC:
                return await CryptoApiManager.get_new_ltc_deposits(user_dto, deposits)
            case Cryptocurrency.SOL:
                return await CryptoApiManager.get_sol_balance(user_dto, deposits)
            case Cryptocurrency.USDT_TRC20:
                return await CryptoApiManager.get_usdt_trc20_balance(user_dto, deposits)
            case Cryptocurrency.USDT_ERC20:
                return await CryptoApiManager.get_usdt_erc20_balance(user_dto, deposits)
            case Cryptocurrency.USDC_ERC20:
                return await CryptoApiManager.get_usdc_erc20_balance(user_dto, deposits)
