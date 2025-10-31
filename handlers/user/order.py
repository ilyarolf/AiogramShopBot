from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import OrderCallback
from services.order import OrderService
from utils.custom_filters import IsUserExistFilter

order_router = Router()


async def create_order(**kwargs):
    """
    Level 0: Create Order from Cart

    - Stock check & adjustment
    - User confirmation of adjustments
    - Address collection (if physical items)
    - Transition to PENDING_PAYMENT
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.create_order_from_cart(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def confirm_shipping_address(**kwargs):
    """
    Level 1: Confirm Shipping Address

    - Save encrypted address
    - Update status: PENDING_PAYMENT_AND_ADDRESS → PENDING_PAYMENT
    - Hand off to PaymentService
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.confirm_shipping_address(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def reenter_shipping_address(**kwargs):
    """
    Level 2: Re-enter Shipping Address

    - User clicked cancel on address confirmation
    - Prompts for address input again with cancel button
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.reenter_shipping_address(callback, session, state)
    await callback.message.edit_reply_markup()
    await callback.message.answer(msg, reply_markup=kb_builder.as_markup())


async def process_payment(**kwargs):
    """
    Level 3: Process Payment

    - Hand off to PaymentService
    - PaymentService handles wallet check, crypto selection, invoice creation
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.process_payment(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def cancel_order(**kwargs):
    """
    Level 4: Show Cancel Confirmation

    - Show confirmation dialog
    - Check grace period
    - Warn about penalties if applicable
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.cancel_order_handler(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def execute_cancel_order(**kwargs):
    """
    Level 5: Execute Order Cancellation

    - Cancel pending order after confirmation
    - Restore stock
    - Clear cart
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.execute_cancel_order(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def reshow_stock_adjustment(**kwargs):
    """
    Level 6: Re-show Stock Adjustment

    - Back navigation from cancel dialog
    - Display stock adjustment screen again
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.reshow_stock_adjustment(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def confirm_adjusted_order(**kwargs):
    """
    Level 9: Confirm Adjusted Order

    - User confirms order with stock adjustments
    - Continue to address collection or payment
    """
    callback = kwargs.get("callback")
    session = kwargs.get("session")
    state = kwargs.get("state")

    msg, kb_builder = await OrderService.confirm_adjusted_order(callback, session, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@order_router.callback_query(OrderCallback.filter(), IsUserExistFilter())
async def navigate_order_process(
    callback: CallbackQuery,
    callback_data: OrderCallback,
    session: AsyncSession | Session,
    state: FSMContext
):
    """
    Order process router.
    Routes callbacks to appropriate level handlers.
    """
    current_level = callback_data.level

    levels = {
        0: create_order,                    # Create order from cart
        1: confirm_shipping_address,        # Confirm shipping address
        2: reenter_shipping_address,        # Re-enter address
        3: process_payment,                 # Process payment
        4: cancel_order,                    # Show cancel confirmation
        5: execute_cancel_order,            # Execute cancellation
        6: reshow_stock_adjustment,         # Re-show stock adjustment
        9: confirm_adjusted_order,          # Confirm adjusted order
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "session": session,
        "state": state,
    }

    await current_level_function(**kwargs)
