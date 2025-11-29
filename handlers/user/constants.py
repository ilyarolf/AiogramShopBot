from aiogram.fsm.state import StatesGroup, State


class UserStates(StatesGroup):
    filter = State()
