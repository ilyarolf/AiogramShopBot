import datetime
import math
from typing import Union
from sqlalchemy import select, update, func, or_
import config
from db import session_execute, session_commit, get_db_session
from models.user import User
from utils.CryptoAddressGenerator import CryptoAddressGenerator
from utils.localizator import Localizator, BotEntity


class UserService:

    @staticmethod
    async def is_exist(telegram_id: int) -> bool:
        async with get_db_session() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            is_exist = await session_execute(stmt, session)
            return is_exist.scalar() is not None

    @staticmethod
    async def create(telegram_id: int, telegram_username: str):
        async with get_db_session() as session:
            crypto_addr_gen = CryptoAddressGenerator()
            crypto_addresses = crypto_addr_gen.get_addresses(i=0)
            new_user = User(
                telegram_username=telegram_username,
                telegram_id=telegram_id,
                btc_address=crypto_addresses['btc'],
                ltc_address=crypto_addresses['ltc'],
                trx_address=crypto_addresses['trx'],
                eth_address=crypto_addresses['eth'],
                sol_address=crypto_addresses['sol'],
                seed=crypto_addr_gen.mnemonic_str
            )
            session.add(new_user)
            await session_commit(session)

    @staticmethod
    async def update_username(telegram_id: int, telegram_username: str):
        async with get_db_session() as session:
            user_from_db = await UserService.get_by_tgid(telegram_id)
            if user_from_db and user_from_db.telegram_username != telegram_username:
                stmt = update(User).where(User.telegram_id == telegram_id).values(telegram_username=telegram_username)
                await session_execute(stmt, session)
                await session_commit(session)

    @staticmethod
    async def get_by_tgid(telegram_id: int) -> User:
        async with get_db_session() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user_from_db = await session_execute(stmt, session)
            user_from_db = user_from_db.scalar()
            return user_from_db

    @staticmethod
    async def can_refresh_balance(telegram_id: int) -> bool:
        async with get_db_session() as session:
            stmt = select(User.last_balance_refresh).where(User.telegram_id == telegram_id)
            user_last_refresh = await session_execute(stmt, session)
            user_last_refresh = user_last_refresh.scalar()
            if user_last_refresh is None:
                return True
            now_time = datetime.datetime.now()
            timedelta = (now_time - user_last_refresh).total_seconds()
            return timedelta > 30

    @staticmethod
    async def create_last_balance_refresh_data(telegram_id: int):
        async with get_db_session() as session:
            time = datetime.datetime.now()
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                last_balance_refresh=time)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_balances(telegram_id: int) -> dict:
        async with get_db_session() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user_balances = await session_execute(stmt, session)
            user_balances = user_balances.scalar()
            user_balances = [user_balances.btc_balance, user_balances.ltc_balance,
                             user_balances.usdt_trc20_balance, user_balances.usdd_trc20_balance,
                             user_balances.usdt_erc20_balance, user_balances.usdc_erc20_balance]
            keys = ["btc_balance", "ltc_balance", "trc_20_usdt_balance", "trc_20_usdd_balance", "erc_20_usdt_balance",
                    "erc_20_usdc_balance"]
            user_balances = dict(zip(keys, user_balances))
            return user_balances

    @staticmethod
    async def get_addresses(telegram_id: int) -> dict:
        async with get_db_session() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user_addresses = await session_execute(stmt, session)
            user_addresses = user_addresses.scalar()
            user_addresses = [user_addresses.btc_address, user_addresses.ltc_address,
                              user_addresses.trx_address, user_addresses.eth_address,
                              user_addresses.sol_address]
            keys = ["btc_address", "ltc_address", "trx_address", "eth_address", "sol_address"]
            user_addresses = dict(zip(keys, user_addresses))
            return user_addresses

    @staticmethod
    async def update_crypto_balances(telegram_id: int, new_crypto_balances: dict):
        async with get_db_session() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session_execute(stmt, session)
            user = result.scalar()
            balance_fields_map = {
                "btc_deposit": "btc_balance",
                "ltc_deposit": "ltc_balance",
                "sol_deposit": "sol_balance",
                "usdt_trc20_deposit": "usdt_trc20_balance",
                "usdd_trc20_deposit": "usdd_trc20_balance",
                "usdd_erc20_deposit": "usdd_erc20_balance",
                "usdc_erc20_deposit": "usdc_erc20_balance",
            }
            update_values = {}

            for key, value in new_crypto_balances.items():
                if key in balance_fields_map:
                    field_name = balance_fields_map[key]
                    current_balance = getattr(user, field_name)
                    update_values[field_name] = current_balance + value

            if update_values:
                stmt = update(User).where(User.telegram_id == telegram_id).values(**update_values)
                await session_execute(stmt, session)
                await session_commit(session)

    @staticmethod
    async def update_top_up_amount(telegram_id: int, deposit_amount: float):
        async with get_db_session() as session:
            stmt = select(User.top_up_amount).where(User.telegram_id == telegram_id)
            old_top_up_amount = await session_execute(stmt, session)
            old_top_up_amount = old_top_up_amount.scalar()
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                top_up_amount=round(old_top_up_amount + deposit_amount, 2))
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def is_buy_possible(telegram_id, total_price):
        user = await UserService.get_by_tgid(telegram_id)
        balance = user.top_up_amount - user.consume_records
        return balance >= total_price

    @staticmethod
    async def update_consume_records(telegram_id: int, total_price: float):
        async with get_db_session() as session:
            get_old_consume_records_stmt = select(User.consume_records).where(User.telegram_id == telegram_id)
            old_consume_records = await session_execute(get_old_consume_records_stmt, session)
            old_consume_records = old_consume_records.scalar()
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                consume_records=old_consume_records + total_price)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_users_tg_ids_for_sending():
        async with get_db_session() as session:
            stmt = select(User.telegram_id).where(User.can_receive_messages == True)
            user_ids = await session_execute(stmt, session)
            user_ids = user_ids.scalars().all()
            return user_ids

    @staticmethod
    async def get_all_users_count():
        async with get_db_session() as session:
            stmt = func.count(User.id)
            users_count = await session_execute(stmt, session)
            return users_count.scalar()

    @staticmethod
    async def reduce_consume_records(user_id: int, total_price):
        async with get_db_session() as session:
            stmt = select(User.consume_records).where(User.id == user_id)
            old_consume_records = await session_execute(stmt, session)
            old_consume_records = old_consume_records.scalar()
            stmt = update(User).where(User.id == user_id).values(consume_records=old_consume_records - total_price)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_new_users_by_timedelta(timedelta_int, page):
        async with get_db_session() as session:
            current_time = datetime.datetime.now()
            one_day_interval = datetime.timedelta(days=int(timedelta_int))
            time_to_subtract = current_time - one_day_interval
            stmt = select(User).where(User.registered_at >= time_to_subtract, User.telegram_username != None).limit(
                config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES)
            count_stmt = select(func.count(User.id)).where(User.registered_at >= time_to_subtract)
            users = await session_execute(stmt, session)
            users_count = await session_execute(count_stmt, session)
            return users.scalars().all(), users_count.scalar_one()

    @staticmethod
    async def get_max_page_for_users_by_timedelta(timedelta_int):
        async with get_db_session() as session:
            current_time = datetime.datetime.now()
            one_day_interval = datetime.timedelta(days=int(timedelta_int))
            time_to_subtract = current_time - one_day_interval
            stmt = select(func.count(User.id)).where(User.registered_at >= time_to_subtract,
                                                     User.telegram_username != None)
            users = await session_execute(stmt, session)
            users = users.scalar_one()
            if users % config.PAGE_ENTRIES == 0:
                return users / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(users / config.PAGE_ENTRIES)

    @staticmethod
    async def update_receive_messages(telegram_id, new_value):
        async with get_db_session() as session:
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                can_receive_messages=new_value)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_by_id(user_id: int) -> User:
        async with get_db_session() as session:
            stmt = select(User).where(User.id == user_id)
            user = await session_execute(stmt, session)
            return user.scalar()

    @staticmethod
    async def get_user_entity(user_entity: Union[str, int]) -> User:
        async with get_db_session() as session:
            stmt = select(User).where(or_(User.telegram_id == user_entity, User.telegram_username == user_entity))
            user = await session_execute(stmt, session)
            return user.scalar()

    @staticmethod
    async def balance_management(state_data: dict):
        operation = state_data['operation']
        user_entity = state_data['user_entity']
        balance_value = state_data['balance_value']
        user = await UserService.get_user_entity(user_entity)
        if user is None:
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_user_not_found")
        elif operation == "plus":
            await UserService.update_top_up_amount(user.telegram_id, float(balance_value))
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_added_success").format(
                amount=balance_value,
                telegram_id=user.telegram_id)
        elif operation == "minus":
            await UserService.update_consume_records(user.telegram_id, float(balance_value))
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_reduced_success").format(
                amount=balance_value,
                telegram_id=user.telegram_id)
