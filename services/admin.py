import asyncio
import logging
import re

from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import AnnouncementCallback, AnnouncementType, InventoryManagementCallback, EntityType, \
    AddType, UserManagementCallback, UserManagementOperation, StatisticsCallback, StatisticsEntity, StatisticsTimeDelta, \
    WalletCallback, MediaManagementCallback
from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.sort_property import SortProperty
from handlers.admin.constants import AdminConstants, AdminInventoryManagementStates, UserManagementStates, WalletStates
from handlers.common.common import add_pagination_buttons, add_sorting_buttons
from models.withdrawal import WithdrawalDTO
from repositories.buy import BuyRepository
from repositories.category import CategoryRepository
from repositories.deposit import DepositRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.notification import NotificationService
from utils.localizator import Localizator


class AdminService:

    @staticmethod
    async def get_entity_picker(callback_data: InventoryManagementCallback | MediaManagementCallback,
                                session: AsyncSession | Session):
        kb_builder = InlineKeyboardBuilder()
        match callback_data.entity_type:
            case EntityType.CATEGORY:
                entities = await CategoryRepository.get_to_delete(callback_data.page, session)
            case _:
                entities = await SubcategoryRepository.get_to_delete(callback_data.page, session)
        for entity in entities:
            if isinstance(callback_data, InventoryManagementCallback):
                kb_builder.button(text=entity.name, callback_data=InventoryManagementCallback.create(
                    level=3,
                    entity_type=callback_data.entity_type,
                    entity_id=entity.id,
                    page=callback_data.page
                ))
            else:
                kb_builder.button(text=entity.name, callback_data=MediaManagementCallback.create(
                    level=2,
                    entity_type=callback_data.entity_type,
                    entity_id=entity.id,
                    page=callback_data.page
                ))
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  SubcategoryRepository.get_maximum_page_to_delete(session),
                                                  callback_data.get_back_button(0))
        if isinstance(callback_data, InventoryManagementCallback):
            msg_text = Localizator.get_text(BotEntity.ADMIN, "delete_entity").format(
                entity=callback_data.entity_type.get_localized()
            )
        else:
            msg_text = Localizator.get_text(BotEntity.ADMIN, "edit_media").format(
                entity=callback_data.entity_type.get_localized()
            )
        return msg_text, kb_builder

    @staticmethod
    async def get_wallet_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "withdraw_funds"),
                          callback_data=WalletCallback.create(1))
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "crypto_withdraw"), kb_builder

    @staticmethod
    async def get_withdraw_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        wallet_balance = await CryptoApiWrapper.get_wallet_balance()
        [kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, f"{key.lower()}_top_up"),
            callback_data=WalletCallback.create(1, Cryptocurrency(key))
        ) for key in wallet_balance.keys()]
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        msg_text = Localizator.get_text(BotEntity.ADMIN, "crypto_wallet").format(
            btc_balance=wallet_balance.get('BTC') or 0.0,
            ltc_balance=wallet_balance.get('LTC') or 0.0,
            sol_balance=wallet_balance.get('SOL') or 0.0,
            eth_balance=wallet_balance.get('ETH') or 0.0,
            bnb_balance=wallet_balance.get('BNB') or 0.0
        )
        if sum(wallet_balance.values()) > 0:
            msg_text += Localizator.get_text(BotEntity.ADMIN, "choose_crypto_to_withdraw")
        return msg_text, kb_builder

    @staticmethod
    async def request_crypto_address(callback: CallbackQuery, state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = WalletCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(AdminConstants.back_to_main_button)
        await state.update_data(cryptocurrency=unpacked_cb.cryptocurrency)
        await state.set_state(WalletStates.crypto_address)
        return Localizator.get_text(BotEntity.ADMIN, "send_addr_request").format(
            crypto_name=unpacked_cb.cryptocurrency.value), kb_builder

    @staticmethod
    async def calculate_withdrawal(message: Message, state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        if message.text and message.text.lower() == "cancel":
            await state.clear()
            return Localizator.get_text(BotEntity.COMMON, "cancelled"), kb_builder
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
        withdraw_dto: WithdrawalDTO = WithdrawalDTO.model_validate(withdraw_dto, from_attributes=True)
        if withdraw_dto.receivingAmount > 0:
            kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                              callback_data=WalletCallback.create(2, cryptocurrency))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=WalletCallback.create(0))
        return Localizator.get_text(BotEntity.ADMIN, "crypto_withdrawal_info").format(
            address=withdraw_dto.toAddress,
            crypto_name=cryptocurrency.value,
            withdrawal_amount=withdraw_dto.totalWithdrawalAmount,
            withdrawal_amount_fiat=withdraw_dto.totalWithdrawalAmount * price,
            currency_text=Localizator.get_currency_text(),
            blockchain_fee_amount=withdraw_dto.blockchainFeeAmount,
            blockchain_fee_fiat=withdraw_dto.blockchainFeeAmount * price,
            service_fee_amount=withdraw_dto.serviceFeeAmount,
            service_fee_fiat=withdraw_dto.serviceFeeAmount * price,
            receiving_amount=withdraw_dto.receivingAmount,
            receiving_amount_fiat=withdraw_dto.receivingAmount * price,
        ), kb_builder

    @staticmethod
    async def withdraw_transaction(callback: CallbackQuery, state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = WalletCallback.unpack(callback.data)
        state_data = await state.get_data()
        kb_builder = InlineKeyboardBuilder()
        withdraw_dto = await CryptoApiWrapper.withdrawal(
            unpacked_cb.cryptocurrency,
            state_data['to_address'],
            False
        )
        withdraw_dto = WithdrawalDTO.model_validate(withdraw_dto, from_attributes=True)
        match unpacked_cb.cryptocurrency:
            case Cryptocurrency.LTC:
                [kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "transaction"),
                                   url=f"{CryptoApiWrapper.LTC_API_BASENAME_TX}{tx_id}") for tx_id in
                 withdraw_dto.txIdList]
            case Cryptocurrency.BTC:
                [kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "transaction"),
                                   url=f"{CryptoApiWrapper.BTC_API_BASENAME_TX}{tx_id}") for tx_id in
                 withdraw_dto.txIdList]
            case Cryptocurrency.SOL:
                [kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "transaction"),
                                   url=f"{CryptoApiWrapper.SOL_API_BASENAME_TX}{tx_id}") for tx_id in
                 withdraw_dto.txIdList]
            case Cryptocurrency.ETH:
                [kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "transaction"),
                                   url=f"{CryptoApiWrapper.ETH_API_BASENAME_TX}{tx_id}") for tx_id in
                 withdraw_dto.txIdList]
            case Cryptocurrency.BNB:
                [kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "transaction"),
                                   url=f"{CryptoApiWrapper.BNB_API_BASENAME_TX}{tx_id}") for tx_id in
                 withdraw_dto.txIdList]
        kb_builder.adjust(1)
        await state.clear()
        return Localizator.get_text(BotEntity.ADMIN, "transaction_broadcasted"), kb_builder

    @staticmethod
    async def validate_withdrawal_address(message: Message, state: FSMContext) -> bool:
        address_regex = {
            Cryptocurrency.BTC: re.compile(r'^bc1[a-zA-HJ-NP-Z0-9]{25,39}$'),
            Cryptocurrency.LTC: re.compile(r'^ltc1[a-zA-HJ-NP-Z0-9]{26,}$'),
            Cryptocurrency.ETH: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.BNB: re.compile(r'^0x[a-fA-F0-9]{40}$'),
            Cryptocurrency.SOL: re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'),
        }
        state_data = await state.get_data()
        cryptocurrency = Cryptocurrency(state_data['cryptocurrency'])
        regex = address_regex[cryptocurrency]
        return bool(regex.match(message.text))
