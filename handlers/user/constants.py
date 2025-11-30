from aiogram.fsm.state import StatesGroup, State


class UserStates(StatesGroup):
    filter_items = State()
    filter_purchase_history = State()
