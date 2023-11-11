import datetime

from sqlalchemy import select, update
from db import async_session_maker

from models.user import User
from utils.CryptoAddressGenerator import CryptoAddressGenerator


class UserService:
    @staticmethod
    async def is_exist(telegram_id: int) -> bool:
        async with async_session_maker() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            is_exist = await session.execute(stmt)
            return is_exist.scalar() is not None

    @staticmethod
    async def get_next_user_id() -> int:
        async with async_session_maker() as session:
            query = select(User.id).order_by(User.id.desc()).limit(1)
            last_user_id = await session.execute(query)
            last_user_id = last_user_id.scalar()
            if last_user_id is None:
                return 0
            else:
                return int(last_user_id) + 1

    @staticmethod
    async def create(telegram_id: int, telegram_username: str):
        async with async_session_maker() as session:
            next_user_id = await UserService.get_next_user_id()
            crypto_addr_gen = CryptoAddressGenerator()
            crypto_addresses = crypto_addr_gen.get_addresses(i=0)
            new_user = User(
                id=next_user_id,
                telegram_username=telegram_username,
                telegram_id=telegram_id,
                btc_address=crypto_addresses['btc'],
                ltc_address=crypto_addresses['ltc'],
                trx_address=crypto_addresses['trx'],
                seed=crypto_addr_gen.mnemonic_str
            )
            session.add(new_user)
            await session.commit()

    @staticmethod
    async def update_username(telegram_id: int, telegram_username: str):
        async with async_session_maker() as session:
            user_from_db = await UserService.get_by_tgid(telegram_id)
            if user_from_db and user_from_db.telegram_username != telegram_username:
                stmt = update(User).where(User.telegram_id == telegram_id).values(telegram_username=telegram_username)
                await session.execute(stmt)
                await session.commit()

    @staticmethod
    async def get_by_tgid(telegram_id: int) -> User:
        async with async_session_maker() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            user_from_db = await session.execute(stmt)
            user_from_db = user_from_db.scalar()
            return user_from_db

    @staticmethod
    async def can_refresh_balance(telegram_id: int) -> bool:
        async with async_session_maker() as session:
            stmt = select(User.last_balance_refresh).where(User.telegram_id == telegram_id)
            user_last_refresh = await session.execute(stmt)
            user_last_refresh = user_last_refresh.scalar()
            if user_last_refresh is None:
                return True
            now_time = datetime.datetime.now()
            timedelta = (now_time - user_last_refresh).total_seconds()
            return timedelta > 30

    @staticmethod
    async def create_last_balance_refresh_data(telegram_id: int):
        time = datetime.datetime.now()
        async with async_session_maker() as session:
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                last_balance_refresh=time)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_balances(telegram_id: int) -> dict:
        async with async_session_maker() as session:
            stmt = select(User.btc_balance, User.ltc_balance, User.usdt_balance).where(User.telegram_id == telegram_id)
            user_balances = await session.execute(stmt)
            user_balances = user_balances.fetchone()
            keys = ["btc_balance", "ltc_balance", "usdt_balance"]
            user_balances = dict(zip(keys, user_balances))
            return user_balances

    @staticmethod
    async def get_addresses(telegram_id: int) -> dict:
        async with async_session_maker() as session:
            stmt = select(User.btc_address, User.ltc_address, User.trx_address).where(User.telegram_id == telegram_id)
            user_addresses = await session.execute(stmt)
            user_addresses = user_addresses.fetchone()
            keys = ["btc_address", "ltc_address", "trx_address"]
            user_addresses = dict(zip(keys, user_addresses))
            return user_addresses

    @staticmethod
    async def update_crypto_balances(telegram_id: int, new_crypto_balances: dict):
        async with async_session_maker() as session:
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                btc_balance=new_crypto_balances["btc_balance"],
                ltc_balance=new_crypto_balances["ltc_balance"],
                usdt_balance=new_crypto_balances["usdt_balance"],
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def update_top_up_amount(telegram_id, deposit_amount):
        async with async_session_maker() as session:
            get_old_top_up_amount_stmt = select(User.top_up_amount).where(User.telegram_id == telegram_id)
            old_top_up_amount = await session.execute(get_old_top_up_amount_stmt)
            old_top_up_amount = old_top_up_amount.scalar()
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                top_up_amount=round(old_top_up_amount + deposit_amount, 2))
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def is_buy_possible(telegram_id, total_price):
        user = await UserService.get_by_tgid(telegram_id)
        balance = user.top_up_amount - user.consume_records
        return balance >= total_price

    @staticmethod
    async def update_consume_records(telegram_id: int, total_price: float):
        async with async_session_maker() as session:
            get_old_consume_records_stmt = select(User.consume_records).where(User.telegram_id == telegram_id)
            old_consume_records = await session.execute(get_old_consume_records_stmt)
            old_consume_records = old_consume_records.scalar()
            stmt = update(User).where(User.telegram_id == telegram_id).values(
                consume_records=old_consume_records + total_price)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_users_tg_ids():
        async with async_session_maker() as session:
            stmt = select(User.telegram_id)
            user_ids = await session.execute(stmt)
            user_ids = user_ids.scalars().all()
            return user_ids

    @staticmethod
    async def get_new_users():
        async with async_session_maker() as session:
            stmt = select(User).where(User.is_new == 1)
            new_users = await session.execute(stmt)
            new_users = new_users.scalars().all()
            await UserService.__set_new_users_not_new()
            return new_users

    @staticmethod
    async def __set_new_users_not_new():
        async with async_session_maker() as session:
            stmt = update(User).where(User.is_new == 1).values(is_new=0)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def reduce_consume_records(user_id: int, total_price):
        async with async_session_maker() as session:
            old_consume_records_stmt = select(User.consume_records).where(User.id == user_id)
            old_consume_records = await session.execute(old_consume_records_stmt)
            old_consume_records = old_consume_records.scalar()
            stmt = update(User).where(User.id == user_id).values(consume_records=old_consume_records-total_price)
            await session.execute(stmt)
            await session.commit()
