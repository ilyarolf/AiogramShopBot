from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from db import session_execute, session_flush
from models.invoice import Invoice, InvoiceDTO


class InvoiceRepository:

    @staticmethod
    async def create(invoice_dto: InvoiceDTO, session: Session | AsyncSession) -> int:
        """Erstellt eine neue Invoice und gibt die ID zurück"""
        invoice = Invoice(**invoice_dto.model_dump(exclude_none=True))
        session.add(invoice)
        await session_flush(session)
        return invoice.id

    @staticmethod
    async def get_by_order_id(order_id: int, session: Session | AsyncSession) -> InvoiceDTO | None:
        """Holt Invoice einer Order"""
        stmt = select(Invoice).where(Invoice.order_id == order_id)
        result = await session_execute(stmt, session)
        invoice = result.scalar_one_or_none()

        if invoice:
            return InvoiceDTO.model_validate(invoice, from_attributes=True)
        return None

    @staticmethod
    async def get_by_payment_processing_id(processing_id: int, session: Session | AsyncSession) -> InvoiceDTO | None:
        """Holt Invoice via KryptoExpress Payment ID (für Webhook)"""
        stmt = select(Invoice).where(Invoice.payment_processing_id == processing_id)
        result = await session_execute(stmt, session)
        invoice = result.scalar_one_or_none()

        if invoice:
            return InvoiceDTO.model_validate(invoice, from_attributes=True)
        return None

    @staticmethod
    async def get_next_invoice_number(session: Session | AsyncSession) -> str:
        """Generiert nächste Invoice-Nummer (INV-2025-00001)"""
        from datetime import datetime

        year = datetime.now().year
        prefix = f"INV-{year}-"

        # Finde höchste Nummer für dieses Jahr
        stmt = (
            select(Invoice.invoice_number)
            .where(Invoice.invoice_number.like(f"{prefix}%"))
            .order_by(Invoice.invoice_number.desc())
            .limit(1)
        )
        result = await session_execute(stmt, session)
        last_invoice = result.scalar_one_or_none()

        if last_invoice:
            # Extrahiere Nummer: "INV-2025-00123" -> 123
            last_number = int(last_invoice.split('-')[-1])
            next_number = last_number + 1
        else:
            next_number = 1

        return f"{prefix}{next_number:05d}"