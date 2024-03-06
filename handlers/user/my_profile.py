from typing import Union
from aiogram import types, Router, F
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot import bot
from crypto_api.CryptoApiManager import CryptoApiManager
from handlers.common.common import add_pagination_buttons
from handlers.user.all_categories import create_message_with_bought_items
from services.buy import BuyService
from services.buyItem import BuyItemService
from services.item import ItemService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.notification_manager import NotificationManager
from utils.tags_remover import HTMLTagsRemover

my_profile_router = Router()


class MyProfileCallback(CallbackData, prefix="my_profile"):
    level: int
    action: str
    args_for_action: Union[int, str]
    page: int


def create_callback_profile(level: int, action: str = "", args_for_action="", page=0):
    return MyProfileCallback(level=level, action=action, args_for_action=args_for_action, page=page).pack()


@my_profile_router.message(F.text == "🎓 My profile", IsUserExistFilter())
async def my_profile_text_message(message: types.message):
    await my_profile(message)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(text="⤵️Back my profile",
                                                   callback_data=create_callback_profile(level=0))


async def get_my_profile_message(telegram_id: int):
    user = await UserService.get_by_tgid(telegram_id)
    btc_balance = user.btc_balance
    usdt_balance = user.usdt_balance
    ltc_balance = user.ltc_balance
    usd_balance = round(user.top_up_amount - user.consume_records, 2)
    return (f'<b>Your profile\nID:</b> <code>{telegram_id}</code>\n\n'
            f'<b>Your BTC balance:</b>\n<code>{btc_balance}</code>\n'
            f'<b>Your USDT balance:</b>\n<code>{usdt_balance}</code>\n'
            f'<b>Your LTC balance:</b>\n<code>{ltc_balance}</code>\n'
            f"<b>Your balance in USD:</b>\n{usd_balance}$")


async def my_profile(message: Union[Message, CallbackQuery]):
    current_level = 0
    top_up_button = types.InlineKeyboardButton(text='Top Up balance',
                                               callback_data=create_callback_profile(current_level + 1, "top_up"))
    purchase_history_button = types.InlineKeyboardButton(text='Purchase history',
                                                         callback_data=create_callback_profile(current_level + 2,
                                                                                               "purchase_history"))
    update_balance = types.InlineKeyboardButton(text='Refresh balance',
                                                callback_data=create_callback_profile(current_level + 3,
                                                                                      "refresh_balance"))
    my_profile_builder = InlineKeyboardBuilder()
    my_profile_builder.add(top_up_button, purchase_history_button, update_balance)
    my_profile_builder.adjust(2)
    my_profile_markup = my_profile_builder.as_markup()

    if isinstance(message, Message):
        telegram_id = message.chat.id
        message_text = await get_my_profile_message(telegram_id)
        await message.answer(message_text, parse_mode=ParseMode.HTML, reply_markup=my_profile_markup)
    elif isinstance(message, CallbackQuery):
        callback = message
        telegram_id = callback.from_user.id
        message = await get_my_profile_message(telegram_id)
        raw_message_text = HTMLTagsRemover.remove_html_tags(message)
        if raw_message_text != callback.message.text:
            await callback.message.edit_text(message, parse_mode=ParseMode.HTML, reply_markup=my_profile_markup)
        else:
            await callback.answer()


async def top_up_balance(callback: CallbackQuery):
    telegram_id = callback.message.chat.id
    user = await UserService.get_by_tgid(telegram_id)
    current_level = 1
    btc_address = user.btc_address
    trx_address = user.trx_address
    ltc_address = user.ltc_address
    back_to_profile_button = types.InlineKeyboardButton(text='Back',
                                                        callback_data=create_callback_profile(current_level - 1))
    back_button_builder = InlineKeyboardBuilder()
    back_button_builder.add(back_to_profile_button)
    back_button_markup = back_button_builder.as_markup()
    bot_entity = await bot.get_me()
    await callback.message.edit_text(
        f'<b>Deposit to the address the amount you want to top up the {bot_entity.first_name}</b> \n\n'
        f'<b>Important</b>\n<i>A unique BTC/LTC/USDT addresses is given for each deposit\n'
        f'The top up takes place within 5 minutes after the transfer</i>\n\n'
        f'<b>Your BTC address\n</b><code>{btc_address}</code>\n'
        f'<b>Your USDT TRC-20 address\n</b><code>{trx_address}</code>\n'
        f'<b>Your LTC address</b>\n<code>{ltc_address}</code>\n', parse_mode=ParseMode.HTML,
        reply_markup=back_button_markup)
    await callback.answer()


