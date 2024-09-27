from sqlalchemy import select

from db import async_session_maker
from models.deposit import Deposit


class DepositService:

    @staticmethod
    async def get_next_user_id() -> int:
        async with async_session_maker() as session:
            query = select(Deposit.id).order_by(Deposit.id.desc()).limit(1)
            last_user_id = await session.execute(query)
            last_user_id = last_user_id.scalar()
            if last_user_id is None:
                return 0
            else:
                return int(last_user_id) + 1

    @staticmethod
    async def create(tx_id, user_id, network, token_name, amount):
        async with async_session_maker() as session:
            next_deposit_id = await DepositService.get_next_user_id()
            dep = Deposit(id=next_deposit_id,
                          user_id=user_id,
                          tx_id=tx_id,
                          network=network,
                          token_name=token_name,
                          amount=amount)
            session.add(dep)
            await session.commit()
            return next_deposit_id

    @staticmethod
    async def get_by_user_id(user_id):
        async with async_session_maker() as session:
            stmt = select(Deposit).where(Deposit.user_id == user_id)
            deposits = await session.execute(stmt)
            deposits = deposits.scalars().all()
            return deposits
