from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from models.deposit import DepositDTO
from models.user import UserDTO
from repositories.deposit import DepositRepository


class DepositService:

    @staticmethod
    async def create(deposit: DepositDTO, session: AsyncSession | Session) -> int:
        return await DepositRepository.create(deposit, session)

    @staticmethod
    async def get_by_user_dto(user_dto: UserDTO, session: AsyncSession | Session) -> list[DepositDTO]:
        return await DepositRepository.get_by_user_dto(user_dto, session)
