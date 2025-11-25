from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import AdminMenuCallback, AnnouncementCallback, InventoryManagementCallback, \
    UserManagementCallback, StatisticsCallback, WalletCallback, MediaManagementCallback
from enums.bot_entity import BotEntity
from handlers.admin.announcement import announcement_router
from handlers.admin.inventory_management import inventory_management
from handlers.admin.media_management import media_management
from handlers.admin.statistics import statistics
from handlers.admin.user_management import user_management
from handlers.admin.wallet import wallet
from utils.custom_filters import AdminIdFilter
from utils.localizator import Localizator

admin_router = Router()
admin_router.include_routers(announcement_router,
                             inventory_management,
                             user_management,
                             statistics,
                             wallet,
                             media_management)


@admin_router.message(F.text == Localizator.get_text(BotEntity.ADMIN, "menu"), AdminIdFilter())
async def admin_command_handler(message: Message):
    await admin(message=message)


async def admin(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "announcements"),
                      callback_data=AnnouncementCallback.create(level=0))
    kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "inventory_management"),
                      callback_data=InventoryManagementCallback.create(level=0))
    kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "user_management"),
                      callback_data=UserManagementCallback.create(level=0))
    kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "statistics"),
                      callback_data=StatisticsCallback.create(level=0))
    kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "crypto_withdraw"),
                      callback_data=WalletCallback.create(level=0))
    kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "media_management"),
                      callback_data=MediaManagementCallback.create(level=0))
    kb_builder.adjust(2)
    if isinstance(message, Message):
        await message.answer(Localizator.get_text(BotEntity.ADMIN, "menu"),
                             reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "menu"),
                                         reply_markup=kb_builder.as_markup())


@admin_router.callback_query(AdminIdFilter(), AdminMenuCallback.filter())
async def admin_menu_navigation(callback: CallbackQuery, state: FSMContext, callback_data: AdminMenuCallback):
    current_level = callback_data.level

    levels = {
        0: admin
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
    }

    await current_level_function(**kwargs)
