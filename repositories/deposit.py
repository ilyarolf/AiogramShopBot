import datetime

from sqlalchemy import select

from callbacks import StatisticsTimeDelta
from db import get_db_session, session_execute
from models.deposit import Deposit, DepositDTO
from models.user import UserDTO


class DepositRepository:
    @staticmethod
    async def get_by_user_dto(user_dto: UserDTO):
        stmt = select(Deposit).where(Deposit.user_id == user_dto.id)
        async with get_db_session() as session:
            deposits = await session_execute(stmt, session)
            return deposits.scalars().all()

    @staticmethod
    async def get_by_timedelta(timedelta: StatisticsTimeDelta) -> list[DepositDTO]:
        current_time = datetime.datetime.now()
        timedelta = datetime.timedelta(days=timedelta.value)
        time_interval = current_time - timedelta
        stmt = select(Deposit).where(Deposit.deposit_datetime >= time_interval)
        async with get_db_session() as session:
            deposits = await session_execute(stmt, session)
            return [DepositDTO.model_validate(deposit) for deposit in deposits.scalars().all()]
