import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute
from models.payment import Payment, TablePaymentDTO
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
    async def create(payment_id: int, user_id: int, message_id: int, session: AsyncSession | Session):
        payment = Payment(
            processing_payment_id=payment_id,
            user_id=user_id,
            message_id=message_id,
            expire_datetime=datetime.datetime.now() + datetime.timedelta(hours=1),
            is_paid=False
        )
        session.add(payment)

    @staticmethod
    async def get_by_processing_payment_id(processing_payment_id: int,
                                           session: AsyncSession | Session) -> TablePaymentDTO:
        stmt = (select(Payment)
                .where(Payment.processing_payment_id == processing_payment_id))
        payment = await session_execute(stmt, session)
        return TablePaymentDTO.model_validate(payment.scalar_one(), from_attributes=True)

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
    async def update(payment_dto: TablePaymentDTO, session: AsyncSession | Session):
        stmt = (update(Payment)
                .where(Payment.id == payment_dto.id)
                .values(**payment_dto.model_dump()))
        await session_execute(stmt, session)
