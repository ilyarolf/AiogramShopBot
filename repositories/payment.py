import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.payment import Payment, DepositRecordDTO
from models.user import User, UserDTO


class PaymentRepository:
    @staticmethod
    async def get_user_by_payment_id(payment_id: int, session: AsyncSession | Session) -> UserDTO:
        stmt = (select(User)
                .join(Payment, Payment.user_id == User.id)
                .where(Payment.processing_payment_id == payment_id))
        user = await session_execute(stmt, session)
        return UserDTO.model_validate(user.scalar_one(), from_attributes=True)

    @staticmethod
    async def get_next_topup_reference(session: AsyncSession | Session) -> str:
        """
        Generates unique top-up reference in format: TOPUP-YYYY-XXXXXX
        Example: TOPUP-2025-AX7D8K

        6-character alphanumeric code (uppercase + digits, excluding confusing characters: 0, O, 1, I, l)
        """
        import random
        import string
        from datetime import datetime

        year = datetime.now().year

        # Alphanumeric characters without confusing ones: 0, O, 1, I, l
        chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'

        # Try max 10 times to generate unique code
        for _ in range(10):
            # Generate 6-character code
            code = ''.join(random.choices(chars, k=6))
            topup_ref = f"TOPUP-{year}-{code}"

            # Check if already exists
            stmt = select(Payment).where(Payment.topup_reference == topup_ref)
            result = await session_execute(stmt, session)
            if not result.scalar_one_or_none():
                return topup_ref

        # Fallback: use timestamp if collision occurs
        import time
        timestamp_code = f"{int(time.time()) % 1000000:06d}"
        return f"TOPUP-{year}-{timestamp_code}"

    @staticmethod
    async def create(payment_id: int, user_id: int, message_id: int, session: AsyncSession | Session):
        # Generate unique top-up reference
        topup_ref = await PaymentRepository.get_next_topup_reference(session)

        payment = Payment(
            processing_payment_id=payment_id,
            topup_reference=topup_ref,
            user_id=user_id,
            message_id=message_id,
            expire_datetime=datetime.datetime.now() + datetime.timedelta(hours=1),
            is_paid=False
        )
        session.add(payment)
        return topup_ref  # Return reference for display

    @staticmethod
    async def get_by_topup_reference(topup_reference: str,
                                     session: AsyncSession | Session) -> DepositRecordDTO:
        """Get payment by topup reference (e.g. TOPUP-2025-ABCDEF)"""
        stmt = (select(Payment)
                .where(Payment.topup_reference == topup_reference))
        payment = await session_execute(stmt, session)
        return DepositRecordDTO.model_validate(payment.scalar_one(), from_attributes=True)

    @staticmethod
    async def get_by_processing_payment_id(processing_payment_id: int,
                                           session: AsyncSession | Session) -> DepositRecordDTO:
        stmt = (select(Payment)
                .where(Payment.processing_payment_id == processing_payment_id))
        payment = await session_execute(stmt, session)
        return DepositRecordDTO.model_validate(payment.scalar_one(), from_attributes=True)

    @staticmethod
    async def get_unexpired_unpaid_payments(user_id: int, session: AsyncSession | Session):
        sub_stmt = (select(Payment)
                    .where(Payment.expire_datetime > datetime.datetime.now(),
                           Payment.user_id == user_id,
                           Payment.is_paid == False))
        stmt = select(func.count()).select_from(sub_stmt)
        count = await session_execute(stmt, session)
        return count.scalar_one()

    @staticmethod
    async def update(payment_dto: DepositRecordDTO, session: AsyncSession | Session):
        stmt = (update(Payment)
                .where(Payment.id == payment_dto.id)
                .values(**payment_dto.model_dump()))
        await session_execute(stmt, session)
