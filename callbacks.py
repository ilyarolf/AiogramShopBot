from aiogram import types
from aiogram.filters.callback_data import CallbackData
from enums.add_type import AddType
from enums.announcement_type import AnnouncementType
from enums.bot_entity import BotEntity
from enums.buy_status import BuyStatus
from enums.cart_action import CartAction
from enums.coupon_type import CouponType
from enums.cryptocurrency import Cryptocurrency
from enums.entity_type import EntityType
from enums.item_type import ItemType
from enums.keyboard_button import KeyboardButton
from enums.language import Language
from enums.shipping_management_action import ShippingManagementAction
from enums.shipping_type_property import ShippingOptionProperty
from enums.sort_order import SortOrder
from enums.sort_property import SortProperty
from enums.statistics_entity import StatisticsEntity
from enums.statistics_timedelta import StatisticsTimeDelta
from enums.user_management_operation import UserManagementOperation
from enums.coupon_number_of_uses import CouponNumberOfUses
from enums.user_role import UserRole
from utils.utils import get_text


class BaseCallback(CallbackData, prefix="base"):
    level: int
    page: int = 0

    def get_back_button(self, language: Language, lvl: int | None = None):
        cb_copy = self.__copy__()
        if lvl is None:
            cb_copy.level = cb_copy.level - 1
        else:
            cb_copy.level = lvl
        return types.InlineKeyboardButton(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=cb_copy.create(**cb_copy.model_dump()).pack())


class SortingCallback(CallbackData, prefix="sorting"):
    sort_order: SortOrder
    sort_property: SortProperty
    is_filter_enabled: bool = False


class AllCategoriesCallback(BaseCallback, SortingCallback, prefix="all_categories"):
    item_type: ItemType | None
    category_id: int | None
    subcategory_id: int | None
    quantity: int | None
    confirmation: bool

    @staticmethod
    def create(level: int,
               item_type: ItemType | None = None,
               category_id: int | None = None,
               subcategory_id: int | None = None,
               quantity: int | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.NAME,
               is_filter_enabled: bool = False,
               confirmation: bool = False,
               page: int = 0) -> 'AllCategoriesCallback':
        return AllCategoriesCallback(level=level,
                                     item_type=item_type,
                                     category_id=category_id, subcategory_id=subcategory_id,
                                     sort_order=sort_order, sort_property=sort_property,
                                     quantity=quantity, is_filter_enabled=is_filter_enabled,
                                     confirmation=confirmation, page=page)


class MyProfileCallback(BaseCallback, SortingCallback, prefix="my_profile"):
    buy_id: int | None = None
    buyItem_id: int | None = None
    cryptocurrency: Cryptocurrency | None = None
    language: Language | None = None
    user_role: UserRole = UserRole.USER
    confirmation: bool = False

    @staticmethod
    def create(level: int,
               buy_id: int | None = None,
               buyItem_id: int | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.BUY_DATETIME,
               is_filter_enabled: bool = False,
               cryptocurrency: Cryptocurrency | None = None,
               language: Language | None = None,
               user_role: UserRole = UserRole.USER,
               confirmation: bool = False,
               page=0) -> 'MyProfileCallback':
        return MyProfileCallback(level=level, buy_id=buy_id, buyItem_id=buyItem_id,
                                 sort_order=sort_order, sort_property=sort_property,
                                 is_filter_enabled=is_filter_enabled,
                                 cryptocurrency=cryptocurrency,
                                 language=language,
                                 user_role=user_role,
                                 confirmation=confirmation,
                                 page=page)


class CartCallback(BaseCallback, prefix="cart"):
    cart_id: int
    cart_item_id: int
    cart_action: CartAction | None
    shipping_option_id: int | None
    confirmation: bool

    @staticmethod
    def create(level: int = 0,
               cart_id: int = -1,
               cart_item_id: int = -1,
               cart_action: CartAction | None = None,
               shipping_option_id: int | None = None,
               confirmation=False,
               page: int = 0):
        return CartCallback(level=level,
                            cart_id=cart_id,
                            cart_item_id=cart_item_id,
                            cart_action=cart_action,
                            shipping_option_id=shipping_option_id,
                            confirmation=confirmation,
                            page=page)


class AdminMenuCallback(BaseCallback, prefix="admin_menu"):

    @staticmethod
    def create(level: int, page: int = 0):
        return AdminMenuCallback(level=level, page=page)


class AnnouncementCallback(BaseCallback, prefix="announcement"):
    announcement_type: AnnouncementType | None

    @staticmethod
    def create(level: int, announcement_type: AnnouncementType | None = None, page: int = 0):
        return AnnouncementCallback(level=level, announcement_type=announcement_type, page=page)


class InventoryManagementCallback(BaseCallback, SortingCallback, prefix="inventory_management"):
    add_type: AddType | None
    entity_type: EntityType | None
    entity_id: int | None
    confirmation: bool

    @staticmethod
    def create(level: int,
               add_type: AddType | None = None,
               entity_type: EntityType | None = None,
               entity_id: int | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.NAME,
               is_filter_enabled: bool = False,
               page: int = 0,
               confirmation: bool = False):
        return InventoryManagementCallback(level=level,
                                           add_type=add_type,
                                           entity_type=entity_type,
                                           entity_id=entity_id,
                                           sort_order=sort_order,
                                           sort_property=sort_property,
                                           is_filter_enabled=is_filter_enabled,
                                           page=page,
                                           confirmation=confirmation)


