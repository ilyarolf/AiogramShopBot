from sqlalchemy import select

from db import get_db_session, session_execute
from models.deposit import Deposit
from models.user import UserDTO


class DepositRepository:
    @staticmethod
    async def get_by_user_dto(user_dto: UserDTO):
        stmt = select(Deposit).where(Deposit.user_id == user_dto.id)
        async with get_db_session() as session:
            deposits = await session_execute(stmt, session)
            return deposits.scalars().all()
