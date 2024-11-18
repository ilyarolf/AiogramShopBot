from aiogram import types, Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from enums.user import UserResponse
from handlers.common.common import add_pagination_buttons
from handlers.user.cart import create_message_with_bought_items
from enums.cryptocurrency import Cryptocurrency
from models.user import UserDTO
from services.buy import BuyService
from services.buyItem import BuyItemService
from services.item import ItemService
from services.user import UserService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator, BotEntity
from utils.tags_remover import HTMLTagsRemover

my_profile_router = Router()


class MyProfileCallback(CallbackData, prefix="my_profile"):
    level: int
    action: str
    args_for_action: int | str
    page: int


def create_callback_profile(level: int, action: str = "", args_for_action="", page=0):
    return MyProfileCallback(level=level, action=action, args_for_action=args_for_action, page=page).pack()


@my_profile_router.message(F.text == Localizator.get_text(BotEntity.USER, "my_profile"), IsUserExistFilter())
async def my_profile_text_message(message: types.message):
    await my_profile(message)


class MyProfileConstants:
    back_to_main_menu = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "back_to_my_profile"),
        callback_data=create_callback_profile(level=0))


async def get_my_profile_message(user_dto: UserDTO):
    user = await UserService.get(user_dto)
    fiat_balance = round(user.top_up_amount - user.consume_records, 2)
    return Localizator.get_text(BotEntity.USER, "my_profile_msg").format(telegram_id=user.telegram_id,
                                                                         btc_balance=user.btc_balance,
                                                                         ltc_balance=user.ltc_balance,
                                                                         sol_balance=user.sol_balance,
                                                                         usdt_trc20_balance=user.usdt_trc20_balance,
                                                                         usdt_erc20_balance=user.usdt_erc20_balance,
                                                                         usdc_erc20_balance=user.usdc_erc20_balance,
                                                                         fiat_balance=fiat_balance,
                                                                         currency_text=Localizator.get_currency_text(),
                                                                         currency_sym=Localizator.get_currency_symbol())


async def my_profile(message: Message | CallbackQuery):
    current_level = 0
    top_up_button = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "top_up_balance_button"),
        callback_data=create_callback_profile(current_level + 1, "top_up"))
    purchase_history_button = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.USER, "purchase_history_button"),
        callback_data=create_callback_profile(current_level + 4,
                                              "purchase_history"))
    my_profile_builder = InlineKeyboardBuilder()
    my_profile_builder.add(top_up_button, purchase_history_button)
    my_profile_builder.adjust(2)
    my_profile_markup = my_profile_builder.as_markup()
    user_dto = UserDTO(telegram_id=message.from_user.id)
    if isinstance(message, Message):
        message_text = await get_my_profile_message(user_dto)
        await message.answer(message_text, reply_markup=my_profile_markup)
    elif isinstance(message, CallbackQuery):
        callback = message
        message = await get_my_profile_message(user_dto)
        raw_message_text = HTMLTagsRemover.remove_html_tags(message)
        if raw_message_text != callback.message.text:
            await callback.message.edit_text(message, reply_markup=my_profile_markup)
        else:
            await callback.answer()


async def top_up_balance(callback: CallbackQuery):
    current_level = 1
    back_to_profile_button = types.InlineKeyboardButton(
        text=Localizator.get_text(BotEntity.COMMON, "back_button"),
        callback_data=create_callback_profile(current_level - 1))
    top_up_methods_builder = InlineKeyboardBuilder()
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action=Cryptocurrency.BTC.value))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action=Cryptocurrency.LTC.value))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action=Cryptocurrency.SOL.value))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.USER, "usdt_trc20_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action=Cryptocurrency.USDT_TRC20.value))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.USER, "usdt_erc20_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action=Cryptocurrency.USDT_ERC20.value))
    top_up_methods_builder.button(text=Localizator.get_text(BotEntity.USER, "usdc_erc20_top_up"),
                                  callback_data=create_callback_profile(current_level + 1,
                                                                        args_for_action=Cryptocurrency.USDC_ERC20.value))
    top_up_methods_builder.row(back_to_profile_button)
    top_up_methods_builder.adjust(1)
    await callback.message.edit_text(
        text=Localizator.get_text(BotEntity.USER, "choose_top_up_method"),
        reply_markup=top_up_methods_builder.as_markup())
    await callback.answer()


