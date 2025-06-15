from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import WalletCallback
from enums.bot_entity import BotEntity
from handlers.admin.constants import WalletStates
from services.admin import AdminService
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator

wallet = Router()


async def wallet_menu(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    await state.clear()
    msg, kb_builder = await AdminService.get_wallet_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def withdraw_crypto(**kwargs):
    callback = kwargs.get("callback")
    state = kwargs.get("state")
    unpacked_cb = WalletCallback.unpack(callback.data)
    if unpacked_cb.cryptocurrency is None:
        msg, kb_builder = await AdminService.get_withdraw_menu()
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    else:
        msg, kb_builder = await AdminService.request_crypto_address(callback, state)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def withdraw_confirmation(callback: CallbackQuery, state: FSMContext):
    msg, kb_builder = await AdminService.withdraw_transaction(callback, state)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@wallet.message(AdminIdFilter(), F.text, StateFilter(WalletStates.crypto_address))
async def receive_address(message: Message, state: FSMContext):
    is_address_valid = await AdminService.validate_withdrawal_address(message, state)
    if is_address_valid:
        msg, kb_builder = await AdminService.calculate_withdrawal(message, state)
    else:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=WalletCallback.create(0))
        msg = Localizator.get_text(BotEntity.ADMIN, "address_not_valid")
    await message.answer(text=msg, reply_markup=kb_builder.as_markup())


@wallet.callback_query(AdminIdFilter(), WalletCallback.filter())
async def wallet_navigation(callback: CallbackQuery, state: FSMContext, callback_data: WalletCallback):
    current_level = callback_data.level

    levels = {
        0: wallet_menu,
        1: withdraw_crypto,
        2: withdraw_confirmation
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state
    }

    await current_level_function(**kwargs)