class UserManagementCallback(BaseCallback, SortingCallback, prefix="user_management"):
    operation: UserManagementOperation | None
    user_id: int | None
    buy_id: int | None
    confirmation: bool

    @staticmethod
    def create(level: int,
               operation: UserManagementOperation | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.BUY_DATETIME,
               is_filter_enabled: bool = False,
               user_id: int | None = None,
               buy_id: int | None = None,
               page: int = 0,
               confirmation: bool = False):
        return UserManagementCallback(level=level,
                                      operation=operation,
                                      sort_order=sort_order,
                                      sort_property=sort_property,
                                      is_filter_enabled=is_filter_enabled,
                                      user_id=user_id,
                                      buy_id=buy_id,
                                      page=page,
                                      confirmation=confirmation)


class StatisticsCallback(BaseCallback, prefix="statistics"):
    statistics_entity: StatisticsEntity | None
    timedelta: StatisticsTimeDelta | None

    @staticmethod
    def create(level: int, statistics_entity: StatisticsEntity | None = None,
               timedelta: StatisticsTimeDelta | None = None, page: int = 0):
        return StatisticsCallback(level=level, statistics_entity=statistics_entity, timedelta=timedelta, page=page)


class WalletCallback(BaseCallback, prefix="wallet"):
    cryptocurrency: Cryptocurrency | None

    @staticmethod
    def create(level: int, cryptocurrency: Cryptocurrency | None = None):
        return WalletCallback(level=level, cryptocurrency=cryptocurrency)


class MediaManagementCallback(BaseCallback, SortingCallback, prefix="media"):
    entity_type: EntityType | None
    entity_id: int | None = None
    keyboard_button: KeyboardButton | None = None

    @staticmethod
    def create(level: int, entity_type: EntityType | None = None,
               keyboard_button: KeyboardButton | None = None,
               sort_order: SortOrder = SortOrder.DISABLE,
               sort_property: SortProperty = SortProperty.NAME,
               is_filter_enabled: bool = False,
               entity_id: int | None = None, page: int = 0):
        return MediaManagementCallback(level=level,
                                       entity_type=entity_type,
                                       entity_id=entity_id,
                                       sort_order=sort_order,
                                       sort_property=sort_property,
                                       is_filter_enabled=is_filter_enabled,
                                       keyboard_button=keyboard_button,
                                       page=page)


class CouponManagementCallback(BaseCallback, prefix="coupons"):
    coupon_id: int | None = None
    coupon_type: CouponType | None = None
    number_of_uses: CouponNumberOfUses | None = None
    confirmation: bool

    @staticmethod
    def create(level: int, coupon_id: int | None = None, coupon_type: CouponType | None = None,
               number_of_uses: CouponNumberOfUses | None = None, confirmation: bool = False, page: int = 0):
        return CouponManagementCallback(level=level,
                                        coupon_id=coupon_id,
                                        coupon_type=coupon_type,
                                        number_of_uses=number_of_uses,
                                        confirmation=confirmation,
                                        page=page)


class ShippingManagementCallback(BaseCallback, prefix="shipping_management"):
    shipping_management_action: ShippingManagementAction | None = None
    shipping_type_property: ShippingOptionProperty | None = None
    shipping_id: int | None = None
    confirmation: bool

    @staticmethod
    def create(level: int, shipping_management_action: ShippingManagementAction | None = None,
               shipping_type_property: ShippingOptionProperty | None = None,
               shipping_id: int | None = None, confirmation: bool = False, page: int = 0):
        return ShippingManagementCallback(level=level,
                                          shipping_management_action=shipping_management_action,
                                          shipping_type_property=shipping_type_property,
                                          shipping_id=shipping_id,
                                          confirmation=confirmation,
                                          page=page)


class BuysManagementCallback(BaseCallback, prefix="buys"):
    buy_id: int | None = None
    item_type: ItemType | None = None
    buy_status: BuyStatus | None = None
    confirmation: bool = False

    @staticmethod
    def create(level: int,
               buy_id: int | None = None,
               item_type: ItemType | None = None,
               buy_status: BuyStatus | None = None,
               confirmation: bool = False,
               page: int = 0):
        return BuysManagementCallback(level=level, buy_id=buy_id,
                                      item_type=item_type,
                                      buy_status=buy_status, confirmation=confirmation,
                                      page=page)


class ReviewManagementCallback(BaseCallback, prefix="reviews"):
    review_id: int | None = None
    buy_id: int | None = None
    buyItem_id: int | None = None
    rating: int | None = None
    user_role: UserRole = UserRole.USER
    confirmation: bool = False

    @staticmethod
    def create(level: int,
               review_id: int | None = None,
               buy_id: int | None = None,
               buyItem_id: int | None = None,
               rating: int | None = None,
               user_role: UserRole = UserRole.USER,
               page: int = 0,
               confirmation: bool = False):
        return ReviewManagementCallback(level=level,
                                        review_id=review_id,
                                        buy_id=buy_id,
                                        buyItem_id=buyItem_id,
                                        rating=rating,
                                        user_role=user_role,
                                        page=page,
                                        confirmation=confirmation)
