from aiogram import types
from aiogram.filters.callback_data import CallbackData
from enums.add_type import AddType
from enums.announcement_type import AnnouncementType
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.entity_type import EntityType
from enums.keyboardbutton import KeyboardButton
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from enums.statistics_entity import StatisticsEntity
from enums.statistics_timedelta import StatisticsTimeDelta
from enums.user_management_operation import UserManagementOperation
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


class SortingCallback(CallbackData, prefix="sorting"):
    sort_order: SortOrder
    sort_property: SortProperty
    is_filter_enabled: bool = False


class AllCategoriesCallback(BaseCallback, SortingCallback, prefix="all_categories"):
    category_id: int | None
    subcategory_id: int | None
    quantity: int | None
    confirmation: bool
    page: int

    @staticmethod
    def create(level: int,
               category_id: int | None = None,
               subcategory_id: int | None = None,
               quantity: int | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.NAME,
               is_filter_enabled: bool = False,
               confirmation: bool = False,
               page: int = 0) -> 'AllCategoriesCallback':
        return AllCategoriesCallback(level=level,
                                     category_id=category_id, subcategory_id=subcategory_id,
                                     sort_order=sort_order, sort_property=sort_property,
                                     quantity=quantity, is_filter_enabled=is_filter_enabled,
                                     confirmation=confirmation, page=page)


class MyProfileCallback(BaseCallback, SortingCallback, prefix="my_profile"):
    buy_id: int | None = None
    cryptocurrency: Cryptocurrency | None = None
    page: int

    @staticmethod
    def create(level: int,
               buy_id: int | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.BUY_DATETIME,
               is_filter_enabled: bool = False,
               cryptocurrency: Cryptocurrency | None = None,
               page=0) -> 'MyProfileCallback':
        return MyProfileCallback(level=level, buy_id=buy_id,
                                 sort_order=sort_order, sort_property=sort_property,
                                 is_filter_enabled=is_filter_enabled,
                                 cryptocurrency=cryptocurrency, page=page)


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

    @staticmethod
    def create(level: int):
        return AdminMenuCallback(level=level)


class AnnouncementCallback(BaseCallback, prefix="announcement"):
    announcement_type: AnnouncementType | None

    @staticmethod
    def create(level: int, announcement_type: AnnouncementType | None = None):
        return AnnouncementCallback(level=level, announcement_type=announcement_type)


class InventoryManagementCallback(BaseCallback, prefix="inventory_management"):
    add_type: AddType | None
    entity_type: EntityType | None
    entity_id: int | None
    page: int
    confirmation: bool

    @staticmethod
    def create(level: int, add_type: AddType | None = None, entity_type: EntityType | None = None,
               entity_id: int | None = None, page: int = 0, confirmation: bool = False):
        return InventoryManagementCallback(level=level,
                                           add_type=add_type,
                                           entity_type=entity_type,
                                           entity_id=entity_id,
                                           page=page,
                                           confirmation=confirmation)


class UserManagementCallback(BaseCallback, SortingCallback, prefix="user_management"):
    operation: UserManagementOperation | None
    buy_id: int | None
    page: int
    confirmation: bool

    @staticmethod
    def create(level: int, operation: UserManagementOperation | None = None,
               sort_order: SortOrder = SortOrder.DISABLE, sort_property: SortProperty = SortProperty.BUY_DATETIME,
               is_filter_enabled: bool = False,
               buy_id: int | None = None, page: int = 0, confirmation: bool = False):
        return UserManagementCallback(level=level, operation=operation,
                                      sort_order=sort_order, sort_property=sort_property,
                                      is_filter_enabled=is_filter_enabled,
                                      buy_id=buy_id,
                                      page=page, confirmation=confirmation)


class StatisticsCallback(BaseCallback, prefix="statistics"):
    statistics_entity: StatisticsEntity | None
    timedelta: StatisticsTimeDelta | None
    page: int

    @staticmethod
    def create(level: int, statistics_entity: StatisticsEntity | None = None,
               timedelta: StatisticsTimeDelta | None = None, page: int = 0):
        return StatisticsCallback(level=level, statistics_entity=statistics_entity, timedelta=timedelta, page=page)


class WalletCallback(BaseCallback, prefix="wallet"):
    cryptocurrency: Cryptocurrency | None

    @staticmethod
    def create(level: int, cryptocurrency: Cryptocurrency | None = None):
        return WalletCallback(level=level, cryptocurrency=cryptocurrency)


class MediaManagementCallback(BaseCallback, prefix="media"):
    entity_type: EntityType | None
    entity_id: int | None = None
    keyboard_button: KeyboardButton | None = None
    page: int

    @staticmethod
    def create(level: int, entity_type: EntityType | None = None,
               keyboard_button: KeyboardButton | None = None,
               entity_id: int | None = None, page: int = 0):
        return MediaManagementCallback(level=level,
                                       entity_type=entity_type,
                                       entity_id=entity_id,
                                       keyboard_button=keyboard_button,
                                       page=page)
