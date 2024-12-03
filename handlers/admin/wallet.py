import inspect

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from callbacks import WalletCallback
from services.admin import AdminService
from utils.custom_filters import AdminIdFilter

wallet = Router()


async def wallet_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    msg, kb_builder = await AdminService.get_wallet_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def withdraw_crypto(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_withdraw_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@wallet.callback_query(AdminIdFilter(), WalletCallback.filter())
async def wallet_navigation(callback: CallbackQuery, state: FSMContext, callback_data: WalletCallback):
    current_level = callback_data.level

    levels = {
        0: wallet_menu,
        1: withdraw_crypto
    }

    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
