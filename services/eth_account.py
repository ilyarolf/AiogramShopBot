from sqlalchemy import select

from db import async_session_maker
from models.eth_account import EthAccount


class EthAccountService:

    @staticmethod
    async def get_next_user_id() -> int:
        async with async_session_maker() as session:
            query = select(EthAccount.id).order_by(EthAccount.id.desc()).limit(1)
            last_user_id = await session.execute(query)
            last_user_id = last_user_id.scalar()
            if last_user_id is None:
                return 0
            else:
                return int(last_user_id) + 1

    @staticmethod
    async def create(address: str) -> int:
        async with async_session_maker() as session:
            next_account_id = await EthAccountService.get_next_user_id()
            eth_acc = EthAccount(id=next_account_id,
                                 address=address)
            session.add(eth_acc)
            await session.commit()
            return next_account_id

    @staticmethod
    async def get_by_id(id: int) -> EthAccount:
        async with async_session_maker() as session:
            stmt = select(EthAccount).where(EthAccount.id == id)
            result = await session.execute(stmt)
            return result.scalar_one()
