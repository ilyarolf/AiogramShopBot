from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import AdminMenuCallback, AnnouncementCallback, InventoryManagementCallback, \
    UserManagementCallback, StatisticsCallback, WalletCallback, MediaManagementCallback, CouponManagementCallback, \
    ShippingManagementCallback, MyProfileCallback, ReviewManagementCallback
from enums.bot_entity import BotEntity
from enums.keyboard_button import KeyboardButton as KB
from enums.language import Language
from enums.user_role import UserRole
from handlers.admin.announcement import announcement_router
from handlers.admin.buys_management import buys_management_router
from handlers.admin.coupon_management import coupons_management
from handlers.admin.inventory_management import inventory_management
from handlers.admin.media_management import media_management
from handlers.admin.shipping_management import shipping_management
from handlers.admin.statistics import statistics
from handlers.admin.user_management import user_management
from handlers.admin.wallet import wallet
from utils.custom_filters import AdminIdFilter
from utils.utils import get_text

admin_router = Router()
admin_router.include_routers(announcement_router,
                             inventory_management,
                             user_management,
                             statistics,
                             wallet,
                             media_management,
                             coupons_management,
                             shipping_management,
                             buys_management_router)


@admin_router.message(F.text.in_(KB.get_localized_set(KB.ADMIN_MENU)), AdminIdFilter())
async def admin_command_handler(message: Message, state: FSMContext, language: Language):
    await admin(message=message, state=state, language=language)


async def admin(**kwargs):
    message: Message | CallbackQuery = kwargs.get("message") or kwargs.get("callback")
    state: FSMContext = kwargs.get("state")
    language: Language = kwargs.get("language")
    await state.clear()
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "announcements"),
                      callback_data=AnnouncementCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "inventory_management"),
                      callback_data=InventoryManagementCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "user_management"),
                      callback_data=UserManagementCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "statistics"),
                      callback_data=StatisticsCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "crypto_withdraw"),
                      callback_data=WalletCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "media_management"),
                      callback_data=MediaManagementCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "coupons_management"),
                      callback_data=CouponManagementCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "shipping_management"),
                      callback_data=ShippingManagementCallback.create(level=0))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "buys_management"),
                      callback_data=MyProfileCallback.create(level=3,
                                                             user_role=UserRole.ADMIN))
    kb_builder.button(text=get_text(language, BotEntity.ADMIN, "reviews_management"),
                      callback_data=ReviewManagementCallback.create(level=5,
                                                                    user_role=UserRole.ADMIN))
    kb_builder.adjust(2)
    msg_text = get_text(language, BotEntity.ADMIN, "menu")
    if isinstance(message, Message):
        await message.answer(msg_text,
                             reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        if callback.message.caption:
            await callback.message.delete()
            await callback.message.answer(text=msg_text, reply_markup=kb_builder.as_markup())
        else:
            await callback.message.edit_text(msg_text, reply_markup=kb_builder.as_markup())


@admin_router.callback_query(AdminIdFilter(), AdminMenuCallback.filter())
async def admin_menu_navigation(callback: CallbackQuery,
                                state: FSMContext,
                                callback_data: AdminMenuCallback,
                                language: Language):
    current_level = callback_data.level

    levels = {
        0: admin
    }

    current_level_function = levels[current_level]

    kwargs = {
        "callback": callback,
        "state": state,
        "language": language
    }

    await current_level_function(**kwargs)
