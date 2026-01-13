from aiogram.fsm.state import StatesGroup, State


class UserStates(StatesGroup):
    review_image = State()
    review_text = State()
    shipping_address = State()
    filter_items = State()
    filter_purchase_history = State()
    coupon = State()
