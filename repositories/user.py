import datetime
import math

from sqlalchemy import select, update, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import StatisticsTimeDelta
from db import session_execute, session_flush

from models.user import UserDTO, User


class UserRepository:
    @staticmethod
    async def get_by_tgid(telegram_id: int, session: AsyncSession | Session) -> UserDTO | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        user = await session_execute(stmt, session)
        user = user.scalar()
        if user is not None:
            return UserDTO.model_validate(user, from_attributes=True)
        else:
            return user

    @staticmethod
    async def update(user_dto: UserDTO, session: Session | AsyncSession) -> None:
        user_dto_dict = user_dto.model_dump()
        none_keys = [k for k, v in user_dto_dict.items() if v is None]
        for k in none_keys:
            user_dto_dict.pop(k)
        stmt = update(User).where(User.telegram_id == user_dto.telegram_id).values(**user_dto_dict)
        await session_execute(stmt, session)

    @staticmethod
    async def create(user_dto: UserDTO, session: Session | AsyncSession) -> int:
        user = User(**user_dto.model_dump())
        session.add(user)
        await session_flush(session)
        return user.id

    @staticmethod
    async def get_active(session: Session | AsyncSession) -> list[UserDTO]:
        stmt = select(User).where(User.can_receive_messages == True)
        users = await session_execute(stmt, session)
        return [UserDTO.model_validate(user, from_attributes=True) for user in users.scalars().all()]

    @staticmethod
    async def get_all_count(session: Session | AsyncSession) -> int:
        stmt = func.count(User.id)
        users_count = await session_execute(stmt, session)
        return users_count.scalar_one()

    @staticmethod
    async def get_user_entity(user_entity: int | str, session: Session | AsyncSession) -> UserDTO | None:
        stmt = select(User).where(or_(User.telegram_id == user_entity, User.telegram_username == user_entity,
                                      User.id == user_entity))
        user = await session_execute(stmt, session)
        user = user.scalar()
        if user is None:
            return user
        else:
            return UserDTO.model_validate(user, from_attributes=True)

    @staticmethod
    async def get_by_timedelta(timedelta: StatisticsTimeDelta,
                               page: int, session: Session | AsyncSession) -> list[UserDTO]:
        start, end = timedelta.get_time_range()
        users_stmt = (select(User)
                      .where(User.registered_at >= start,
                             User.registered_at <= end)
                      .limit(config.PAGE_ENTRIES)
                      .offset(config.PAGE_ENTRIES * page))
        users = await session_execute(users_stmt, session)
        return [UserDTO.model_validate(user, from_attributes=True) for user in users.scalars().all()]

    @staticmethod
    async def get_max_page_by_timedelta(timedelta: StatisticsTimeDelta, session: Session | AsyncSession) -> int:
        start, end = timedelta.get_time_range()
        stmt = select(func.count(User.id)).where(
            User.registered_at >= start,
            User.registered_at <= end)
        users = await session_execute(stmt, session)
        users = users.scalar_one()
        if users % config.PAGE_ENTRIES == 0:
            return users / config.PAGE_ENTRIES - 1
        else:
            return math.trunc(users / config.PAGE_ENTRIES)
