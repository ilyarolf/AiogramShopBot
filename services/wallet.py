import re

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
from callbacks import WalletCallback
from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from handlers.admin.constants import AdminConstants, WalletStates
from models.withdrawal import WithdrawalDTO
from utils.utils import get_text


class WalletService:
    @staticmethod
    async def get_wallet_menu(language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "withdraw_funds"),
                          callback_data=WalletCallback.create(1))
        kb_builder.row(AdminConstants.back_to_main_button(language))
        return get_text(language, BotEntity.ADMIN, "crypto_withdraw"), kb_builder

    @staticmethod
    async def get_withdraw_menu(language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        wallet_balance = await CryptoApiWrapper.get_wallet_balance()
        [kb_builder.button(
            text=get_text(language, BotEntity.COMMON, f"{key.lower()}_top_up"),
            callback_data=WalletCallback.create(1, Cryptocurrency(key))
        ) for key in wallet_balance.keys()]
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button(language))
        msg_text = get_text(language, BotEntity.ADMIN, "crypto_wallet").format(
            btc_balance=wallet_balance.get('BTC') or 0.0,
            ltc_balance=wallet_balance.get('LTC') or 0.0,
            sol_balance=wallet_balance.get('SOL') or 0.0,
            eth_balance=wallet_balance.get('ETH') or 0.0,
            bnb_balance=wallet_balance.get('BNB') or 0.0
        )
        if sum(wallet_balance.values()) > 0:
            msg_text += get_text(language, BotEntity.ADMIN, "choose_crypto_to_withdraw")
        return msg_text, kb_builder

    @staticmethod
    async def request_crypto_address(callback_data: WalletCallback,
                                     state: FSMContext,
                                     language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(AdminConstants.back_to_main_button(language))
        await state.update_data(cryptocurrency=callback_data.cryptocurrency)
        await state.set_state(WalletStates.crypto_address)
        return get_text(language, BotEntity.ADMIN, "send_addr_request").format(
            crypto_name=callback_data.cryptocurrency.value), kb_builder

    @staticmethod
    async def calculate_withdrawal(message: Message,
                                   state: FSMContext,
                                   language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        if message.text and message.text.lower() == "cancel":
            await state.clear()
            return get_text(language, BotEntity.COMMON, "cancelled"), kb_builder
        to_address = message.text
        state_data = await state.get_data()
        await state.update_data(to_address=to_address)
        cryptocurrency = Cryptocurrency(state_data['cryptocurrency'])
        prices = await CryptoApiWrapper.get_crypto_prices()
        price = prices[cryptocurrency.get_coingecko_name()][config.CURRENCY.value.lower()]

        withdraw_dto = await CryptoApiWrapper.withdrawal(
            cryptocurrency,
            to_address,
            True
        )
        withdraw_dto = WithdrawalDTO.model_validate(withdraw_dto, from_attributes=True)
        if withdraw_dto.receivingAmount > 0:
            kb_builder.button(text=get_text(language, BotEntity.COMMON, "confirm"),
                              callback_data=WalletCallback.create(2, cryptocurrency))
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                          callback_data=WalletCallback.create(0))
        return get_text(language, BotEntity.ADMIN, "crypto_withdrawal_info").format(
            address=withdraw_dto.toAddress,
            crypto_name=cryptocurrency.value,
            withdrawal_amount=withdraw_dto.totalWithdrawalAmount,
            withdrawal_amount_fiat=withdraw_dto.totalWithdrawalAmount * price,
            currency_text=config.CURRENCY.get_localized_text(),
            blockchain_fee_amount=withdraw_dto.blockchainFeeAmount,
            blockchain_fee_fiat=withdraw_dto.blockchainFeeAmount * price,
            service_fee_amount=withdraw_dto.serviceFeeAmount,
            service_fee_fiat=withdraw_dto.serviceFeeAmount * price,
            receiving_amount=withdraw_dto.receivingAmount,
            receiving_amount_fiat=withdraw_dto.receivingAmount * price,
        ), kb_builder

    @staticmethod
    async def withdraw_transaction(callback_data: WalletCallback,
                                   state: FSMContext,
                                   language: Language) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        kb_builder = InlineKeyboardBuilder()
        withdraw_dto = await CryptoApiWrapper.withdrawal(
            callback_data.cryptocurrency,
            state_data['to_address'],
            False
        )
        withdraw_dto = WithdrawalDTO.model_validate(withdraw_dto, from_attributes=True)
        [kb_builder.button(
            text=get_text(language, BotEntity.ADMIN, "transaction"),
            url=f"{callback_data.cryptocurrency.get_explorer_base_url()}/tx/{tx_id}") for tx_id in
            withdraw_dto.txIdList]
        kb_builder.adjust(1)
        await state.clear()
        return get_text(language, BotEntity.ADMIN, "transaction_broadcasted"), kb_builder

    @staticmethod
    def validate_withdrawal_address(address: str, cryptocurrency: Cryptocurrency) -> bool:
        address_regex = {
            Cryptocurrency.BTC: re.compile(r'^bc1[a-zA-HJ-NP-Z0-9]{25,39}$'),
            Cryptocurrency.LTC: re.compile(r'^ltc1[a-zA-HJ-NP-Z0-9]{26,}$'),
            Cryptocurrency.ETH: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.BNB: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.SOL: re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'),
            Cryptocurrency.USDT_SOL: re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'),
            Cryptocurrency.USDC_SOL: re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'),
            Cryptocurrency.USDT_ERC20: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.USDC_ERC20: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.USDT_BEP20: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.USDC_BEP20: re.compile(r'^0x[a-fA-F0-9]{40}$'),
        }
        regex = address_regex[cryptocurrency]
        return bool(regex.match(address))
