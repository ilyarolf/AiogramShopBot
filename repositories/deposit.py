import datetime

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import StatisticsTimeDelta
from db import session_execute, session_flush
from enums.cryptocurrency import Cryptocurrency
from models.deposit import Deposit, DepositDTO
from models.user import UserDTO


class DepositRepository:
    @staticmethod
    async def get_by_user_dto(user_dto: UserDTO, session: Session | AsyncSession) -> list[DepositDTO]:
        stmt = select(Deposit).where(Deposit.user_id == user_dto.id)
        deposits = await session_execute(stmt, session)
        return [DepositDTO.model_validate(deposit, from_attributes=True) for deposit in deposits.scalars().all()]

    @staticmethod
    async def get_by_timedelta(timedelta: StatisticsTimeDelta, session: Session | AsyncSession) -> list[DepositDTO]:
        current_time = datetime.datetime.now()
        timedelta = datetime.timedelta(days=timedelta.value)
        time_interval = current_time - timedelta
        stmt = select(Deposit).where(Deposit.deposit_datetime >= time_interval)
        deposits = await session_execute(stmt, session)
        return [DepositDTO.model_validate(deposit, from_attributes=True) for deposit in deposits.scalars().all()]

    @staticmethod
    async def create(deposit: DepositDTO, session: Session | AsyncSession) -> int:
        dep = Deposit(**deposit.model_dump())
        session.add(dep)
        await session_flush(session)
        return dep.id
