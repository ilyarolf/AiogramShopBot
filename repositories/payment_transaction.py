from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute, session_flush
from models.payment_transaction import PaymentTransaction, PaymentTransactionDTO


class PaymentTransactionRepository:
    """Repository for PaymentTransaction database operations."""

    @staticmethod
    async def create(transaction_dto: PaymentTransactionDTO, session: Session | AsyncSession) -> int:
        """
        Creates a new PaymentTransaction and returns the ID.

        Args:
            transaction_dto: Payment transaction data
            session: Database session

        Returns:
            ID of created transaction
        """
        transaction = PaymentTransaction(**transaction_dto.model_dump(exclude_none=True))
        session.add(transaction)
        await session_flush(session)
        return transaction.id

    @staticmethod
    async def get_by_id(transaction_id: int, session: Session | AsyncSession) -> PaymentTransactionDTO | None:
        """
        Gets PaymentTransaction by ID.

        Args:
            transaction_id: Transaction ID
            session: Database session

        Returns:
            PaymentTransactionDTO or None if not found
        """
        stmt = select(PaymentTransaction).where(PaymentTransaction.id == transaction_id)
        result = await session_execute(stmt, session)
        transaction = result.scalar_one_or_none()

        if transaction:
            return PaymentTransactionDTO.model_validate(transaction, from_attributes=True)
        return None

    @staticmethod
    async def get_by_order_id(order_id: int, session: Session | AsyncSession) -> list[PaymentTransactionDTO]:
        """
        Gets all PaymentTransactions for an order.

        Args:
            order_id: Order ID
            session: Database session

        Returns:
            List of PaymentTransactionDTO (may be empty)
        """
        stmt = select(PaymentTransaction).where(PaymentTransaction.order_id == order_id)
        result = await session_execute(stmt, session)
        transactions = result.scalars().all()

        return [PaymentTransactionDTO.model_validate(t, from_attributes=True) for t in transactions]

    @staticmethod
    async def get_by_invoice_id(invoice_id: int, session: Session | AsyncSession) -> list[PaymentTransactionDTO]:
        """
        Gets all PaymentTransactions for an invoice.

        Args:
            invoice_id: Invoice ID
            session: Database session

        Returns:
            List of PaymentTransactionDTO (may be empty)
        """
        stmt = select(PaymentTransaction).where(PaymentTransaction.invoice_id == invoice_id)
        result = await session_execute(stmt, session)
        transactions = result.scalars().all()

        return [PaymentTransactionDTO.model_validate(t, from_attributes=True) for t in transactions]

    @staticmethod
    async def get_by_payment_processing_id(
        processing_id: int,
        session: Session | AsyncSession
    ) -> PaymentTransactionDTO | None:
        """
        Gets PaymentTransaction by KryptoExpress payment processing ID.
        Useful for checking if a payment has already been processed.

        Args:
            processing_id: KryptoExpress payment ID
            session: Database session

        Returns:
            PaymentTransactionDTO or None if not found
        """
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.payment_processing_id == processing_id
        )
        result = await session_execute(stmt, session)
        transaction = result.scalar_one_or_none()

        if transaction:
            return PaymentTransactionDTO.model_validate(transaction, from_attributes=True)
        return None

    @staticmethod
    async def get_total_paid_for_order(order_id: int, session: Session | AsyncSession) -> float:
        """
        Calculates total fiat amount paid for an order across all transactions.

        Args:
            order_id: Order ID
            session: Database session

        Returns:
            Total fiat amount paid (0.0 if no transactions)
        """
        transactions = await PaymentTransactionRepository.get_by_order_id(order_id, session)
        return sum(t.fiat_amount for t in transactions)

    @staticmethod
    async def get_penalty_transactions(session: Session | AsyncSession) -> list[PaymentTransactionDTO]:
        """
        Gets all PaymentTransactions where a penalty was applied.
        Useful for admin statistics/analytics.

        Args:
            session: Database session

        Returns:
            List of PaymentTransactionDTO with penalties
        """
        stmt = select(PaymentTransaction).where(PaymentTransaction.penalty_applied == True)
        result = await session_execute(stmt, session)
        transactions = result.scalars().all()

        return [PaymentTransactionDTO.model_validate(t, from_attributes=True) for t in transactions]

    @staticmethod
    async def get_overpayment_transactions(session: Session | AsyncSession) -> list[PaymentTransactionDTO]:
        """
        Gets all PaymentTransactions marked as overpayments.
        Useful for admin statistics/analytics.

        Args:
            session: Database session

        Returns:
            List of PaymentTransactionDTO with overpayments
        """
        stmt = select(PaymentTransaction).where(PaymentTransaction.is_overpayment == True)
        result = await session_execute(stmt, session)
        transactions = result.scalars().all()

        return [PaymentTransactionDTO.model_validate(t, from_attributes=True) for t in transactions]
