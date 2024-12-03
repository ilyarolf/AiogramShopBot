from enum import IntEnum

from aiogram import types
from aiogram.filters.callback_data import CallbackData

from enums.bot_entity import BotEntity
from utils.localizator import Localizator


class BaseCallback(CallbackData, prefix="base"):
    level: int

    def get_back_button(self, lvl: int | None = None):
        cb_copy = self.__copy__()
        if lvl is None:
            cb_copy.level = cb_copy.level - 1
        else:
            cb_copy.level = lvl
        return types.InlineKeyboardButton(
            text=Localizator.get_text(BotEntity.COMMON, "back_button"),
            callback_data=cb_copy.create(**cb_copy.model_dump()).pack())


class AllCategoriesCallback(BaseCallback, prefix="all_categories"):
    category_id: int
    subcategory_id: int
    price: float
    quantity: int
    confirmation: bool
    page: int

    @staticmethod
    def create(level: int,
               category_id: int = -1,
               subcategory_id: int = -1,
               price: float = 0.0,
               quantity: int = 0,
               confirmation: bool = False,
               page: int = 0) -> 'AllCategoriesCallback':
        return AllCategoriesCallback(level=level, category_id=category_id, subcategory_id=subcategory_id, price=price,
                                     quantity=quantity, confirmation=confirmation, page=page)


class MyProfileCallback(BaseCallback, prefix="my_profile"):
    action: str
    args_for_action: int | str
    page: int

    @staticmethod
    def create(level: int, action: str = "", args_for_action="", page=0) -> 'MyProfileCallback':
        return MyProfileCallback(level=level, action=action, args_for_action=args_for_action, page=page)


class CartCallback(BaseCallback, prefix="cart"):
    page: int
    cart_id: int
    cart_item_id: int
    confirmation: bool

    @staticmethod
    def create(level: int = 0, page: int = 0, cart_id: int = -1, cart_item_id: int = -1,
               confirmation=False):
        return CartCallback(level=level, page=page, cart_id=cart_id, cart_item_id=cart_item_id,
                            confirmation=confirmation)


class AdminMenuCallback(BaseCallback, prefix="admin_menu"):
    action: str
    args_to_action: str | int
    page: int

    @staticmethod
    def create(level: int, action: str = "", args_to_action: str = "", page: int = 0):
        return AdminMenuCallback(level=level, action=action, args_to_action=args_to_action, page=page)


class AnnouncementType(IntEnum):
    RESTOCKING = 1
    CURRENT_STOCK = 2
    FROM_RECEIVING_MESSAGE = 3


class AdminAnnouncementCallback(BaseCallback, prefix="announcement"):
    announcement_type: AnnouncementType | None

    @staticmethod
    def create(level: int, announcement_type: AnnouncementType | None = None):
        return AdminAnnouncementCallback(level=level, announcement_type=announcement_type)


class AddType(IntEnum):
    JSON = 1
    TXT = 2


class EntityType(IntEnum):
    CATEGORY = 1
    SUBCATEGORY = 2
    ITEM = 3


class AdminInventoryManagementCallback(BaseCallback, prefix="inventory_management"):
    add_type: AddType | None
    entity_type: EntityType | None
    entity_id: int | None
    page: int
    confirmation: bool

    @staticmethod
    def create(level: int, add_type: AddType | None = None, entity_type: EntityType | None = None,
               entity_id: int | None = None, page: int = 0, confirmation: bool = False):
        return AdminInventoryManagementCallback(level=level,
                                                add_type=add_type,
                                                entity_type=entity_type,
                                                entity_id=entity_id,
                                                page=page,
                                                confirmation=confirmation)


class UserManagementOperation(IntEnum):
    REFUND = 1
    ADD_BALANCE = 2
    REDUCE_BALANCE = 3


class UserManagementCallback(BaseCallback, prefix="user_management"):
    operation: UserManagementOperation | None
    page: int
    confirmation: bool
    buy_id: int | None

    @staticmethod
    def create(level: int, operation: UserManagementOperation | None = None, page: int = 0, confirmation: bool = False,
               buy_id: int | None = None):
        return UserManagementCallback(level=level, operation=operation, page=page, confirmation=confirmation,
                                      buy_id=buy_id)


class StatisticsEntity(IntEnum):
    USERS = 1
    BUYS = 2
    DEPOSITS = 3


class StatisticsTimeDelta(IntEnum):
    DAY = 1
    WEEK = 7
    MONTH = 30


class StatisticsCallback(BaseCallback, prefix="statistics"):
    statistics_entity: StatisticsEntity | None
    timedelta: StatisticsTimeDelta | None
    page: int

    @staticmethod
    def create(level: int, statistics_entity: StatisticsEntity | None = None,
               timedelta: StatisticsTimeDelta | None = None, page: int = 0):
        return StatisticsCallback(level=level, statistics_entity=statistics_entity, timedelta=timedelta, page=page)


class WalletCallback(BaseCallback, prefix="wallet"):
    pass

    @staticmethod
    def create(level: int):
        return WalletCallback(level=level)