async def create_purchase_history_keyboard_builder(page: int, user_id: int):
    # TODO (refactoring)
    orders_markup_builder = InlineKeyboardBuilder()
    orders = await BuyService.get_buys_by_buyer_id(user_id, page)
    for order in orders:
        quantity = order.quantity
        total_price = order.total_price
        buy_id = order.id
        buy_item = await BuyItemService.get_buy_item_by_buy_id(buy_id)
        item = await ItemService.get_by_primary_key(buy_item.item_id)
        item_from_history_callback = create_callback_profile(5, action="get_order",
                                                             args_for_action=str(buy_id))
        orders_markup_builder.button(
            text=Localizator.get_text(BotEntity.USER, "purchase_history_item").format(
                subcategory_name=item.subcategory.name,
                total_price=total_price,
                quantity=quantity,
                currency_sym=Localizator.get_currency_symbol()),
            callback_data=item_from_history_callback)
    orders_markup_builder.adjust(1)
    return orders_markup_builder, len(orders)


async def purchase_history(callback: CallbackQuery):
    unpacked_callback = MyProfileCallback.unpack(callback.data)
    user = await UserService.get(UserDTO(telegram_id=callback.from_user.id))
    orders_markup_builder, orders_num = await create_purchase_history_keyboard_builder(unpacked_callback.page, user.id)
    orders_markup_builder = await add_pagination_buttons(orders_markup_builder, callback.data,
                                                         BuyService.get_max_page_purchase_history(user.id),
                                                         MyProfileCallback.unpack, MyProfileConstants.back_to_main_menu)
    if orders_num == 0:
        await callback.message.edit_text(Localizator.get_text(BotEntity.USER, "no_purchases"),
                                         reply_markup=orders_markup_builder.as_markup())
    else:
        await callback.message.edit_text(Localizator.get_text(BotEntity.USER, "purchases"),
                                         reply_markup=orders_markup_builder.as_markup())
    await callback.answer()


async def refresh_balance(callback: CallbackQuery):
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    cryptocurrency = Cryptocurrency(unpacked_cb.args_for_action)
    response = await UserService.refresh_balance(UserDTO(telegram_id=callback.from_user.id), cryptocurrency)
    match response:
        case UserResponse.BALANCE_REFRESHED:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_refreshed_successfully"),
                                  show_alert=True)
            await my_profile(callback)
        case UserResponse.BALANCE_NOT_REFRESHED:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_not_refreshed"),
                                  show_alert=True)
        case UserResponse.BALANCE_REFRESH_COOLDOWN:
            await callback.answer(Localizator.get_text(BotEntity.USER, "balance_refresh_timeout"), show_alert=True)


async def get_order_from_history(callback: CallbackQuery):
    current_level = 5
    buy_id = MyProfileCallback.unpack(callback.data).args_for_action
    items = await ItemService.get_items_by_buy_id(buy_id)
    message = await create_message_with_bought_items(items)
    back_builder = InlineKeyboardBuilder()
    back_builder.button(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                        callback_data=create_callback_profile(level=current_level - 1))
    await callback.message.edit_text(text=message, reply_markup=back_builder.as_markup())


async def top_up_by_method(callback: CallbackQuery):
    unpacked_cb = MyProfileCallback.unpack(callback.data)
    current_level = unpacked_cb.level
    payment_method = Cryptocurrency(unpacked_cb.args_for_action)
    user = await UserService.get(UserDTO(telegram_id=callback.from_user.id))
    bot = await callback.bot.get_me()
    addr = getattr(user, payment_method.get_address_field())
    msg = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(
        bot_name=bot.first_name,
        crypto_name=payment_method.value.replace('_', ' '),
        addr=addr)
    refresh_balance_builder = InlineKeyboardBuilder()
    refresh_balance_builder.button(text=Localizator.get_text(BotEntity.USER, "refresh_balance_button"),
                                   callback_data=create_callback_profile(current_level + 1,
                                                                         args_for_action=payment_method.value))
    refresh_balance_builder.button(text=Localizator.get_text(BotEntity.COMMON, "back_button"),
                                   callback_data=create_callback_profile(
                                       level=current_level - 1))
    await callback.message.edit_text(text=msg, reply_markup=refresh_balance_builder.as_markup())


@my_profile_router.callback_query(MyProfileCallback.filter(), IsUserExistFilter())
async def navigate(callback: CallbackQuery, callback_data: MyProfileCallback):
    current_level = callback_data.level

    levels = {
        0: my_profile,
        1: top_up_balance,
        2: top_up_by_method,
        3: refresh_balance,
        4: purchase_history,
        5: get_order_from_history
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)
