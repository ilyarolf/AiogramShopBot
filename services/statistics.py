from collections import defaultdict
from datetime import datetime, timedelta
from aiogram.types import InputMediaPhoto, BufferedInputFile
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
from models.buy import BuyDTO
from models.deposit import DepositDTO
from models.user import UserDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.deposit import DepositRepository
from repositories.user import UserRepository
from utils.utils import get_text
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO


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
    def build_statistics_chart(objects: list[UserDTO | BuyDTO | DepositDTO],
                               time_delta: StatisticsTimeDelta,
                               language: Language, crypto_price: dict | None = None) -> bytes:
        start, end = time_delta.get_time_range()[0], datetime.now()
        day_count = (end.date() - start.date()).days + 1
        dates = [start.date() + timedelta(days=i) for i in range(day_count)]
        values = defaultdict(float)

        if len(objects) == 0:
            dto_type = None
        else:
            dto_type = type(objects[0])

        if dto_type == UserDTO:
            for user in objects:
                if user.registered_at:
                    d = user.registered_at.date()
                    if start.date() <= d <= end.date():
                        values[d] += 1
        elif dto_type == BuyDTO:
            for buy in objects:
                if buy.buy_datetime:
                    d = buy.buy_datetime.date()
                    if start.date() <= d <= end.date():
                        values[d] += buy.total_price
        elif dto_type == DepositDTO:
            for dep in objects:
                if dep.deposit_datetime:
                    d = dep.deposit_datetime.date()
                    if start.date() <= d <= end.date():
                        value = dep.amount / pow(10, dep.network.get_decimals()) * \
                                crypto_price[dep.network.get_coingecko_name()][config.CURRENCY.value.lower()]
                        values[d] += value

        y = [values[d] for d in dates]

        plt.style.use("ggplot")
        fig, ax = plt.subplots(figsize=(9, 4))

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d/%Y"))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))

        bars = ax.bar(dates, y, width=0.8)
        if dto_type:
            chart_ylabel, chart_title = dto_type.get_chart_text(language)
            ax.set_ylabel(chart_ylabel)
            ax.set_title(chart_title)
        ax.set_xlabel(get_text(language, BotEntity.ADMIN, "date"))

        plt.xticks(rotation=45)
        plt.tight_layout()

        for bar, value in zip(bars, y):
            height = bar.get_height()
            ax.annotate(
                f"{value:.0f}" if isinstance(value, (int, float)) else str(value),
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8
            )

        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)

        return buf.getvalue()

    @staticmethod
    async def get_statistics(callback_data: StatisticsCallback,
                             session: AsyncSession,
                             language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        timedelta_localized = get_text(language, BotEntity.ADMIN, f"{callback_data.timedelta}_day")
        match callback_data.statistics_entity:
            case StatisticsEntity.USERS:
                users = await UserRepository.get_by_timedelta(callback_data.timedelta, callback_data.page,
                                                              session)
                [kb_builder.button(text=user.telegram_username, url=f'tg://user?id={user.telegram_id}') for user in
                 users
                 if user.telegram_username]
                chart = StatisticsService.build_statistics_chart(users, callback_data.timedelta, language)
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(
                    kb_builder,
                    callback_data,
                    UserRepository.get_max_page_by_timedelta(callback_data.timedelta, session),
                    None,
                    language)
                kb_builder.row(AdminConstants.back_to_main_button(language), callback_data.get_back_button(language))
                caption = get_text(language, BotEntity.ADMIN, "new_users_msg").format(
                    users_count=len(users),
                    timedelta=timedelta_localized
                )
                media = InputMediaPhoto(
                    media=BufferedInputFile(file=chart,
                                            filename="chart.png"),
                    caption=caption
                )
                return media, kb_builder
            case StatisticsEntity.BUYS:
                buys = await BuyRepository.get_by_timedelta(callback_data.timedelta, session)
                chart = StatisticsService.build_statistics_chart(buys, callback_data.timedelta, language)
                total_profit = 0.0
                items_sold = 0
                for buy in buys:
                    total_profit += buy.total_price
                    buyItem_list = await BuyItemRepository.get_all_by_buy_id(buy.id, session)
                    items_sold += sum([len(buyItem.item_ids) for buyItem in buyItem_list])
                kb_builder.row(AdminConstants.back_to_main_button(language), callback_data.get_back_button(language))
                caption = get_text(language, BotEntity.ADMIN, "sales_statistics").format(
                    timedelta=timedelta_localized,
                    total_profit=total_profit, items_sold=items_sold,
                    buys_count=len(buys), currency_sym=config.CURRENCY.get_localized_symbol())
                media = InputMediaPhoto(
                    media=BufferedInputFile(file=chart,
                                            filename="chart.png"),
                    caption=caption
                )
                return media, kb_builder
            case StatisticsEntity.DEPOSITS:
                deposits = await DepositRepository.get_by_timedelta(callback_data.timedelta, session)
                prices = await CryptoApiWrapper.get_crypto_prices()
                chart = StatisticsService.build_statistics_chart(deposits, callback_data.timedelta, language, prices)
                fiat_amount = 0.0
                btc_amount = sum(
                    [btc_deposit.amount if btc_deposit.network == Cryptocurrency.BTC else 0 for btc_deposit in
                     deposits])
                ltc_amount = sum(
                    [ltc_deposit.amount if ltc_deposit.network == Cryptocurrency.LTC else 0 for ltc_deposit in
                     deposits])
                sol_amount = sum(
                    [sol_deposit.amount if sol_deposit.network == Cryptocurrency.SOL else 0 for sol_deposit in
                     deposits])
                eth_amount = sum(
                    [eth_deposit.amount if eth_deposit.network == Cryptocurrency.ETH else 0 for eth_deposit in
                     deposits])
                bnb_amount = sum(
                    [bnb_deposit.amount if bnb_deposit.network == Cryptocurrency.BNB else 0 for bnb_deposit in
                     deposits])
                btc_amount = btc_amount / pow(10, Cryptocurrency.BTC.get_decimals())
                ltc_amount = ltc_amount / pow(10, Cryptocurrency.LTC.get_decimals())
                sol_amount = sol_amount / pow(10, Cryptocurrency.SOL.get_decimals())
                eth_amount = eth_amount / pow(10, Cryptocurrency.ETH.get_decimals())
                bnb_amount = bnb_amount / pow(10, Cryptocurrency.BNB.get_decimals())
                btc_price = prices[Cryptocurrency.BTC.get_coingecko_name()][config.CURRENCY.value.lower()]
                ltc_price = prices[Cryptocurrency.LTC.get_coingecko_name()][config.CURRENCY.value.lower()]
                sol_price = prices[Cryptocurrency.SOL.get_coingecko_name()][config.CURRENCY.value.lower()]
                eth_price = prices[Cryptocurrency.ETH.get_coingecko_name()][config.CURRENCY.value.lower()]
                bnb_price = prices[Cryptocurrency.BNB.get_coingecko_name()][config.CURRENCY.value.lower()]
                fiat_amount += ((btc_amount * btc_price) + (ltc_amount * ltc_price) + (sol_amount * sol_price)
                                + (eth_amount * eth_price) + (bnb_amount * bnb_price))
                kb_builder.row(AdminConstants.back_to_main_button(language), callback_data.get_back_button(language))
                caption = get_text(language, BotEntity.ADMIN, "deposits_statistics_msg").format(
                    timedelta=timedelta_localized, deposits_count=len(deposits),
                    btc_amount=btc_amount, ltc_amount=ltc_amount,
                    sol_amount=sol_amount, eth_amount=eth_amount,
                    bnb_amount=bnb_amount,
                    fiat_amount=fiat_amount, currency_text=config.CURRENCY.get_localized_text())
                media = InputMediaPhoto(
                    media=BufferedInputFile(file=chart,
                                            filename="chart.png"),
                    caption=caption
                )
                return media, kb_builder
