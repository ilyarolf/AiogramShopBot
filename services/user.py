from sqlalchemy import exists, select
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
            crypto_addresses = CryptoAddressGenerator().get_addresses(next_user_id)
            new_user = User(
                id=next_user_id,
                telegram_username=telegram_username,
                telegram_id=telegram_id,
                btc_address=crypto_addresses['btc'],
                ltc_address=crypto_addresses['ltc'],
                trx_address=crypto_addresses['trx'],
            )
            session.add(new_user)
            await session.commit()
