from aiogram.fsm.state import State, StatesGroup


class ShippingAddressStates(StatesGroup):
    """FSM states for shipping address collection"""
    waiting_for_address = State()
    confirm_address = State()
