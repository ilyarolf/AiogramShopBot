import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db_session
from enums.order_status import OrderStatus
from repositories.item import ItemRepository
from repositories.order import OrderRepository


class PaymentTimeoutJob:
    """
    Background job that periodically checks for expired orders
    and releases their reserved stock.
    """

    def __init__(self, check_interval_seconds: int = 60):
        """
        Args:
            check_interval_seconds: How often to check for expired orders (default: 60s)
        """
        self.check_interval_seconds = check_interval_seconds
        self._task = None
        self._running = False

    async def start(self):
        """Starts the background job."""
        if self._running:
            logging.warning("PaymentTimeoutJob is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logging.info(f"PaymentTimeoutJob started (check interval: {self.check_interval_seconds}s)")

    async def stop(self):
        """Stops the background job gracefully."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logging.info("PaymentTimeoutJob stopped")

    async def _run_loop(self):
        """Main loop that runs the timeout check periodically."""
        while self._running:
            try:
                await self._check_expired_orders()
            except Exception as e:
                logging.error(f"Error in PaymentTimeoutJob: {e}", exc_info=True)

            # Wait for next check
            await asyncio.sleep(self.check_interval_seconds)

    async def _check_expired_orders(self):
        """
        Checks for expired orders and cancels them.
        Releases reserved stock back to available pool.
        """
        async with get_db_session() as session:
            # Get all pending orders that have expired
            expired_orders = await OrderRepository.get_expired_orders(session)

            if not expired_orders:
                return  # Nothing to do

            logging.info(f"Found {len(expired_orders)} expired orders to process")

            for order in expired_orders:
                try:
                    await self._cancel_expired_order(order.id, session)
                    logging.info(f"Cancelled expired order {order.id}")
                except Exception as e:
                    logging.error(f"Failed to cancel expired order {order.id}: {e}", exc_info=True)

            await session.commit()

    async def _cancel_expired_order(self, order_id: int, session: AsyncSession):
        """
        Cancels a single expired order and releases its stock.

        Args:
            order_id: Order ID to cancel
            session: DB session
        """
        # Release reserved items
        items = await ItemRepository.get_by_order_id(order_id, session)
        for item in items:
            item.order_id = None  # Remove reservation

        await ItemRepository.update(items, session)

        # Set order status to TIMEOUT
        await OrderRepository.update_status(order_id, OrderStatus.TIMEOUT, session)

        logging.debug(f"Order {order_id}: Released {len(items)} reserved items")