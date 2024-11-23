from aiogram import types, F, Router
from aiogram.types import CallbackQuery, Message

from callbacks import CartCallback
from services.cart import CartService
from utils.custom_filters import IsUserExistFilter
from utils.localizator import Localizator, BotEntity

cart_router = Router()


@cart_router.message(F.text == Localizator.get_text(BotEntity.USER, "cart"), IsUserExistFilter())
async def cart_text_message(message: types.message):
    await show_cart(message)


async def show_cart(message: Message | CallbackQuery):
    msg, kb_builder = await CartService.create_buttons(message)
    if isinstance(message, Message):
        await message.answer(msg, reply_markup=kb_builder.as_markup())
    elif isinstance(message, CallbackQuery):
        callback = message
        await callback.message.edit_text(msg, reply_markup=kb_builder.as_markup())


async def delete_cart_item(callback: CallbackQuery):
    msg, kb_builder = await CartService.delete_cart_item(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


#
#
# async def create_cart_content_string(cart_items: List[CartItem]) -> str:
#     cart_line_items_total = "<b>\n\n"
#     cart_grand_total = 0.0
#
#     for cart_item in cart_items:
#         price = await ItemService.get_price_by_subcategory(cart_item.subcategory_id, cart_item.category_id)
#         subcategory = await SubcategoryService.get_by_primary_key(cart_item.subcategory_id)
#         line_item_total = price * cart_item.quantity
#         cart_line_item = Localizator.get_text(BotEntity.USER, "cart_item_button").format(
#             subcategory_name=subcategory.name, qty=cart_item.quantity,
#             total_price=line_item_total, currency_sym=Localizator.get_currency_symbol()
#         )
#         cart_grand_total += line_item_total
#         cart_line_items_total += cart_line_item
#     cart_line_items_total += Localizator.get_text(BotEntity.USER, "cart_grand_total_string").format(
#         cart_grand_total=cart_grand_total, currency_sym=Localizator.get_currency_symbol())
#     cart_line_items_total += "</b>"
#     return cart_line_items_total
#
#
# def get_checkout_buttons_inline_builder(callback):
#     unpacked_cart_callback = CartCallback.unpack(callback.data)
#     cart_checkout_inline_keyboard_builder = InlineKeyboardBuilder()
#     confirmation_checkout_callback = create_cart_callback(level=3, purchase_confirmation=True)
#     confirmation_button_checkout = types.InlineKeyboardButton(
#         text=Localizator.get_text(BotEntity.COMMON, "confirm"),
#         callback_data=confirmation_checkout_callback)
#     decline_checkout_callback = create_cart_callback(level=unpacked_cart_callback.level - 2)
#     decline_button_checkout = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.COMMON, "decline"),
#                                                          callback_data=decline_checkout_callback)
#     cart_checkout_inline_keyboard_builder.add(confirmation_button_checkout)
#     cart_checkout_inline_keyboard_builder.add(decline_button_checkout)
#     cart_checkout_inline_keyboard_builder.adjust(2)
#
#     return cart_checkout_inline_keyboard_builder
#
#
async def checkout_processing(callback: CallbackQuery):
    msg, kb_builder = await CartService.checkout_processing(callback)
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def buy_processing(callback: CallbackQuery):
    await callback.message.edit_reply_markup()
    msg, kb_builder = await CartService.buy_processing(callback)
#     unpacked_callback = CartCallback.unpack(callback.data)
#     purchase_confirmation = unpacked_callback.purchase_confirmation
#     telegram_id = callback.from_user.id
#     user = await UserService.get_by_tgid(telegram_id)
#     cart = await CartService.get_cart_by_user_id(user.id)
#     cart_items = await CartItemService.get_all_cart_items_by_cart_id(cart.id)
#
#     is_in_stock = False
#     out_of_stock_items = []
#     cart_grand_total = 0.0
#
#     for cart_item in cart_items:
#         price = await ItemService.get_price_by_subcategory(cart_item.subcategory_id, cart_item.category_id)
#         subcategory_id = cart_item.subcategory_id
#         category_id = cart_item.category_id
#         quantity = cart_item.quantity
#         cart_grand_total += price * quantity
#
#         is_in_stock = await ItemService.get_available_quantity(subcategory_id, category_id) >= quantity
#         if is_in_stock is False:
#             out_of_stock_items.append(cart_item)
#
#     is_enough_money = await UserService.is_buy_possible(telegram_id, cart_grand_total)
#     back_to_main_builder = InlineKeyboardBuilder()
#     back_to_main_callback = create_callback_all_categories(level=0)
#     back_to_main_button = types.InlineKeyboardButton(text=Localizator.get_text(BotEntity.USER, "all_categories"),
#                                                      callback_data=back_to_main_callback)
#     back_to_main_builder.add(back_to_main_button)
#
#     bot = callback.bot
#     if purchase_confirmation and is_in_stock and is_enough_money:
#         user = await UserService.get_by_tgid(telegram_id)
#         await UserService.update_consume_records(telegram_id, cart_grand_total)
#         message_total = ""
#         sold_cart_items = []
#
#         for cart_item in cart_items:
#             price = await ItemService.get_price_by_subcategory(cart_item.subcategory_id, cart_item.category_id)
#             sold_items = await ItemService.get_bought_items(cart_item.category_id, cart_item.subcategory_id,
#                                                             cart_item.quantity)
#             message_total += await create_message_with_bought_items(sold_items) + "\n"
#             cart_item_total = cart_item.quantity * price
#             new_buy_id = await BuyService.insert_new(user, cart_item.quantity, cart_item_total)
#             await BuyItemService.insert_many(sold_items, new_buy_id)
#             await ItemService.set_items_sold(sold_items)
#             await CartItemService.remove_from_cart(cart_item_id=cart_item.id)
#             sold_cart_items.append(cart_item)
#
#         await NotificationManager.new_buy(sold_cart_items, user, bot)
#         await callback.message.edit_text(text=message_total)
#
#     elif purchase_confirmation is False:
#         await callback.message.edit_text(text=Localizator.get_text(BotEntity.USER, "purchase_confirmation_declined"),
#                                          parse_mode=ParseMode.HTML,
#                                          reply_markup=back_to_main_builder.as_markup())
#     elif is_enough_money is False:
#         await callback.message.edit_text(text=Localizator.get_text(BotEntity.USER, "insufficient_funds"),
#                                          parse_mode=ParseMode.HTML,
#                                          reply_markup=back_to_main_builder.as_markup())
#     elif is_in_stock is False:
#         out_of_stock_message = Localizator.get_text(BotEntity.USER, "out_of_stock")
#
#         for cart_item in out_of_stock_items:
#             subcategory = await SubcategoryService.get_by_primary_key(cart_item.subcategory_id)
#             out_of_stock_message += subcategory.name + "\n"
#
#         await callback.message.edit_text(out_of_stock_message, reply_markup=back_to_main_builder.as_markup())


async def create_message_with_bought_items(bought_data: list):
    message = "<b>"
    for count, item in enumerate(bought_data, start=1):
        private_data = item.private_data
        message += Localizator.get_text(BotEntity.USER, "purchased_item").format(count=count,
                                                                                 private_data=private_data)
    message += "</b>"
    return message


@cart_router.callback_query(CartCallback.filter(), IsUserExistFilter())
async def navigate_cart_process(callback: CallbackQuery, callback_data: CartCallback):
    current_level = callback_data.level

    levels = {
        0: show_cart,
        1: delete_cart_item,
        2: checkout_processing,
        # 3: buy_processing,
    }

    current_level_function = levels[current_level]

    await current_level_function(callback)
