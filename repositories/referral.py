from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import session_flush, session_execute
from models.referral import ReferralBonusDTO, ReferralBonus


class ReferralRepository:
    @staticmethod
    async def create(referral_bonus_dto: ReferralBonusDTO, session: AsyncSession) -> ReferralBonusDTO:
        referral_bonus = ReferralBonus(**referral_bonus_dto.model_dump(exclude={"referral_user_dto",
                                                                                "referrer_user_dto"}))
        session.add(referral_bonus)
        await session_flush(session)
        referral_bonus_dto.id = referral_bonus.id
        return referral_bonus_dto

    @staticmethod
    async def get_bonus_sum_as_referral(referral_user_id: int, session: AsyncSession):
        stmt = (
            select(
                func.coalesce(
                    func.sum(ReferralBonus.applied_referral_bonus),
                    0
                )
            )
            .where(ReferralBonus.referral_user_id == referral_user_id)
        )
        result = await session_execute(stmt, session)
        return result.scalar_one()

    @staticmethod
    async def get_bonus_sum_as_referrer(referrer_user_id: int, session: AsyncSession):
        stmt = (
            select(
                func.coalesce(
                    func.sum(ReferralBonus.applied_referral_bonus),
                    0
                )
            )
            .where(ReferralBonus.referrer_user_id == referrer_user_id)
        )
        result = await session_execute(stmt, session)
        return result.scalar_one()
