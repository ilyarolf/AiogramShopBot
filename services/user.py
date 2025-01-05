from datetime import datetime
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import MyProfileCallback
from crypto_api.CryptoApiManager import CryptoApiManager
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.user import UserResponse
from handlers.common.common import add_pagination_buttons
from models.user import User, UserDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.cart import CartRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.notification import NotificationService
from utils.localizator import Localizator


class UserService:

    @staticmethod
    async def create_if_not_exist(user_dto: UserDTO) -> None:
        user = await UserRepository.get_by_tgid(user_dto)
        match user:
            case None:
                user_id = await UserRepository.create(user_dto)
                await CartRepository.get_or_create(user_id)
            case _:
                update_user_dto = UserDTO(**user.__dict__)
                update_user_dto.can_receive_messages = True
                update_user_dto.telegram_username = user_dto.telegram_username
                await UserRepository.update(update_user_dto)

    @staticmethod
    async def get(user_dto: UserDTO) -> User | None:
        return await UserRepository.get_by_tgid(user_dto)

    @staticmethod
    async def refresh_balance(callback: CallbackQuery) -> tuple[str, UserResponse]:
        user_dto = UserDTO.model_validate(await UserRepository.get_by_tgid(UserDTO(telegram_id=callback.from_user.id)),
                                          from_attributes=True)
        cryptocurrency = Cryptocurrency(MyProfileCallback.unpack(callback.data).args_for_action)
        now_time = datetime.now()
        if user_dto.last_balance_refresh is None or (
                user_dto.last_balance_refresh is not None and (
                now_time - user_dto.last_balance_refresh).total_seconds() > 30):
            user_dto.last_balance_refresh = now_time
            await UserRepository.update(user_dto)
            deposits_amount = await CryptoApiManager.get_new_deposits_amount(user_dto, cryptocurrency)
            if deposits_amount > 0:
                crypto_price = await CryptoApiManager.get_crypto_prices(cryptocurrency)
                fiat_amount = deposits_amount * crypto_price
                new_crypto_balance = getattr(user_dto, cryptocurrency.get_balance_field()) + deposits_amount
                setattr(user_dto, cryptocurrency.get_balance_field(), new_crypto_balance)
                user_dto.top_up_amount = user_dto.top_up_amount + fiat_amount
                await UserRepository.update(user_dto)
                await NotificationService.new_deposit(deposits_amount, cryptocurrency, fiat_amount, user_dto)
                return (Localizator.get_text(BotEntity.USER, "balance_refreshed_successfully"),
                        UserResponse.BALANCE_REFRESHED)
            else:
                return (Localizator.get_text(BotEntity.USER, "balance_not_refreshed"),
                        UserResponse.BALANCE_NOT_REFRESHED)
        else:
            return (Localizator.get_text(BotEntity.USER, "balance_refresh_timeout"),
                    UserResponse.BALANCE_REFRESH_COOLDOWN)

    @staticmethod
    async def get_my_profile_buttons(user_dto: UserDTO) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "top_up_balance_button"),
                          callback_data=MyProfileCallback.create(1, "top_up"))
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "purchase_history_button"),
                          callback_data=MyProfileCallback.create(4, "purchase_history"))
        user = await UserService.get(user_dto)
        fiat_balance = round(user.top_up_amount - user.consume_records, 2)
        message = (Localizator.get_text(BotEntity.USER, "my_profile_msg")
                   .format(telegram_id=user.telegram_id,
                           btc_balance=user.btc_balance,
                           ltc_balance=user.ltc_balance,
                           sol_balance=user.sol_balance,
                           usdt_trc20_balance=user.usdt_trc20_balance,
                           usdt_erc20_balance=user.usdt_erc20_balance,
                           usdc_erc20_balance=user.usdc_erc20_balance,
                           fiat_balance=fiat_balance,
                           currency_text=Localizator.get_currency_text(),
                           currency_sym=Localizator.get_currency_symbol()))
        return message, kb_builder

    @staticmethod
    async def get_top_up_buttons(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "btc_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.BTC.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "ltc_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.LTC.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "sol_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.SOL.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "usdt_trc20_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.USDT_TRC20.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "usdt_erc20_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.USDT_ERC20.value))
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "usdc_erc20_top_up"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=Cryptocurrency.USDC_ERC20.value))
        kb_builder.adjust(1)
        kb_builder.row(unpacked_cb.get_back_button())
        msg_text = Localizator.get_text(BotEntity.USER, "choose_top_up_method")
        return msg_text, kb_builder

    @staticmethod
    async def get_purchase_history_buttons(callback: CallbackQuery, telegram_id: int) \
            -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=telegram_id))
        buys = await BuyRepository.get_by_buyer_id(user.id, unpacked_cb.page)
        kb_builder = InlineKeyboardBuilder()
        for buy in buys:
            buy_item = await BuyItemRepository.get_single_by_buy_id(buy.id)
            item = await ItemRepository.get_by_id(buy_item.id)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id)
            kb_builder.button(text=Localizator.get_text(BotEntity.USER, "purchase_history_item").format(
                subcategory_name=subcategory.name,
                total_price=buy.total_price,
                quantity=buy.quantity,
                currency_sym=Localizator.get_currency_symbol()),
                callback_data=MyProfileCallback.create(
                    unpacked_cb.level + 1,
                    args_for_action=buy.id
                ))
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                  BuyRepository.get_max_page_purchase_history(user.id),
                                                  unpacked_cb.get_back_button(0))
        if len(kb_builder.as_markup().inline_keyboard) > 1:
            return Localizator.get_text(BotEntity.USER, "purchases"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "no_purchases"), kb_builder

    @staticmethod
    async def get_top_up_by_msg(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        payment_method = Cryptocurrency(unpacked_cb.args_for_action)
        user = await UserService.get(UserDTO(telegram_id=callback.from_user.id))
        addr = getattr(user, payment_method.get_address_field())
        bot = await callback.bot.get_me()
        msg = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(
            bot_name=bot.first_name,
            crypto_name=payment_method.value.replace('_', ' '),
            addr=addr)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.USER, "refresh_balance_button"),
                          callback_data=MyProfileCallback.create(unpacked_cb.level + 1,
                                                                 args_for_action=payment_method.value))
        kb_builder.row(unpacked_cb.get_back_button())
        return msg, kb_builder
