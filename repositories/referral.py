from sqlalchemy.ext.asyncio import AsyncSession

from db import session_flush
from models.referral import ReferralBonusDTO, ReferralBonus


class ReferralRepository:
    @staticmethod
    async def create(referral_bonus_dto: ReferralBonusDTO, session: AsyncSession) -> ReferralBonusDTO:
        referral_bonus = ReferralBonus(**referral_bonus_dto.model_dump())
        session.add(referral_bonus)
        await session_flush(session)
        return ReferralBonusDTO.model_validate(referral_bonus, from_attributes=True)
