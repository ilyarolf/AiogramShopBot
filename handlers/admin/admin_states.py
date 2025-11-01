from aiogram.fsm.state import State, StatesGroup


class AdminOrderCancellationStates(StatesGroup):
    """FSM states for admin order cancellation with custom reason"""
    waiting_for_cancellation_reason = State()
