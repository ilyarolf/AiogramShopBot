from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
import config
from callbacks import StatisticsCallback
from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from enums.statistics_entity import StatisticsEntity
from enums.statistics_timedelta import StatisticsTimeDelta
from handlers.admin.constants import AdminConstants
from handlers.common.common import add_pagination_buttons
from repositories.buy import BuyRepository
from repositories.deposit import DepositRepository
from repositories.user import UserRepository
from utils.utils import get_text


class StatisticsService:
    @staticmethod
    async def get_statistics_menu(language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "users_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.USERS))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "buys_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.BUYS))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "deposits_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.DEPOSITS))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "get_database_file"),
                          callback_data=StatisticsCallback.create(3))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button(language))
        return get_text(language, BotEntity.ADMIN, "pick_statistics_entity"), kb_builder

    @staticmethod
    async def get_timedelta_menu(callback_data: StatisticsCallback,
                                 language: Language) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "1_day"),
                          callback_data=StatisticsCallback.create(callback_data.level + 1,
                                                                  callback_data.statistics_entity,
                                                                  StatisticsTimeDelta.DAY))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "7_day"),
                          callback_data=StatisticsCallback.create(callback_data.level + 1,
                                                                  callback_data.statistics_entity,
                                                                  StatisticsTimeDelta.WEEK))
        kb_builder.button(text=get_text(language, BotEntity.ADMIN, "30_day"),
                          callback_data=StatisticsCallback.create(callback_data.level + 1,
                                                                  callback_data.statistics_entity,
                                                                  StatisticsTimeDelta.MONTH))
        kb_builder.row(callback_data.get_back_button(language, 0))
        return get_text(language, BotEntity.ADMIN, "statistics_timedelta"), kb_builder

    @staticmethod
    async def get_statistics(callback_data: StatisticsCallback,
                             session: AsyncSession,
                             language: Language):
        kb_builder = InlineKeyboardBuilder()
        match callback_data.statistics_entity:
            case StatisticsEntity.USERS:
                users, users_count = await UserRepository.get_by_timedelta(callback_data.timedelta, callback_data.page,
                                                                           session)
                [kb_builder.button(text=user.telegram_username, url=f't.me/{user.telegram_username}') for user in
                 users
                 if user.telegram_username]
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(
                    kb_builder,
                    callback_data,
                    UserRepository.get_max_page_by_timedelta(callback_data.timedelta, session),
                    None,
                    language)
                kb_builder.row(AdminConstants.back_to_main_button(language), callback_data.get_back_button(language))
                return get_text(language, BotEntity.ADMIN, "new_users_msg").format(
                    users_count=users_count,
                    timedelta=callback_data.timedelta.value
                ), kb_builder
            case StatisticsEntity.BUYS:
                buys = await BuyRepository.get_by_timedelta(callback_data.timedelta, session)
                total_profit = 0.0
                items_sold = 0
                for buy in buys:
                    total_profit += buy.total_price
                    items_sold += buy.quantity
                kb_builder.row(AdminConstants.back_to_main_button(language), callback_data.get_back_button(language))
                return get_text(language, BotEntity.ADMIN, "sales_statistics").format(
                    timedelta=callback_data.timedelta,
                    total_profit=total_profit, items_sold=items_sold,
                    buys_count=len(buys), currency_sym=config.CURRENCY.get_localized_symbol()), kb_builder
            case StatisticsEntity.DEPOSITS:
                deposits = await DepositRepository.get_by_timedelta(callback_data.timedelta, session)
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
                kb_builder.row(AdminConstants.back_to_main_button(language), callback_data.get_back_button(language))
                return get_text(language, BotEntity.ADMIN, "deposits_statistics_msg").format(
                    timedelta=callback_data.timedelta, deposits_count=len(deposits),
                    btc_amount=btc_amount, ltc_amount=ltc_amount,
                    sol_amount=sol_amount, eth_amount=eth_amount,
                    bnb_amount=bnb_amount,
                    fiat_amount=fiat_amount, currency_text=config.CURRENCY.get_localized_text()), kb_builder
