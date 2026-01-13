import secrets
import string

from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from enums.language import Language
from models.payment import ProcessingPaymentDTO
from models.referral import ReferralBonusDTO
from models.user import UserDTO
from repositories.deposit import DepositRepository
from repositories.referral import ReferralRepository
from repositories.user import UserRepository
from utils.utils import get_text


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
            referrer_user_id=referrer_user_dto.id if referrer_user_dto else None,
            referrer_user_dto=referrer_user_dto,
            payment_amount=payment_dto.fiatAmount,
            applied_referral_bonus=referral_bonus,
            applied_referrer_bonus=referrer_bonus
        )
        if referrer_user_dto:
            referral_bonus_dto = await ReferralRepository.create(referral_bonus_dto, session)
        return referral_bonus_dto

    @staticmethod
    async def view_statistics(callback: CallbackQuery,
                              callback_data: MyProfileCallback,
                              session: AsyncSession,
                              language: Language):
        user_dto = await UserRepository.get_by_tgid(callback.from_user.id, session)
        deposits_sum = await DepositRepository.get_sum(user_dto.id, session)
        referrals_qty = await UserRepository.get_referrals_qty_by_referrer_id(user_dto.id, session)
        referral_bonus_sum = await ReferralRepository.get_bonus_sum_as_referral(user_dto.id, session)
        referrer_bonus_sum = await ReferralRepository.get_bonus_sum_as_referrer(user_dto.id, session)
        access_emoji = "🔒"
        referral_code_section = ""
        if deposits_sum >= config.MIN_REFERRER_TOTAL_DEPOSIT:
            access_emoji = "🔓"
            bot = await callback.bot.get_me()
            referral_code_section = get_text(language, BotEntity.USER, "referral_code_section").format(
                bot_username=bot.username,
                referral_code=user_dto.referral_code,
            )
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(callback_data.get_back_button(language, 0))
        msg = get_text(language, BotEntity.USER, "referral_statistics_message").format(
            user_total_deposits=deposits_sum,
            min_referrer_total_deposit=config.MIN_REFERRER_TOTAL_DEPOSIT,
            referral_access_status=access_emoji,
            referral_bonus_percent=config.REFERRAL_BONUS_PERCENT,
            referral_bonus_deposit_limit=config.REFERRAL_BONUS_DEPOSIT_LIMIT,
            referral_bonus_cap_percent=config.REFERRAL_BONUS_CAP_PERCENT,
            referrer_bonus_percent=config.REFERRER_BONUS_PERCENT,
            referrer_bonus_deposit_limit=config.REFERRER_BONUS_DEPOSIT_LIMIT,
            referrer_bonus_cap_percent=config.REFERRER_BONUS_CAP_PERCENT,
            total_bonus_cap_percent=config.TOTAL_BONUS_CAP_PERCENT,
            referrals_count=referrals_qty,
            referral_bonus_earned=referral_bonus_sum,
            referrer_bonus_earned=referrer_bonus_sum,
            currency_sym=config.CURRENCY.get_localized_symbol()
        )
        msg = "".join([msg, referral_code_section])
        return msg, kb_builder
