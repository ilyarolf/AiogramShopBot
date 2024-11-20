from aiogram.filters.callback_data import CallbackData


class AllCategoriesCallback(CallbackData, prefix="all_categories"):
    level: int
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
               page: int = 0):
        return AllCategoriesCallback(level=level, category_id=category_id, subcategory_id=subcategory_id, price=price,
                                     total_price=total_price,
                                     quantity=quantity, confirmation=confirmation, page=page)
