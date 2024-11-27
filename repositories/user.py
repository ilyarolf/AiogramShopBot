from sqlalchemy import select, update, func, or_
from db import get_db_session, session_commit, session_execute, session_refresh

from models.user import UserDTO, User
from utils.CryptoAddressGenerator import CryptoAddressGenerator


class UserRepository:
    @staticmethod
    async def get_by_tgid(user_dto: UserDTO) -> UserDTO | None:
        stmt = select(User).where(User.telegram_id == user_dto.telegram_id)
        async with get_db_session() as session:
            user = await session_execute(stmt, session)
            user = user.scalar()
            if user is not None:
                return UserDTO.model_validate(user, from_attributes=True)
            else:
                return user

    @staticmethod
    async def update(user_dto: UserDTO) -> None:
        user_dto_dict = user_dto.__dict__
        none_keys = [k for k, v in user_dto_dict.items() if v is None]
        for k in none_keys:
            user_dto_dict.pop(k)
        stmt = update(User).where(User.telegram_id == user_dto.telegram_id).values(**user_dto_dict)
        async with get_db_session() as session:
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def create(user_dto: UserDTO) -> int:
        crypto_addr_gen = CryptoAddressGenerator()
        crypto_addresses = crypto_addr_gen.get_addresses()
        user_dto.btc_address = crypto_addresses['btc']
        user_dto.ltc_address = crypto_addresses['ltc']
        user_dto.trx_address = crypto_addresses['trx']
        user_dto.eth_address = crypto_addresses['eth']
        user_dto.sol_address = crypto_addresses['sol']
        user_dto.seed = crypto_addr_gen.mnemonic_str
        async with get_db_session() as session:
            user = User(**user_dto.__dict__)
            session.add(user)
            await session_commit(session)
            await session_refresh(session, user)
            return user.id

    @staticmethod
    async def get_active() -> list[UserDTO]:
        stmt = select(User).where(User.can_receive_messages == True)
        async with get_db_session() as session:
            users = await session_execute(stmt, session)
            return [UserDTO.model_validate(user, from_attributes=True) for user in users.scalars().all()]

    @staticmethod
    async def get_all_count() -> int:
        stmt = func.count(User.id)
        async with get_db_session() as session:
            users_count = await session_execute(stmt, session)
            return users_count.scalar_one()

    @staticmethod
    async def get_user_entity(user_entity: int | str) -> UserDTO | None:
        stmt = select(User).where(or_(User.telegram_id == user_entity, User.telegram_username == user_entity))
        async with get_db_session() as session:
            user = await session_execute(stmt, session)
            user = user.scalar()
            if user is None:
                return user
            else:
                return UserDTO.model_validate(user, from_attributes=True)

