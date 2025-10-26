"""
Data Retention Cleanup Job

Automatically deletes old data according to retention policies:
- Orders, Invoices, PaymentTransactions: 30 days
- ReferralUsage: 365 days
- ReferralDiscount: After 90-day expiry

Runs daily to ensure GDPR compliance and minimize data storage.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import config
from db import get_db_session, session_commit
from models.order import Order
from models.invoice import Invoice
from models.payment_transaction import PaymentTransaction
from models.referral_usage import ReferralUsage
from models.referral_discount import ReferralDiscount
from sqlalchemy import select, delete


async def cleanup_old_orders():
    """
    Deletes orders older than DATA_RETENTION_DAYS.
    Cascade deletes: Invoice, PaymentTransaction (via relationships).
    """
    async with get_db_session() as session:
        cutoff_date = datetime.now() - timedelta(days=config.DATA_RETENTION_DAYS)

        # Get count for logging
        count_stmt = select(Order).where(Order.created_at < cutoff_date)
        result = await session.execute(count_stmt)
        orders_to_delete = result.scalars().all()
        count = len(orders_to_delete)

        if count == 0:
            logging.info(f"[Data Retention] No orders older than {config.DATA_RETENTION_DAYS} days")
            return

        # Delete orders (cascade will handle invoices and payment_transactions)
        delete_stmt = delete(Order).where(Order.created_at < cutoff_date)
        await session.execute(delete_stmt)
        await session_commit(session)

        logging.info(f"[Data Retention] ✅ Deleted {count} orders older than {config.DATA_RETENTION_DAYS} days")


async def cleanup_old_invoices_orphaned():
    """
    Safety cleanup: Delete orphaned invoices without orders.
    Should not happen due to cascade, but provides extra safety.
    """
    async with get_db_session() as session:
        cutoff_date = datetime.now() - timedelta(days=config.DATA_RETENTION_DAYS)

        # Find invoices without orders
        stmt = select(Invoice).where(
            Invoice.id.notin_(select(Order.id))
        ).where(Invoice.id < cutoff_date)  # Assuming id correlates with creation time

        result = await session.execute(stmt)
        orphaned = result.scalars().all()

        if len(orphaned) > 0:
            logging.warning(f"[Data Retention] Found {len(orphaned)} orphaned invoices - cleaning up")
            delete_stmt = delete(Invoice).where(Invoice.id.in_([i.id for i in orphaned]))
            await session.execute(delete_stmt)
            await session_commit(session)


async def cleanup_old_payment_transactions():
    """
    Deletes payment transactions older than DATA_RETENTION_DAYS.
    Should be handled by Order cascade, but provides explicit cleanup.
    """
    async with get_db_session() as session:
        cutoff_date = datetime.now() - timedelta(days=config.DATA_RETENTION_DAYS)

        count_stmt = select(PaymentTransaction).where(PaymentTransaction.received_at < cutoff_date)
        result = await session.execute(count_stmt)
        count = len(result.scalars().all())

        if count == 0:
            logging.info(f"[Data Retention] No payment transactions older than {config.DATA_RETENTION_DAYS} days")
            return

        delete_stmt = delete(PaymentTransaction).where(PaymentTransaction.received_at < cutoff_date)
        await session.execute(delete_stmt)
        await session_commit(session)

        logging.info(f"[Data Retention] ✅ Deleted {count} payment transactions older than {config.DATA_RETENTION_DAYS} days")


async def cleanup_old_referral_usages():
    """
    Deletes referral usage records older than REFERRAL_DATA_RETENTION_DAYS.
    Kept longer than orders for abuse pattern detection.
    """
    async with get_db_session() as session:
        cutoff_date = datetime.now() - timedelta(days=config.REFERRAL_DATA_RETENTION_DAYS)

        count_stmt = select(ReferralUsage).where(ReferralUsage.created_at < cutoff_date)
        result = await session.execute(count_stmt)
        count = len(result.scalars().all())

        if count == 0:
            logging.info(f"[Data Retention] No referral usages older than {config.REFERRAL_DATA_RETENTION_DAYS} days")
            return

        delete_stmt = delete(ReferralUsage).where(ReferralUsage.created_at < cutoff_date)
        await session.execute(delete_stmt)
        await session_commit(session)

        logging.info(f"[Data Retention] ✅ Deleted {count} referral usages older than {config.REFERRAL_DATA_RETENTION_DAYS} days")


async def cleanup_expired_referral_discounts():
    """
    Deletes referral discounts that have expired.
    Expiry is 90 days from creation (as per T&Cs).
    """
    async with get_db_session() as session:
        now = datetime.now()

        # Delete expired discounts
        count_stmt = select(ReferralDiscount).where(ReferralDiscount.expires_at < now)
        result = await session.execute(count_stmt)
        count = len(result.scalars().all())

        if count == 0:
            logging.info(f"[Data Retention] No expired referral discounts")
            return

        delete_stmt = delete(ReferralDiscount).where(ReferralDiscount.expires_at < now)
        await session.execute(delete_stmt)
        await session_commit(session)

        logging.info(f"[Data Retention] ✅ Deleted {count} expired referral discounts")


async def run_data_retention_cleanup():
    """
    Main cleanup routine - runs all cleanup tasks.
    Should be called daily via scheduler.
    """
    logging.info("=" * 80)
    logging.info("[Data Retention] Starting daily cleanup job")
    logging.info(f"[Data Retention] Order retention: {config.DATA_RETENTION_DAYS} days")
    logging.info(f"[Data Retention] Referral retention: {config.REFERRAL_DATA_RETENTION_DAYS} days")
    logging.info("=" * 80)

    try:
        # Run all cleanup tasks
        await cleanup_old_orders()
        await cleanup_old_invoices_orphaned()
        await cleanup_old_payment_transactions()
        await cleanup_old_referral_usages()
        await cleanup_expired_referral_discounts()

        logging.info("[Data Retention] ✅ Daily cleanup completed successfully")

    except Exception as e:
        logging.error(f"[Data Retention] ❌ Error during cleanup: {e}", exc_info=True)

    logging.info("=" * 80 + "\n")


async def start_data_retention_cleanup_job():
    """
    Background job that runs cleanup every 24 hours.
    Call this function at application startup.
    """
    while True:
        try:
            await run_data_retention_cleanup()
        except Exception as e:
            logging.error(f"[Data Retention] Unexpected error in cleanup job: {e}", exc_info=True)

        # Wait 24 hours before next cleanup
        await asyncio.sleep(86400)  # 24 hours = 86400 seconds


if __name__ == "__main__":
    # For manual testing: python -m jobs.data_retention_cleanup_job
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_data_retention_cleanup())