async def create_purchase_history_keyboard_builder(page: int, user_id: int):
    orders_markup_builder = InlineKeyboardBuilder()
    orders = await BuyService.get_buys_by_buyer_id(user_id, page)
    for order in orders:
        quantity = order.quantity
        total_price = order.total_price
        buy_id = order.id
        buy_item = await BuyItemService.get_buy_item_by_buy_id(buy_id)
        item = await ItemService.get_by_primary_key(buy_item.item_id)
        item_from_history_callback = create_callback_profile(4, action="get_order",
                                                             args_for_action=str(buy_id))
        order_inline = types.InlineKeyboardButton(
            text=f"{item.subcategory.name} | Total Price: {total_price}$ | Quantity: {quantity} pcs",
            callback_data=item_from_history_callback
        )
        orders_markup_builder.add(order_inline)
    orders_markup_builder.adjust(1)
    return orders_markup_builder, len(orders)


async def purchase_history(callback: CallbackQuery):
    unpacked_callback = MyProfileCallback.unpack(callback.data)
    telegram_id = callback.message.chat.id
    user = await UserService.get_by_tgid(telegram_id)
    orders_markup_builder, orders_num = await create_purchase_history_keyboard_builder(unpacked_callback.page, user.id)
    orders_markup_builder = await add_pagination_buttons(orders_markup_builder, callback.data,
                                                         BuyService.get_max_page_purchase_history(user.id),
                                                         MyProfileCallback.unpack, MyProfileConstants.back_to_main_menu)
    if orders_num == 0:
        await callback.message.edit_text("<b>You haven't had any purchases yet</b>",
                                         reply_markup=orders_markup_builder.as_markup(),
                                         parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text('<b>Your purchases:</b>', reply_markup=orders_markup_builder.as_markup(),
                                         parse_mode=ParseMode.HTML)
    await callback.answer()


async def refresh_balance(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    if await UserService.can_refresh_balance(telegram_id):
        await callback.answer("Refreshing...")
        old_crypto_balances = await UserService.get_balances(telegram_id)
        await UserService.create_last_balance_refresh_data(telegram_id)
        addresses = await UserService.get_addresses(telegram_id)
        new_crypto_balances = await CryptoApiManager(**addresses).get_top_ups()
        crypto_prices = await CryptoApiManager.get_crypto_prices()
        deposit_usd_amount = 0.0
        if sum(new_crypto_balances.values()) > sum(old_crypto_balances.values()):
            merged_deposit = {key: new_crypto_balances[key] - old_crypto_balances[key] for key in
                              new_crypto_balances.keys()}
            for balance_key, balance in merged_deposit.items():
                balance_key = balance_key.split('_')[0]
                crypto_balance_in_usd = balance * crypto_prices[balance_key]
                deposit_usd_amount += crypto_balance_in_usd
            await UserService.update_crypto_balances(telegram_id, new_crypto_balances)
            await UserService.update_top_up_amount(telegram_id, deposit_usd_amount * 0.95)
            await NotificationManager.new_deposit(old_crypto_balances, new_crypto_balances, deposit_usd_amount,
                                                  telegram_id)
        await my_profile(callback)
    else:
        await callback.answer("Please wait and try again later", show_alert=True)


async def get_order_from_history(callback: CallbackQuery):
    current_level = 4
    buy_id = MyProfileCallback.unpack(callback.data).args_for_action
    items = await ItemService.get_items_by_buy_id(buy_id)
    message = await create_message_with_bought_items(items)
    back_builder = InlineKeyboardBuilder()
    back_button = types.InlineKeyboardButton(text="Back",
                                             callback_data=create_callback_profile(level=current_level - 2))
    back_builder.add(back_button)
    await callback.message.edit_text(text=message, parse_mode=ParseMode.HTML, reply_markup=back_builder.as_markup())


@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery, callback_data: MyProfileCallback):
    current_level = callback_data.level

    levels = {
        0: my_profile,
        1: top_up_balance,
        2: purchase_history,
        3: refresh_balance,
        4: get_order_from_history
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)
