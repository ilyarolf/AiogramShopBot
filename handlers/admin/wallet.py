from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import WalletCallback
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from handlers.admin.constants import WalletStates
from services.wallet import WalletService
from utils.custom_filters import AdminIdFilter
from utils.utils import get_text

wallet = Router()


async def wallet_menu(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    msg, kb_builder = await WalletService.get_wallet_menu(language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def withdraw_crypto(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: WalletCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    if callback_data.cryptocurrency is None:
        msg, kb_builder = await WalletService.get_withdraw_menu(language)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())
    else:
        msg, kb_builder = await WalletService.request_crypto_address(callback_data, state, language)
        await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def withdraw_confirmation(**kwargs):
    callback: CallbackQuery = kwargs.get("callback")
    callback_data: WalletCallback = kwargs.get("callback_data")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    msg, kb_builder = await WalletService.withdraw_transaction(callback_data, state, language)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


@wallet.message(AdminIdFilter(), F.text, StateFilter(WalletStates.crypto_address))
async def receive_address(message: Message, state: FSMContext, language: Language):
    state_data = await state.get_data()
    cryptocurrency = Cryptocurrency(state_data['cryptocurrency'])
    is_address_valid = WalletService.validate_withdrawal_address(message.text, cryptocurrency)
    if is_address_valid:
        msg, kb_builder = await WalletService.calculate_withdrawal(message, state, language)
    else:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=get_text(language, BotEntity.COMMON, "cancel"),
                          callback_data=WalletCallback.create(0))
        msg = get_text(language, BotEntity.ADMIN, "address_not_valid")
    await message.answer(text=msg, reply_markup=kb_builder.as_markup())


@wallet.callback_query(AdminIdFilter(), WalletCallback.filter())
async def wallet_navigation(callback: CallbackQuery,
                            state: FSMContext,
                            callback_data: WalletCallback,
                            language: Language):
    current_level = callback_data.level

    levels = {
        0: wallet_menu,
        1: withdraw_crypto,
        2: withdraw_confirmation
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "callback_data": callback_data,
        "language": language
    }

    await current_level_function(**kwargs)
