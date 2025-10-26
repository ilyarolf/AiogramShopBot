from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import OrderCallback
from enums.bot_entity import BotEntity
from handlers.user.shipping_states import ShippingAddressStates
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator

shipping_router = Router()


@shipping_router.message(ShippingAddressStates.waiting_for_address, IsUserExistFilter())
async def process_shipping_address_input(message: Message, state: FSMContext, session: AsyncSession | Session):
    """
    Process user's shipping address input (free-text).
    Shows confirmation screen with address preview.
    """
    address_text = message.text.strip()

    if not address_text or len(address_text) < 10:
        # Address too short - ask again
        await message.answer(
            Localizator.get_text(BotEntity.USER, "shipping_address_invalid")
        )
        return

    # Store address in FSM context
    await state.update_data(shipping_address=address_text)

    # Show confirmation screen
    message_text = Localizator.get_text(BotEntity.USER, "shipping_address_confirm").format(
        address=address_text
    )

    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "confirm"),
        callback_data=OrderCallback.create(level=1).pack()  # Level 1 = confirm address
    )
    kb_builder.button(
        text=Localizator.get_text(BotEntity.COMMON, "cancel"),
        callback_data=OrderCallback.create(level=2).pack()  # Level 2 = re-enter address
    )

    await message.answer(message_text, reply_markup=kb_builder.as_markup())
    await state.set_state(ShippingAddressStates.confirm_address)


# Note: Shipping address confirmation is handled in handlers/user/order.py Level 1
# which calls OrderService.confirm_shipping_address()
