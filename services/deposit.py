from models.deposit import DepositDTO
from models.user import UserDTO
from repositories.deposit import DepositRepository


class DepositService:

    @staticmethod
    async def create(deposit: DepositDTO) -> int:
        return await DepositRepository.create(deposit)

    @staticmethod
    async def get_by_user_dto(user_dto: UserDTO):
        return await DepositRepository.get_by_user_dto(user_dto)
