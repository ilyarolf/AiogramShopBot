from typing import Union
from aiogram import types, Router, F
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from crypto_api.CryptoApiManager import CryptoApiManager
from handlers.common.common import add_pagination_buttons
from handlers.user.all_categories import create_message_with_bought_items
from services.buy import BuyService
from services.buyItem import BuyItemService
from services.item import ItemService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator
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


@my_profile_router.message(F.text == Localizator.get_text_from_key("my_profile"), IsUserExistFilter())
async def my_profile_text_message(message: types.message):
    await my_profile(message)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(text=Localizator.get_text_from_key("back_to_my_profile"),
                                                   callback_data=create_callback_profile(level=0))


async def get_my_profile_message(telegram_id: int):
    user = await UserService.get_by_tgid(telegram_id)
    btc_balance = user.btc_balance
    usdt_trc20_balance = user.trx_account.usdt_balance
    usdd_trc20_balance = user.trx_account.usdd_balance
    usdt_erc20_balance = user.eth_account.usdt_balance
    usdc_erc20_balance = user.eth_account.usdc_balance
    ltc_balance = user.ltc_balance
    usd_balance = round(user.top_up_amount - user.consume_records, 2)
    return Localizator.get_text_from_key("my_profile_msg").format(telegram_id=telegram_id,
                                                                  btc_balance=btc_balance,
                                                                  usdt_trc20_balance=usdt_trc20_balance,
                                                                  usdd_trc20_balance=usdd_trc20_balance,
                                                                  usdt_erc20_balance=usdt_erc20_balance,
                                                                  usdc_erc20_balance=usdc_erc20_balance,
                                                                  ltc_balance=ltc_balance,
                                                                  usd_balance=usd_balance)


async def my_profile(message: Union[Message, CallbackQuery]):
    current_level = 0
    top_up_button = types.InlineKeyboardButton(text=Localizator.get_text_from_key("top_up_balance_button"),
                                               callback_data=create_callback_profile(current_level + 1, "top_up"))
    purchase_history_button = types.InlineKeyboardButton(text=Localizator.get_text_from_key("purchase_history_button"),
                                                         callback_data=create_callback_profile(current_level + 2,
                                                                                               "purchase_history"))
    update_balance = types.InlineKeyboardButton(text=Localizator.get_text_from_key("refresh_balance_button"),
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
    trx_address = user.trx_account.address
    eth_address = user.eth_account.address
    ltc_address = user.ltc_address
    back_to_profile_button = types.InlineKeyboardButton(text=Localizator.get_text_from_key("admin_back_button"),
                                                        callback_data=create_callback_profile(current_level - 1))
    back_button_builder = InlineKeyboardBuilder()
    back_button_builder.add(back_to_profile_button)
    back_button_markup = back_button_builder.as_markup()
    bot_entity = await callback.bot.get_me()
    await callback.message.edit_text(
        text=Localizator.get_text_from_key("top_up_balance_msg").format(bot_name=bot_entity.first_name,
                                                                        btc_address=btc_address,
                                                                        trx_address=trx_address,
                                                                        ltc_address=ltc_address,
                                                                        eth_address=eth_address),
        parse_mode=ParseMode.HTML,
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
            text=Localizator.get_text_from_key("purchase_history_item").format(subcategory_name=item.subcategory.name,
                                                                               total_price=total_price,
                                                                               quantity=quantity),
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
        await callback.message.edit_text(Localizator.get_text_from_key("no_purchases"),
                                         reply_markup=orders_markup_builder.as_markup(),
                                         parse_mode=ParseMode.HTML)
    else:
        await callback.message.edit_text(Localizator.get_text_from_key("purchases"), reply_markup=orders_markup_builder.as_markup(),
                                         parse_mode=ParseMode.HTML)
    await callback.answer()


async def refresh_balance(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    # if await UserService.can_refresh_balance(telegram_id):
    if True:
        await callback.answer(Localizator.get_text_from_key("balance_refreshing"))
        old_crypto_balances = await UserService.get_balances(telegram_id)
        await UserService.create_last_balance_refresh_data(telegram_id)
        user = await UserService.get_by_tgid(telegram_id)
        addresses = await UserService.get_addresses(telegram_id)
        new_crypto_balances = await CryptoApiManager(**addresses, user_id=user.id).get_top_ups()
        crypto_prices = await CryptoApiManager.get_crypto_prices()
        deposit_usd_amount = 0.0
        bot_obj = callback.bot
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
                                                  telegram_id, bot_obj)
        await my_profile(callback)
    else:
        await callback.answer(Localizator.get_text_from_key("balance_refresh_timeout"), show_alert=True)


async def get_order_from_history(callback: CallbackQuery):
    current_level = 4
    buy_id = MyProfileCallback.unpack(callback.data).args_for_action
    items = await ItemService.get_items_by_buy_id(buy_id)
    message = await create_message_with_bought_items(items)
    back_builder = InlineKeyboardBuilder()
    back_button = types.InlineKeyboardButton(text=Localizator.get_text_from_key("admin_back_button"),
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
