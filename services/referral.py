import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession

import config
from models.payment import ProcessingPaymentDTO
from models.referral import ReferralBonusDTO
from models.user import UserDTO
from repositories.deposit import DepositRepository
from repositories.referral import ReferralRepository
from repositories.user import UserRepository


class ReferralService:
    @staticmethod
    async def create_referral_code(user_dto: UserDTO, session: AsyncSession):
        deposits_sum = await DepositRepository.get_sum(user_dto.id, session)
        if user_dto.referral_code is None and deposits_sum >= config.MIN_REFERRER_TOTAL_DEPOSIT:
            alphabet = string.ascii_uppercase + string.digits
            random_part = ''.join(secrets.choice(alphabet) for _ in range(6))
            referral_code = f"U_{random_part}"
            user_dto.referral_code = referral_code

    @staticmethod
    async def process_referral_bonus(payment_dto: ProcessingPaymentDTO,
                                     user_dto: UserDTO,
                                     session: AsyncSession):
        referral_deposits_qty = await DepositRepository.get_deposits_qty_by_user_id(user_dto.id, session)
        referral_bonus = 0
        if user_dto.referred_by_user_id is not None and referral_deposits_qty <= config.REFERRAL_BONUS_DEPOSIT_LIMIT:
            referral_bonus = payment_dto.fiatAmount * (config.REFERRAL_BONUS_PERCENT / 100)
        referral_bonus_cap = await DepositRepository.get_sum(user_dto.id, session) * (
                config.REFERRAL_BONUS_CAP_PERCENT / 100)
        if referral_bonus > referral_bonus_cap:
            referral_bonus = referral_bonus_cap
        user_dto.top_up_amount += payment_dto.fiatAmount + referral_bonus

    @staticmethod
    async def process_referrer_bonus(payment_dto: ProcessingPaymentDTO,
                                     user_dto: UserDTO,
                                     session: AsyncSession):
        referrer_user_dto = await UserRepository.get_user_entity(user_dto.referred_by_user_id, session)
        referrer_bonus = 0
        referral_deposits_qty = await DepositRepository.get_deposits_qty_by_user_id(user_dto.id, session)
        if referral_deposits_qty <= config.REFERRER_BONUS_DEPOSIT_LIMIT:
            referrer_bonus = payment_dto.fiatAmount * (config.REFERRER_BONUS_PERCENT / 100)
        referrer_bonus_cap = await DepositRepository.get_sum(referrer_user_dto.id, session) * (
                config.REFERRER_BONUS_CAP_PERCENT / 100)
        if referrer_bonus > referrer_bonus_cap:
            referrer_bonus = referrer_bonus_cap
        referrer_user_dto.top_up_amount += referrer_bonus
        await UserRepository.update(referrer_user_dto, session)

    @staticmethod
    async def apply_referral_logic(payment_dto: ProcessingPaymentDTO,
                                   user_dto: UserDTO,
                                   session: AsyncSession) -> ReferralBonusDTO:
        await ReferralService.create_referral_code(user_dto, session)

        referral_bonus = 0
        referrer_bonus = 0
        referrer_user_dto = None
        if user_dto.referred_by_user_id is not None:
            referral_deposits_qty = await DepositRepository.get_deposits_qty_by_user_id(
                user_dto.id, session
            )

            raw_referral_bonus = 0
            raw_referrer_bonus = 0

            if referral_deposits_qty <= config.REFERRAL_BONUS_DEPOSIT_LIMIT:
                raw_referral_bonus = payment_dto.fiatAmount * (config.REFERRAL_BONUS_PERCENT / 100)

            if referral_deposits_qty <= config.REFERRER_BONUS_DEPOSIT_LIMIT:
                raw_referrer_bonus = payment_dto.fiatAmount * (config.REFERRER_BONUS_PERCENT / 100)

            referral_deposits_sum = await DepositRepository.get_sum(user_dto.id, session)

            total_bonus_cap = referral_deposits_sum * (config.TOTAL_BONUS_CAP_PERCENT / 100)

            referral_bonus = min(raw_referral_bonus, total_bonus_cap)
            remaining_cap = total_bonus_cap - referral_bonus
            referrer_bonus = min(raw_referrer_bonus, max(0, remaining_cap))

            if referrer_bonus > 0:
                referrer_user_dto = await UserRepository.get_user_entity(user_dto.referred_by_user_id, session)
                referrer_user_dto.top_up_amount += referrer_bonus
                await UserRepository.update(referrer_user_dto, session)

        user_dto.top_up_amount += payment_dto.fiatAmount + referral_bonus
        await UserRepository.update(user_dto, session)
        referral_bonus_dto = ReferralBonusDTO(
            referral_user_id=user_dto.id,
            referral_user_dto=user_dto,
            referrer_user_id=referrer_user_dto.id,
            referrer_user_dto=referrer_user_dto,
            payment_amount=payment_dto.fiatAmount,
            applied_referral_bonus=referral_bonus,
            applied_referrer_bonus=referrer_bonus
        )
        return await ReferralRepository.create(referral_bonus_dto, session)
