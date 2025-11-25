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
    async def send_announcement(callback: CallbackQuery, session: AsyncSession | Session):
        unpacked_cb = AnnouncementCallback.unpack(callback.data)
        await NotificationService.edit_reply_markup(callback.bot,
                                                    callback.message.chat.id,
                                                    callback.message.message_id)
        active_users = await UserRepository.get_active(session)
        all_users_count = await UserRepository.get_all_count(session)
        counter = 0
        for user in active_users:
            try:
                await callback.message.copy_to(user.telegram_id, reply_markup=None)
                counter += 1
                await asyncio.sleep(1.5)
            except TelegramForbiddenError as e:
                logging.error(f"TelegramForbiddenError: {e.message}")
                if "user is deactivated" in e.message.lower():
                    user.can_receive_messages = False
                elif "bot was blocked by the user" in e.message.lower():
                    user.can_receive_messages = False
                    await UserRepository.update(user, session)
            except Exception as e:
                logging.error(e)
            finally:
                if unpacked_cb.announcement_type == AnnouncementType.RESTOCKING:
                    await ItemRepository.set_not_new(session)
                await session_commit(session)
        return Localizator.get_text(BotEntity.ADMIN, "sending_result").format(counter=counter,
                                                                              len=len(active_users),
                                                                              users_count=all_users_count)

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
    async def get_user_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management"),
                          callback_data=UserManagementCallback.create(1))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "make_refund"),
                          callback_data=UserManagementCallback.create(2))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "user_management"), kb_builder

    @staticmethod
    async def get_credit_management_menu(callback_data: UserManagementCallback) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_add_balance"),
                          callback_data=UserManagementCallback.create(1, UserManagementOperation.ADD_BALANCE))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_reduce_balance"),
                          callback_data=UserManagementCallback.create(1, UserManagementOperation.REDUCE_BALANCE))
        kb_builder.row(callback_data.get_back_button())
        return Localizator.get_text(BotEntity.ADMIN, "credit_management"), kb_builder

    @staticmethod
    async def request_user_entity(callback_data: UserManagementCallback, state: FSMContext):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        await state.set_state(UserManagementStates.user_entity)
        await state.update_data(operation=callback_data.operation.value)
        return Localizator.get_text(BotEntity.ADMIN, "credit_management_request_user_entity"), kb_builder

    @staticmethod
    async def request_balance_amount(message: Message, state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        state_data = await state.get_data()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        await state.update_data(user_entity=message.text)
        await state.set_state(UserManagementStates.balance_amount)
        data = await state.get_data()
        operation = UserManagementOperation(int(data['operation']))
        match operation:
            case UserManagementOperation.ADD_BALANCE:
                return Localizator.get_text(BotEntity.ADMIN, "credit_management_plus_operation").format(
                    currency_text=Localizator.get_currency_text()), kb_builder
            case UserManagementOperation.REDUCE_BALANCE:
                return Localizator.get_text(BotEntity.ADMIN, "credit_management_minus_operation").format(
                    currency_text=Localizator.get_currency_text()), kb_builder

    @staticmethod
    async def balance_management(message: Message, state: FSMContext, session: AsyncSession | Session) -> str:
        state_data = await state.get_data()
        await state.clear()
        await NotificationService.edit_reply_markup(message.bot, state_data['chat_id'], state_data['msg_id'])
        user = await UserRepository.get_user_entity(state_data['user_entity'].replace("@", ""), session)
        operation = UserManagementOperation(int(state_data['operation']))
        if user is None:
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_user_not_found")
        elif operation == UserManagementOperation.ADD_BALANCE:
            user.top_up_amount += float(message.text)
            await UserRepository.update(user, session)
            await session_commit(session)
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_added_success").format(
                amount=message.text,
                telegram_id=user.telegram_id,
                currency_text=Localizator.get_currency_text())
        else:
            user.consume_records += float(message.text)
            await UserRepository.update(user, session)
            await session_commit(session)
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_reduced_success").format(
                amount=message.text,
                telegram_id=user.telegram_id,
                currency_text=Localizator.get_currency_text())

    @staticmethod
    async def get_refund_menu(callback_data: UserManagementCallback, state: FSMContext, session: AsyncSession) -> tuple[
        str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        state_data = await state.get_data()
        sort_pairs = state_data.get("sort_pairs") or {}
        sort_pairs[str(callback_data.sort_property.value)] = callback_data.sort_order.value
        await state.update_data(sort_pairs=sort_pairs)
        refund_data = await BuyRepository.get_refund_data(sort_pairs, callback_data.page, session)
        for refund_item in refund_data:
            callback = UserManagementCallback.create(
                callback_data.level + 1,
                UserManagementOperation.REFUND,
                buy_id=refund_item.buy_id)
            if refund_item.telegram_username:
                kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "refund_by_username").format(
                    telegram_username=refund_item.telegram_username,
                    total_price=refund_item.total_price,
                    subcategory=refund_item.subcategory_name,
                    currency_sym=Localizator.get_currency_symbol()),
                    callback_data=callback)
            else:
                kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "refund_by_tgid").format(
                    telegram_id=refund_item.telegram_id,
                    total_price=refund_item.total_price,
                    subcategory=refund_item.subcategory_name,
                    currency_sym=Localizator.get_currency_symbol()),
                    callback_data=callback)
        kb_builder.adjust(1)
        kb_builder = await add_sorting_buttons(kb_builder, [SortProperty.QUANTITY,
                                                            SortProperty.TOTAL_PRICE,
                                                            SortProperty.BUY_DATETIME],
                                               callback_data,
                                               sort_pairs)
        kb_builder = await add_pagination_buttons(kb_builder, callback_data,
                                                  BuyRepository.get_max_refund_page(session),
                                                  callback_data.get_back_button(0))
        return Localizator.get_text(BotEntity.ADMIN, "refund_menu"), kb_builder

    @staticmethod
    async def refund_confirmation(callback_data: UserManagementCallback, session: AsyncSession):
        callback_data.confirmation = True
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=callback_data)
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        refund_data = await BuyRepository.get_refund_data_single(callback_data.buy_id, session)
        if refund_data.telegram_username:
            return Localizator.get_text(BotEntity.ADMIN, "refund_confirmation_by_username").format(
                telegram_username=refund_data.telegram_username,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                total_price=refund_data.total_price,
                currency_sym=Localizator.get_currency_symbol()), kb_builder
        else:
            return Localizator.get_text(BotEntity.ADMIN, "refund_confirmation_by_tgid").format(
                telegram_id=refund_data.telegram_id,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                total_price=refund_data.total_price,
                currency_sym=Localizator.get_currency_symbol()), kb_builder

    @staticmethod
    async def get_statistics_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "users_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.USERS))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "buys_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.BUYS))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "deposits_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.DEPOSITS))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "get_database_file"),
                          callback_data=StatisticsCallback.create(3))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "pick_statistics_entity"), kb_builder

    @staticmethod
    async def get_timedelta_menu(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        unpacked_cb = StatisticsCallback.unpack(callback.data)
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "1_day"),
                          callback_data=StatisticsCallback.create(unpacked_cb.level + 1,
                                                                  unpacked_cb.statistics_entity,
                                                                  StatisticsTimeDelta.DAY))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "7_day"),
                          callback_data=StatisticsCallback.create(unpacked_cb.level + 1,
                                                                  unpacked_cb.statistics_entity,
                                                                  StatisticsTimeDelta.WEEK))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "30_day"),
                          callback_data=StatisticsCallback.create(unpacked_cb.level + 1,
                                                                  unpacked_cb.statistics_entity,
                                                                  StatisticsTimeDelta.MONTH))
        kb_builder.row(unpacked_cb.get_back_button(0))
        return Localizator.get_text(BotEntity.ADMIN, "statistics_timedelta"), kb_builder

    @staticmethod
    async def get_statistics(callback: CallbackQuery, session: AsyncSession | Session):
        unpacked_cb = StatisticsCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        match unpacked_cb.statistics_entity:
            case StatisticsEntity.USERS:
                users, users_count = await UserRepository.get_by_timedelta(unpacked_cb.timedelta, unpacked_cb.page,
                                                                           session)
                [kb_builder.button(text=user.telegram_username, url=f't.me/{user.telegram_username}') for user in
                 users
                 if user.telegram_username]
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(
                    kb_builder,
                    unpacked_cb,
                    UserRepository.get_max_page_by_timedelta(unpacked_cb.timedelta, session),
                    None)
                kb_builder.row(AdminConstants.back_to_main_button, unpacked_cb.get_back_button())
                return Localizator.get_text(BotEntity.ADMIN, "new_users_msg").format(
                    users_count=users_count,
                    timedelta=unpacked_cb.timedelta.value
                ), kb_builder
            case StatisticsEntity.BUYS:
                buys = await BuyRepository.get_by_timedelta(unpacked_cb.timedelta, session)
                total_profit = 0.0
                items_sold = 0
                for buy in buys:
                    total_profit += buy.total_price
                    items_sold += buy.quantity
                kb_builder.row(AdminConstants.back_to_main_button, unpacked_cb.get_back_button())
                return Localizator.get_text(BotEntity.ADMIN, "sales_statistics").format(
                    timedelta=unpacked_cb.timedelta,
                    total_profit=total_profit, items_sold=items_sold,
                    buys_count=len(buys), currency_sym=Localizator.get_currency_symbol()), kb_builder
            case StatisticsEntity.DEPOSITS:
                deposits = await DepositRepository.get_by_timedelta(unpacked_cb.timedelta, session)
                fiat_amount = 0.0
                btc_amount = 0.0
                ltc_amount = 0.0
                sol_amount = 0.0
                eth_amount = 0.0
                bnb_amount = 0.0
                for deposit in deposits:
                    match deposit.network:
                        case "BTC":
                            btc_amount += deposit.amount / pow(10, deposit.network.get_divider())
                        case "LTC":
                            ltc_amount += deposit.amount / pow(10, deposit.network.get_divider())
                        case "SOL":
                            sol_amount += deposit.amount / pow(10, deposit.network.get_divider())
                        case "ETH":
                            eth_amount += deposit.amount / pow(10, deposit.network.get_divider())
                        case "BNB":
                            bnb_amount += deposit.amount / pow(10, deposit.network.get_divider())
                prices = await CryptoApiWrapper.get_crypto_prices()
                btc_price = prices[Cryptocurrency.BTC.get_coingecko_name()][config.CURRENCY.value.lower()]
                ltc_price = prices[Cryptocurrency.LTC.get_coingecko_name()][config.CURRENCY.value.lower()]
                sol_price = prices[Cryptocurrency.SOL.get_coingecko_name()][config.CURRENCY.value.lower()]
                eth_price = prices[Cryptocurrency.ETH.get_coingecko_name()][config.CURRENCY.value.lower()]
                bnb_price = prices[Cryptocurrency.BNB.get_coingecko_name()][config.CURRENCY.value.lower()]
                fiat_amount += ((btc_amount * btc_price) + (ltc_amount * ltc_price) + (sol_amount * sol_price)
                                + (eth_amount * eth_price) + (bnb_amount * bnb_price))
                kb_builder.row(AdminConstants.back_to_main_button, unpacked_cb.get_back_button())
                return Localizator.get_text(BotEntity.ADMIN, "deposits_statistics_msg").format(
                    timedelta=unpacked_cb.timedelta, deposits_count=len(deposits),
                    btc_amount=btc_amount, ltc_amount=ltc_amount,
                    sol_amount=sol_amount, eth_amount=eth_amount,
                    bnb_amount=bnb_amount,
                    fiat_amount=fiat_amount, currency_text=Localizator.get_currency_text()), kb_builder

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
