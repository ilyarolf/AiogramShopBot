from datetime import datetime

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from callbacks import MyProfileCallback
from crypto_api.CryptoApiManager import CryptoApiManager
from enums.cryptocurrency import Cryptocurrency
from enums.user import UserResponse
from handlers.user.constants import UserConstants
from models.user import User, UserDTO
from repositories.buy import BuyRepository
from repositories.buyItem import BuyItemRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.notification import NotifcationService
from services.cart import CartService
from utils.localizator import Localizator, BotEntity


class UserService:
    #
    #     @staticmethod
    #     async def is_exist(telegram_id: int) -> bool:
    #         async with get_db_session() as session:
    #             stmt = select(User).where(User.telegram_id == telegram_id)
    #             is_exist = await session_execute(stmt, session)
    #             return is_exist.scalar() is not None
    #
    #     @staticmethod
    #     async def create(telegram_id: int, telegram_username: str) -> int:
    #         async with get_db_session() as session:
    #             crypto_addr_gen = CryptoAddressGenerator()
    #             crypto_addresses = crypto_addr_gen.get_addresses()
    #             new_user = User(
    #                 telegram_username=telegram_username,
    #                 telegram_id=telegram_id,
    #                 btc_address=crypto_addresses['btc'],
    #                 ltc_address=crypto_addresses['ltc'],
    #                 trx_address=crypto_addresses['trx'],
    #                 eth_address=crypto_addresses['eth'],
    #                 sol_address=crypto_addresses['sol'],
    #                 seed=crypto_addr_gen.mnemonic_str
    #             )
    #             session.add(new_user)
    #             await session_commit(session)
    #             await session_refresh(session, new_user)
    #             return new_user.id
    #
    #     @staticmethod
    #     async def update_username(telegram_id: int, telegram_username: str):
    #         async with get_db_session() as session:
    #             user_from_db = await UserService.get_by_tgid(telegram_id)
    #             if user_from_db and user_from_db.telegram_username != telegram_username:
    #                 stmt = update(User).where(User.telegram_id == telegram_id).values(telegram_username=telegram_username)
    #                 await session_execute(stmt, session)
    #                 await session_commit(session)
    #
    #     @staticmethod
    #     async def get_by_tgid(telegram_id: int) -> User:
    #         async with get_db_session() as session:
    #             stmt = select(User).where(User.telegram_id == telegram_id)
    #             user_from_db = await session_execute(stmt, session)
    #             user_from_db = user_from_db.scalar()
    #             return user_from_db
    #
    #     @staticmethod
    #     async def can_refresh_balance(telegram_id: int) -> bool:
    #         async with get_db_session() as session:
    #             stmt = select(User.last_balance_refresh).where(User.telegram_id == telegram_id)
    #             user_last_refresh = await session_execute(stmt, session)
    #             user_last_refresh = user_last_refresh.scalar()
    #             if user_last_refresh is None:
    #                 return True
    #             now_time = datetime.datetime.now()
    #             timedelta = (now_time - user_last_refresh).total_seconds()
    #             return timedelta > 30
    #
    #     @staticmethod
    #     async def create_last_balance_refresh_data(telegram_id: int):
    #         async with get_db_session() as session:
    #             time = datetime.datetime.now()
    #             stmt = update(User).where(User.telegram_id == telegram_id).values(
    #                 last_balance_refresh=time)
    #             await session_execute(stmt, session)
    #             await session_commit(session)
    #
    #     @staticmethod
    #     async def get_balances(telegram_id: int) -> dict:
    #         async with get_db_session() as session:
    #             stmt = select(User).where(User.telegram_id == telegram_id)
    #             user_balances = await session_execute(stmt, session)
    #             user_balances = user_balances.scalar()
    #             user_balances = [user_balances.btc_balance, user_balances.ltc_balance,
    #                              user_balances.usdt_trc20_balance, user_balances.usdd_trc20_balance,
    #                              user_balances.usdt_erc20_balance, user_balances.usdc_erc20_balance]
    #             keys = ["btc_balance", "ltc_balance", "trc_20_usdt_balance", "trc_20_usdd_balance", "erc_20_usdt_balance",
    #                     "erc_20_usdc_balance"]
    #             user_balances = dict(zip(keys, user_balances))
    #             return user_balances
    #
    #     @staticmethod
    #     async def get_addresses(telegram_id: int) -> dict:
    #         async with get_db_session() as session:
    #             stmt = select(User).where(User.telegram_id == telegram_id)
    #             user_addresses = await session_execute(stmt, session)
    #             user_addresses = user_addresses.scalar()
    #             user_addresses = [user_addresses.btc_address, user_addresses.ltc_address,
    #                               user_addresses.trx_address, user_addresses.eth_address,
    #                               user_addresses.sol_address]
    #             keys = ["btc_address", "ltc_address", "trx_address", "eth_address", "sol_address"]
    #             user_addresses = dict(zip(keys, user_addresses))
    #             return user_addresses
    #
    #     @staticmethod
    #     async def update_crypto_balances(telegram_id: int, new_crypto_balances: dict):
    #         async with get_db_session() as session:
    #             stmt = select(User).where(User.telegram_id == telegram_id)
    #             result = await session_execute(stmt, session)
    #             user = result.scalar()
    #             balance_fields_map = {
    #                 "btc_deposit": "btc_balance",
    #                 "ltc_deposit": "ltc_balance",
    #                 "sol_deposit": "sol_balance",
    #                 "usdt_trc20_deposit": "usdt_trc20_balance",
    #                 "usdd_trc20_deposit": "usdd_trc20_balance",
    #                 "usdd_erc20_deposit": "usdd_erc20_balance",
    #                 "usdc_erc20_deposit": "usdc_erc20_balance",
    #             }
    #             update_values = {}
    #
    #             for key, value in new_crypto_balances.items():
    #                 if key in balance_fields_map:
    #                     field_name = balance_fields_map[key]
    #                     current_balance = getattr(user, field_name)
    #                     update_values[field_name] = current_balance + value
    #
    #             if update_values:
    #                 stmt = update(User).where(User.telegram_id == telegram_id).values(**update_values)
    #                 await session_execute(stmt, session)
    #                 await session_commit(session)
    #
    #     @staticmethod
    #     async def update_top_up_amount(telegram_id: int, deposit_amount: float):
    #         async with get_db_session() as session:
    #             stmt = select(User.top_up_amount).where(User.telegram_id == telegram_id)
    #             old_top_up_amount = await session_execute(stmt, session)
    #             old_top_up_amount = old_top_up_amount.scalar()
    #             stmt = update(User).where(User.telegram_id == telegram_id).values(
    #                 top_up_amount=round(old_top_up_amount + deposit_amount, 2))
    #             await session_execute(stmt, session)
    #             await session_commit(session)
    #
    #     @staticmethod
    #     async def is_buy_possible(telegram_id, total_price):
    #         user = await UserService.get_by_tgid(telegram_id)
    #         balance = user.top_up_amount - user.consume_records
    #         return balance >= total_price
    #
    #     @staticmethod
    #     async def update_consume_records(telegram_id: int, total_price: float):
    #         async with get_db_session() as session:
    #             get_old_consume_records_stmt = select(User.consume_records).where(User.telegram_id == telegram_id)
    #             old_consume_records = await session_execute(get_old_consume_records_stmt, session)
    #             old_consume_records = old_consume_records.scalar()
    #             stmt = update(User).where(User.telegram_id == telegram_id).values(
    #                 consume_records=old_consume_records + total_price)
    #             await session_execute(stmt, session)
    #             await session_commit(session)
    #
    #     @staticmethod
    #     async def get_users_tg_ids_for_sending():
    #         async with get_db_session() as session:
    #             stmt = select(User.telegram_id).where(User.can_receive_messages is True)
    #             user_ids = await session_execute(stmt, session)
    #             user_ids = user_ids.scalars().all()
    #             return user_ids
    #
    #     @staticmethod
    #     async def get_all_users_count():
    #         async with get_db_session() as session:
    #             stmt = func.count(User.id)
    #             users_count = await session_execute(stmt, session)
    #             return users_count.scalar()
    #
    #     @staticmethod
    #     async def reduce_consume_records(user_id: int, total_price):
    #         async with get_db_session() as session:
    #             stmt = select(User.consume_records).where(User.id == user_id)
    #             old_consume_records = await session_execute(stmt, session)
    #             old_consume_records = old_consume_records.scalar()
    #             stmt = update(User).where(User.id == user_id).values(consume_records=old_consume_records - total_price)
    #             await session_execute(stmt, session)
    #             await session_commit(session)
    #
    #     @staticmethod
    #     async def get_new_users_by_timedelta(timedelta_int, page):
    #         async with get_db_session() as session:
    #             current_time = datetime.datetime.now()
    #             one_day_interval = datetime.timedelta(days=int(timedelta_int))
    #             time_to_subtract = current_time - one_day_interval
    #             stmt = select(User).where(User.registered_at >= time_to_subtract, User.telegram_username is not None).limit(
    #                 config.PAGE_ENTRIES).offset(
    #                 page * config.PAGE_ENTRIES)
    #             count_stmt = select(func.count(User.id)).where(User.registered_at >= time_to_subtract)
    #             users = await session_execute(stmt, session)
    #             users_count = await session_execute(count_stmt, session)
    #             return users.scalars().all(), users_count.scalar_one()
    #
    #     @staticmethod
    #     async def get_max_page_for_users_by_timedelta(timedelta_int):
    #         async with get_db_session() as session:
    #             current_time = datetime.datetime.now()
    #             one_day_interval = datetime.timedelta(days=int(timedelta_int))
    #             time_to_subtract = current_time - one_day_interval
    #             stmt = select(func.count(User.id)).where(User.registered_at >= time_to_subtract,
    #                                                      User.telegram_username is not None)
    #             users = await session_execute(stmt, session)
    #             users = users.scalar_one()
    #             if users % config.PAGE_ENTRIES == 0:
    #                 return users / config.PAGE_ENTRIES - 1
    #             else:
    #                 return math.trunc(users / config.PAGE_ENTRIES)
    #
    #     @staticmethod
    #     async def update_receive_messages(telegram_id, new_value):
    #         async with get_db_session() as session:
    #             stmt = update(User).where(User.telegram_id == telegram_id).values(
    #                 can_receive_messages=new_value)
    #             await session_execute(stmt, session)
    #             await session_commit(session)
    #
    #     @staticmethod
    #     async def get_by_id(user_id: int) -> User:
    #         async with get_db_session() as session:
    #             stmt = select(User).where(User.id == user_id)
    #             user = await session_execute(stmt, session)
    #             return user.scalar()
    #
    #     @staticmethod
    #     async def get_user_entity(user_entity: str | int) -> User:
    #         async with get_db_session() as session:
    #             stmt = select(User).where(or_(User.telegram_id == user_entity, User.telegram_username == user_entity))
    #             user = await session_execute(stmt, session)
    #             return user.scalar()
    #
    #     @staticmethod
    #     async def balance_management(state_data: dict):
    #         operation = state_data['operation']
    #         user_entity = state_data['user_entity']
    #         balance_value = state_data['balance_value']
    #         user = await UserService.get_user_entity(user_entity)
    #         if user is None:
    #             return Localizator.get_text(BotEntity.ADMIN, "credit_management_user_not_found")
    #         elif operation == "plus":
    #             await UserService.update_top_up_amount(user.telegram_id, float(balance_value))
    #             return Localizator.get_text(BotEntity.ADMIN, "credit_management_added_success").format(
    #                 amount=balance_value,
    #                 telegram_id=user.telegram_id,
    #                 currency_text=Localizator.get_currency_text())
    #         elif operation == "minus":
    #             await UserService.update_consume_records(user.telegram_id, float(balance_value))
    #             return Localizator.get_text(BotEntity.ADMIN, "credit_management_reduced_success").format(
    #                 amount=balance_value,
    #                 telegram_id=user.telegram_id,
    #                 currency_text=Localizator.get_currency_text())

    @staticmethod
    async def create_if_not_exist(user_dto: UserDTO) -> None:
        user = await UserRepository.get_by_tgid(user_dto)
        match user:
            case None:
                user_id = await UserRepository.create(user_dto)
                await CartService.get_or_create_cart(user_id)
            case _:
                update_user_dto = UserDTO(**user.__dict__)
                update_user_dto.can_receive_messages = True
                update_user_dto.telegram_username = user_dto.telegram_username
                await UserRepository.update(update_user_dto)

    @staticmethod
    async def get(user_dto: UserDTO) -> User | None:
        return await UserRepository.get_by_tgid(user_dto)

    @staticmethod
    async def refresh_balance(user_dto: UserDTO, cryptocurrency: Cryptocurrency):
        user_dto = UserDTO.model_validate(await UserRepository.get_by_tgid(user_dto), from_attributes=True)
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
                await NotifcationService.new_deposit(deposits_amount, cryptocurrency, fiat_amount, user_dto)
                return UserResponse.BALANCE_REFRESHED
            else:
                return UserResponse.BALANCE_NOT_REFRESHED
        else:
            return UserResponse.BALANCE_REFRESH_COOLDOWN

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
    async def get_top_up_buttons(unpacked_cb: MyProfileCallback) -> tuple[str, InlineKeyboardBuilder]:
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
        kb_builder.row(UserConstants.get_back_button(unpacked_cb))
        msg_text = Localizator.get_text(BotEntity.USER, "choose_top_up_method")
        return msg_text, kb_builder

    @staticmethod
    async def get_purchase_history_buttons(unpacked_callback: MyProfileCallback, telegram_id: int) -> tuple[str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=telegram_id))
        buys = await BuyRepository.get_by_buyer_id(user.id, unpacked_callback.page)
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
                    unpacked_callback.level + 1,
                    args_for_action=buy.id
                ))
        if len(kb_builder.as_markup().inline_keyboard) == 0:
            return Localizator.get_text(BotEntity.USER, "no_purchases"), kb_builder
        else:
            return Localizator.get_text(BotEntity.USER, "purchases"), kb_builder
