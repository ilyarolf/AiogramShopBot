from typing import Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute, session_commit
from models.deposit import Deposit


class DepositService:

    @staticmethod
    async def get_next_user_id(session: Union[AsyncSession, Session]) -> int:
        stmt = select(Deposit.id).order_by(Deposit.id.desc()).limit(1)
        last_user_id = await session_execute(stmt, session)
        last_user_id = last_user_id.scalar()
        if last_user_id is None:
            return 0
        else:
            return int(last_user_id) + 1

    @staticmethod
    async def create(session: Union[AsyncSession, Session], tx_id, user_id, network, token_name, amount, vout=None):
        next_deposit_id = await DepositService.get_next_user_id(session)
        dep = Deposit(id=next_deposit_id,
                      user_id=user_id,
                      tx_id=tx_id,
                      network=network,
                      token_name=token_name,
                      amount=amount,
                      vout=vout)
        session.add(dep)
        await session_commit(session)
        return next_deposit_id

    @staticmethod
    async def get_by_user_id(user_id, session: Union[AsyncSession, Session]):
        stmt = select(Deposit).where(Deposit.user_id == user_id)
        deposits = await session_execute(stmt, session)
        deposits = deposits.scalars().all()
        return deposits
