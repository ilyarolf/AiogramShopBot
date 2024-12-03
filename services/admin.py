import asyncio
import logging
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import AdminAnnouncementCallback, AnnouncementType, AdminInventoryManagementCallback, EntityType, \
    AddType, UserManagementCallback, UserManagementOperation, StatisticsCallback, StatisticsEntity, StatisticsTimeDelta, \
    WalletCallback
from crypto_api.CryptoApiManager import CryptoApiManager
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from handlers.admin.constants import AdminConstants, AdminInventoryManagementStates, UserManagementStates
from handlers.common.common import add_pagination_buttons
from repositories.buy import BuyRepository
from repositories.category import CategoryRepository
from repositories.deposit import DepositRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from utils.localizator import Localizator


class AdminService:

    @staticmethod
    async def get_announcement_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "send_everyone"),
                          callback_data=AdminAnnouncementCallback.create(1))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "restocking"),
                          callback_data=AdminAnnouncementCallback.create(2, AnnouncementType.RESTOCKING))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "stock"),
                          callback_data=AdminAnnouncementCallback.create(2, AnnouncementType.CURRENT_STOCK))
        kb_builder.row(AdminConstants.back_to_main_button)
        kb_builder.adjust(1)
        return Localizator.get_text(BotEntity.ADMIN, "announcements"), kb_builder

    @staticmethod
    async def send_announcement(callback: CallbackQuery):
        unpacked_cb = AdminAnnouncementCallback.unpack(callback.data)
        await callback.message.edit_reply_markup()
        active_users = await UserRepository.get_active()
        all_users_count = await UserRepository.get_all_count()
        counter = 0
        for user in active_users:
            try:
                await callback.message.copy_to(user.telegram_id, reply_markup=None)
                counter += 1
                await asyncio.sleep(1.5)
            except TelegramForbiddenError as e:
                logging.error(f"TelegramForbiddenError: {e.message}")
                if "user is deactivated" in e.message.lower():
                    user.can_receive_messages = False
                elif "bot was blocked by the user" in e.message.lower():
                    user.can_receive_messages = False
                    await UserRepository.update(user)
            except Exception as e:
                logging.error(e)
            finally:
                if unpacked_cb.announcement_type == AnnouncementType.RESTOCKING:
                    await ItemRepository.set_not_new()
        return Localizator.get_text(BotEntity.ADMIN, "sending_result").format(counter=counter,
                                                                              len=len(active_users),
                                                                              users_count=all_users_count)

    @staticmethod
    async def get_inventory_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items"),
                          callback_data=AdminInventoryManagementCallback.create(level=1, entity_type=EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "delete_category"),
                          callback_data=AdminInventoryManagementCallback.create(level=2,
                                                                                entity_type=EntityType.CATEGORY))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "delete_subcategory"),
                          callback_data=AdminInventoryManagementCallback.create(level=2,
                                                                                entity_type=EntityType.SUBCATEGORY))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "inventory_management"), kb_builder

    @staticmethod
    async def get_add_items_type(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_json"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.JSON, EntityType.ITEM))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "add_items_txt"),
                          callback_data=AdminInventoryManagementCallback.create(1, AddType.TXT, EntityType.ITEM))
        kb_builder.adjust(1)
        kb_builder.row(unpacked_cb.get_back_button())
        return Localizator.get_text(BotEntity.ADMIN, "add_items_msg"), kb_builder

    @staticmethod
    async def get_delete_entity_menu(callback: CallbackQuery):
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        match unpacked_cb.entity_type:
            case EntityType.CATEGORY:
                categories = await CategoryRepository.get_to_delete(unpacked_cb.page)
                [kb_builder.button(text=category.name, callback_data=AdminInventoryManagementCallback.create(
                    level=3,
                    entity_type=unpacked_cb.entity_type,
                    entity_id=category.id
                )) for category in categories]
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                          CategoryRepository.get_maximum_page(),
                                                          unpacked_cb.get_back_button(0))
                return Localizator.get_text(BotEntity.ADMIN, "delete_category"), kb_builder
            case EntityType.SUBCATEGORY:
                subcategories = await SubcategoryRepository.get_to_delete(unpacked_cb.page)
                [kb_builder.button(text=subcategory.name, callback_data=AdminInventoryManagementCallback.create(
                    level=3,
                    entity_type=unpacked_cb.entity_type,
                    entity_id=subcategory.id
                )) for subcategory in subcategories]
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                          SubcategoryRepository.get_maximum_page_to_delete(),
                                                          unpacked_cb.get_back_button(0))
                return Localizator.get_text(BotEntity.ADMIN, "delete_subcategory"), kb_builder

    @staticmethod
    async def delete_confirmation(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        unpacked_cb.confirmation = True
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=unpacked_cb)
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=AdminInventoryManagementCallback.create(0))
        match unpacked_cb.entity_type:
            case EntityType.CATEGORY:
                category = await CategoryRepository.get_by_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
                    entity=unpacked_cb.entity_type.name.capitalize(),
                    entity_name=category.name
                ), kb_builder
            case EntityType.SUBCATEGORY:
                subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "delete_entity_confirmation").format(
                    entity=unpacked_cb.entity_type.name.capitalize(),
                    entity_name=subcategory.name
                ), kb_builder

    @staticmethod
    async def delete_entity(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(AdminConstants.back_to_main_button)
        match unpacked_cb.entity_type:
            case EntityType.CATEGORY:
                category = await CategoryRepository.get_by_id(unpacked_cb.entity_id)
                await ItemRepository.delete_unsold_by_category_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
                    entity_name=category.name,
                    entity_to_delete=unpacked_cb.entity_type.name.capitalize()), kb_builder
            case EntityType.SUBCATEGORY:
                subcategory = await SubcategoryRepository.get_by_id(unpacked_cb.entity_id)
                await ItemRepository.delete_unsold_by_subcategory_id(unpacked_cb.entity_id)
                return Localizator.get_text(BotEntity.ADMIN, "successfully_deleted").format(
                    entity_name=subcategory.name,
                    entity_to_delete=unpacked_cb.entity_type.name.capitalize()), kb_builder

    @staticmethod
    async def get_add_item_msg(callback: CallbackQuery, state: FSMContext):
        unpacked_cb = AdminInventoryManagementCallback.unpack(callback.data)
        kb_markup = InlineKeyboardBuilder()
        kb_markup.button(text=Localizator.get_text(BotEntity.COMMON, 'cancel'),
                         callback_data=AdminInventoryManagementCallback.create(0))
        await state.update_data(add_type=unpacked_cb.add_type.value)
        await state.set_state()
        match unpacked_cb.add_type:
            case AddType.JSON:
                await state.set_state(AdminInventoryManagementStates.document)
                return Localizator.get_text(BotEntity.ADMIN, "add_items_json_msg"), kb_markup
            case AddType.TXT:
                await state.set_state(AdminInventoryManagementStates.document)
                return Localizator.get_text(BotEntity.ADMIN, "add_items_txt_msg"), kb_markup

    @staticmethod
    async def get_user_management_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management"),
                          callback_data=UserManagementCallback.create(1))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "make_refund"),
                          callback_data=UserManagementCallback.create(2))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "user_management"), kb_builder

    @staticmethod
    async def get_credit_management_menu(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = UserManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_add_balance"),
                          callback_data=UserManagementCallback.create(1, UserManagementOperation.ADD_BALANCE))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "credit_management_reduce_balance"),
                          callback_data=UserManagementCallback.create(1, UserManagementOperation.REDUCE_BALANCE))
        kb_builder.row(unpacked_cb.get_back_button())
        return Localizator.get_text(BotEntity.ADMIN, "credit_management"), kb_builder

    @staticmethod
    async def request_user_entity(callback: CallbackQuery, state: FSMContext):
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        await state.set_state(UserManagementStates.user_entity)
        unpacked_cb = UserManagementCallback.unpack(callback.data)
        await state.update_data(operation=unpacked_cb.operation.value)
        return Localizator.get_text(BotEntity.ADMIN, "credit_management_request_user_entity"), kb_builder

    @staticmethod
    async def request_balance_amount(message: Message, state: FSMContext) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        await state.update_data(user_entity=message.text)
        await state.set_state(UserManagementStates.balance_amount)
        data = await state.get_data()
        operation = UserManagementOperation(int(data['operation']))
        match operation:
            case UserManagementOperation.ADD_BALANCE:
                return Localizator.get_text(BotEntity.ADMIN, "credit_management_plus_operation").format(
                    currency_text=Localizator.get_currency_text()), kb_builder
            case UserManagementOperation.REDUCE_BALANCE:
                return Localizator.get_text(BotEntity.ADMIN, "credit_management_minus_operation").format(
                    currency_text=Localizator.get_currency_text()), kb_builder

    @staticmethod
    async def balance_management(message: Message, state: FSMContext) -> str:
        data = await state.get_data()
        await state.clear()
        user = await UserRepository.get_user_entity(data['user_entity'])
        operation = UserManagementOperation(int(data['operation']))
        if user is None:
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_user_not_found")
        elif operation == UserManagementOperation.ADD_BALANCE:
            user.top_up_amount += float(message.text)
            await UserRepository.update(user)
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_added_success").format(
                amount=message.text,
                telegram_id=user.telegram_id,
                currency_text=Localizator.get_currency_text())
        else:
            user.consume_records += float(message.text)
            await UserRepository.update(user)
            return Localizator.get_text(BotEntity.ADMIN, "credit_management_reduced_success").format(
                amount=message.text,
                telegram_id=user.telegram_id,
                currency_text=Localizator.get_currency_text())

    @staticmethod
    async def get_refund_menu(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = UserManagementCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        refund_data = await BuyRepository.get_refund_data(unpacked_cb.page)
        for refund_item in refund_data:
            callback = UserManagementCallback.create(
                unpacked_cb.level + 1,
                UserManagementOperation.REFUND,
                buy_id=refund_item.buy_id)
            if refund_item.telegram_username:
                kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "refund_by_username").format(
                    telegram_username=refund_item.telegram_username,
                    total_price=refund_item.total_price,
                    subcategory=refund_item.subcategory_name,
                    currency_sym=Localizator.get_currency_symbol()),
                    callback_data=callback)
            else:
                kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "refund_by_tgid").format(
                    telegram_id=refund_item.telegram_id,
                    total_price=refund_item.total_price,
                    subcategory=refund_item.subcategory_name,
                    currency_sym=Localizator.get_currency_symbol()),
                    callback_data=callback)
        kb_builder.adjust(1)
        kb_builder = await add_pagination_buttons(kb_builder, unpacked_cb,
                                                  BuyRepository.get_max_refund_page(), unpacked_cb.get_back_button(0))
        return Localizator.get_text(BotEntity.ADMIN, "refund_menu"), kb_builder

    @staticmethod
    async def refund_confirmation(callback: CallbackQuery):
        unpacked_cb = UserManagementCallback.unpack(callback.data)
        unpacked_cb.confirmation = True
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                          callback_data=unpacked_cb)
        kb_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                          callback_data=UserManagementCallback.create(0))
        refund_data = await BuyRepository.get_refund_data_single(unpacked_cb.buy_id)
        if refund_data.telegram_username:
            return Localizator.get_text(BotEntity.ADMIN, "refund_confirmation_by_username").format(
                telegram_username=refund_data.telegram_username,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                total_price=refund_data.total_price,
                currency_sym=Localizator.get_currency_symbol()), kb_builder
        else:
            return Localizator.get_text(BotEntity.ADMIN, "refund_confirmation_by_tgid").format(
                telegram_id=refund_data.telegram_id,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                total_price=refund_data.total_price,
                currency_sym=Localizator.get_currency_symbol()), kb_builder

    @staticmethod
    async def get_statistics_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "users_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.USERS))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "buys_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.BUYS))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "deposits_statistics"),
                          callback_data=StatisticsCallback.create(1, StatisticsEntity.DEPOSITS))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "get_database_file"),
                          callback_data=StatisticsCallback.create(3))
        kb_builder.adjust(1)
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "pick_statistics_entity"), kb_builder

    @staticmethod
    async def get_timedelta_menu(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        unpacked_cb = StatisticsCallback.unpack(callback.data)
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "1_day"),
                          callback_data=StatisticsCallback.create(unpacked_cb.level + 1,
                                                                  unpacked_cb.statistics_entity,
                                                                  StatisticsTimeDelta.DAY))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "7_day"),
                          callback_data=StatisticsCallback.create(unpacked_cb.level + 1,
                                                                  unpacked_cb.statistics_entity,
                                                                  StatisticsTimeDelta.WEEK))
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "30_day"),
                          callback_data=StatisticsCallback.create(unpacked_cb.level + 1,
                                                                  unpacked_cb.statistics_entity,
                                                                  StatisticsTimeDelta.MONTH))
        kb_builder.row(unpacked_cb.get_back_button(0))
        return Localizator.get_text(BotEntity.ADMIN, "statistics_timedelta"), kb_builder

    @staticmethod
    async def get_statistics(callback: CallbackQuery):
        unpacked_cb = StatisticsCallback.unpack(callback.data)
        kb_builder = InlineKeyboardBuilder()
        match unpacked_cb.statistics_entity:
            case StatisticsEntity.USERS:
                users, users_count = await UserRepository.get_by_timedelta(unpacked_cb.timedelta, unpacked_cb.page)
                [kb_builder.button(text=user.telegram_username, url=f't.me/{user.telegram_username}') for user in users
                 if user.telegram_username]
                kb_builder.adjust(1)
                kb_builder = await add_pagination_buttons(
                    kb_builder,
                    unpacked_cb,
                    UserRepository.get_max_page_by_timedelta(unpacked_cb.timedelta),
                    None)
                kb_builder.row(AdminConstants.back_to_main_button, unpacked_cb.get_back_button())
                return Localizator.get_text(BotEntity.ADMIN, "new_users_msg").format(
                    users_count=len(users),
                    timedelta=unpacked_cb.timedelta.value
                ), kb_builder
            case StatisticsEntity.BUYS:
                buys = await BuyRepository.get_by_timedelta(unpacked_cb.timedelta)
                total_profit = 0.0
                items_sold = 0
                for buy in buys:
                    total_profit += buy.total_price
                    items_sold += buy.quantity
                kb_builder.row(AdminConstants.back_to_main_button, unpacked_cb.get_back_button())
                return Localizator.get_text(BotEntity.ADMIN, "sales_statistics").format(
                    timedelta=unpacked_cb.timedelta,
                    total_profit=total_profit, items_sold=items_sold,
                    buys_count=len(buys), currency_sym=Localizator.get_currency_symbol()), kb_builder
            case StatisticsEntity.DEPOSITS:
                deposits = await DepositRepository.get_by_timedelta(unpacked_cb.timedelta)
                fiat_amount = 0.0
                btc_amount = 0.0
                ltc_amount = 0.0
                sol_amount = 0.0
                usdt_trc20_amount = 0.0
                usdt_erc20_amount = 0.0
                usdc_erc20_amount = 0.0
                for deposit in deposits:
                    match deposit.network:
                        case "BTC":
                            btc_amount += deposit.amount / pow(10, 8)
                        case "LTC":
                            ltc_amount += deposit.amount / pow(10, 8)
                        case "SOL":
                            sol_amount += deposit.amount / pow(10, 9)
                        case "TRX":
                            divided_amount = deposit.amount / pow(10, 6)
                            fiat_amount += divided_amount
                            usdt_trc20_amount += divided_amount
                        case "ETH":
                            divided_amount = deposit.amount / pow(10, 6)
                            fiat_amount += divided_amount
                            match deposit.token_name:
                                case "USDT_ERC20":
                                    usdt_erc20_amount += divided_amount
                                case "USDC_ERC20":
                                    usdc_erc20_amount += divided_amount
                btc_price = await CryptoApiManager.get_crypto_prices(Cryptocurrency.BTC)
                ltc_price = await CryptoApiManager.get_crypto_prices(Cryptocurrency.LTC)
                sol_price = await CryptoApiManager.get_crypto_prices(Cryptocurrency.SOL)
                fiat_amount += (btc_amount * btc_price) + (ltc_amount * ltc_price) + (sol_amount * sol_price)
                kb_builder.row(AdminConstants.back_to_main_button, unpacked_cb.get_back_button())
                return Localizator.get_text(BotEntity.ADMIN, "deposits_statistics_msg").format(
                    timedelta=unpacked_cb.timedelta, deposits_count=len(deposits),
                    btc_amount=btc_amount, ltc_amount=ltc_amount,
                    sol_amount=sol_amount, usdt_trc20_amount=usdt_trc20_amount,
                    usdt_erc20_amount=usdt_erc20_amount, usdc_erc20_amount=usdc_erc20_amount, fiat_amount=fiat_amount,
                    currency_text=Localizator.get_currency_text()), kb_builder

    @staticmethod
    async def get_wallet_menu() -> tuple[str, InlineKeyboardBuilder]:
        kb_builder = InlineKeyboardBuilder()
        kb_builder.button(text=Localizator.get_text(BotEntity.ADMIN, "withdraw_funds"),
                          callback_data=WalletCallback.create(1))
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "crypto_withdraw"), kb_builder

    @staticmethod
    async def get_withdraw_menu():
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(AdminConstants.back_to_main_button)
        return Localizator.get_text(BotEntity.ADMIN, "choose_crypto_to_withdraw"), kb_builder
