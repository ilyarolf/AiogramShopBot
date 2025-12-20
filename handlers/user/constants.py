from aiogram.fsm.state import StatesGroup, State


class UserStates(StatesGroup):
    shipping_address = State()
    filter_items = State()
    filter_purchase_history = State()
    coupon = State()
