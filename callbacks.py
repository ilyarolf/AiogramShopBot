from enum import Enum

from aiogram.filters.callback_data import CallbackData


class BaseCallback(CallbackData, prefix="base"):
    level: int


class AllCategoriesCallback(BaseCallback, prefix="all_categories"):
    category_id: int
    subcategory_id: int
    price: float
    quantity: int
    total_price: float
    confirmation: bool
    page: int

    @staticmethod
    def create(level: int,
               category_id: int = -1,
               subcategory_id: int = -1,
               price: float = 0.0,
               total_price: float = 0.0,
               quantity: int = 0,
               confirmation: bool = False,
               page: int = 0) -> 'AllCategoriesCallback':
        return AllCategoriesCallback(level=level, category_id=category_id, subcategory_id=subcategory_id, price=price,
                                     total_price=total_price,
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
    delete_cart_item_confirmation: bool
    purchase_confirmation: bool
    cart_grand_total: float

    @staticmethod
    def create(level: int = 0, page: int = 0, cart_id: int = -1, cart_item_id: int = -1,
               delete_cart_item_confirmation=False, purchase_confirmation=False,
               cart_grand_total=0.0):
        return CartCallback(level=level, page=page, cart_id=cart_id, cart_item_id=cart_item_id,
                            delete_cart_item_confirmation=delete_cart_item_confirmation,
                            purchase_confirmation=purchase_confirmation, cart_grand_total=cart_grand_total)


class AdminMenuCallback(BaseCallback, prefix="admin_menu"):
    action: str
    args_to_action: str | int
    page: int

    @staticmethod
    def create(level: int, action: str = "", args_to_action: str = "", page: int = 0):
        return AdminMenuCallback(level=level, action=action, args_to_action=args_to_action, page=page)


class AnnouncementType(Enum):
    RESTOCKING = 1
    CURRENT_STOCK = 2
    FROM_RECEIVING_MESSAGE = 3


class AdminAnnouncementCallback(BaseCallback, prefix="admin_announcement"):
    announcement_type: AnnouncementType

    @staticmethod
    def create(level: int):
        return AdminAnnouncementCallback(level=level, announcement_type=AnnouncementType.FROM_RECEIVING_MESSAGE)
