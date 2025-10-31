"""
User Strike Repository

Handles database operations for the strike system.
Strikes are penalties for order timeouts and cancellations.
"""

import logging
from datetime import datetime
from typing import List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from enums.strike_type import StrikeType
from models.user_strike import UserStrike, UserStrikeDTO


class UserStrikeRepository:
    """Repository for user strike database operations"""

    @staticmethod
    async def create(user_strike_dto: UserStrikeDTO, session: AsyncSession | Session) -> UserStrike:
        """
        Create a new strike record

        Args:
            user_strike_dto: Strike data
            session: Database session

        Returns:
            Created UserStrike instance
        """
        strike = UserStrike(
            user_id=user_strike_dto.user_id,
            strike_type=user_strike_dto.strike_type,
            order_id=user_strike_dto.order_id,
            reason=user_strike_dto.reason
        )

        session.add(strike)
        logging.info(f"⚠️ Strike created: user_id={user_strike_dto.user_id}, type={user_strike_dto.strike_type.name}, order_id={user_strike_dto.order_id}")

        return strike

    @staticmethod
    async def get_by_user_id(user_id: int, session: AsyncSession | Session) -> List[UserStrike]:
        """
        Get all strikes for a user

        Args:
            user_id: User ID
            session: Database session

        Returns:
            List of UserStrike instances
        """
        if isinstance(session, AsyncSession):
            result = await session.execute(
                select(UserStrike)
                .where(UserStrike.user_id == user_id)
                .order_by(UserStrike.created_at.desc())
            )
            return list(result.scalars().all())
        else:
            return session.query(UserStrike).filter(UserStrike.user_id == user_id).order_by(UserStrike.created_at.desc()).all()

    @staticmethod
    async def count_by_user_id(user_id: int, session: AsyncSession | Session) -> int:
        """
        Count total strikes for a user

        Args:
            user_id: User ID
            session: Database session

        Returns:
            Strike count
        """
        if isinstance(session, AsyncSession):
            result = await session.execute(
                select(func.count(UserStrike.id)).where(UserStrike.user_id == user_id)
            )
            return result.scalar() or 0
        else:
            return session.query(func.count(UserStrike.id)).filter(UserStrike.user_id == user_id).scalar() or 0

    @staticmethod
    async def get_by_order_id(order_id: int, session: AsyncSession | Session) -> UserStrike | None:
        """
        Get strike associated with an order

        Args:
            order_id: Order ID
            session: Database session

        Returns:
            UserStrike instance or None
        """
        if isinstance(session, AsyncSession):
            result = await session.execute(
                select(UserStrike).where(UserStrike.order_id == order_id)
            )
            return result.scalar_one_or_none()
        else:
            return session.query(UserStrike).filter(UserStrike.order_id == order_id).first()
