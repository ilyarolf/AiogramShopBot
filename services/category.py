from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AllCategoriesCallback
from enums.bot_entity import BotEntity
from handlers.common.common import add_pagination_buttons
from models.category import CategoryDTO
from repositories.category import CategoryRepository
from utils.localizator import Localizator


class CategoryService:
    """
    Service for tree-based category navigation with image support.
    Handles dynamic navigation through N-level category tree.
    """

    @staticmethod
    async def get_buttons(
        session: AsyncSession | Session,
        callback: CallbackQuery | None = None
    ) -> tuple[str, InlineKeyboardBuilder, str | None]:
        """
        Get category navigation buttons for current level.

        Returns:
            tuple: (message_text, keyboard_builder, image_file_id or None)
        """
        if callback is None:
            unpacked_cb = AllCategoriesCallback.create(level=0)
        else:
            unpacked_cb = AllCategoriesCallback.unpack(callback.data)

        category_id = unpacked_cb.category_id
        page = unpacked_cb.page

        # Determine if we're at root level or viewing children
        if category_id == -1:
            # Root level - show root categories
            categories = await CategoryRepository.get_roots(page, session)
            max_page_coro = CategoryRepository.get_maximum_page_roots(session)
            parent_category = None
        else:
            # Child level - show children of current category
            categories = await CategoryRepository.get_children(category_id, page, session)
            max_page_coro = CategoryRepository.get_maximum_page_children(category_id, session)
            parent_category = await CategoryRepository.get_by_id(category_id, session)

        kb_builder = InlineKeyboardBuilder()

        # Build category buttons
        for cat in categories:
            if cat.is_product:
                # Product category - show price and quantity
                qty = await CategoryRepository.get_available_qty(cat.id, session)
                button_text = Localizator.get_text(BotEntity.USER, "product_button").format(
                    product_name=cat.name,
                    price=cat.price,
                    currency_sym=Localizator.get_currency_symbol(),
                    available_quantity=qty
                )
                # Level for product: select quantity
                next_level = unpacked_cb.level + 1
            else:
                # Navigation category - just show name
                button_text = cat.name
                # Level for navigation: same level but different category_id
                next_level = unpacked_cb.level

            kb_builder.button(
                text=button_text,
                callback_data=AllCategoriesCallback.create(
                    level=next_level,
                    category_id=cat.id,
                    page=0  # Reset page when entering new category
                )
            )

        kb_builder.adjust(1)

        # Add pagination and back button
        back_button = None
        if category_id != -1:
            # Not at root - add back button
            if parent_category and parent_category.parent_id is not None:
                # Go to parent's parent
                back_button = AllCategoriesCallback.create(
                    level=unpacked_cb.level,
                    category_id=parent_category.parent_id,
                    page=0
                )
            else:
                # Go to root
                back_button = AllCategoriesCallback.create(
                    level=0,
                    category_id=-1,
                    page=0
                )
            back_btn = unpacked_cb.get_back_button(lvl=0)
            back_btn.callback_data = back_button.pack()

        max_page = await max_page_coro
        kb_builder = await add_pagination_buttons(
            kb_builder,
            unpacked_cb,
            max_page,
            back_btn if category_id != -1 else None
        )

        # Determine message text and image
        if len(categories) == 0:
            msg = Localizator.get_text(BotEntity.USER, "no_categories")
            return msg, kb_builder, None

        if category_id == -1:
            msg = Localizator.get_text(BotEntity.USER, "all_categories")
            return msg, kb_builder, None
        else:
            # Build breadcrumb
            breadcrumb = await CategoryRepository.get_breadcrumb(category_id, session)
            breadcrumb_str = " > ".join([c.name for c in breadcrumb])
            msg = f"📂 {breadcrumb_str}"

            # Return parent's image if it exists
            image_file_id = parent_category.image_file_id if parent_category else None
            return msg, kb_builder, image_file_id

    @staticmethod
    async def get_product_details(
        callback: CallbackQuery,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder, str | None]:
        """
        Get product details with quantity selection buttons.

        Returns:
            tuple: (message_text, keyboard_builder, image_file_id or None)
        """
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        category_id = unpacked_cb.category_id

        product = await CategoryRepository.get_by_id(category_id, session)
        if product is None or not product.is_product:
            return Localizator.get_text(BotEntity.USER, "no_categories"), InlineKeyboardBuilder(), None

        available_qty = await CategoryRepository.get_available_qty(category_id, session)

        # Build breadcrumb for context
        breadcrumb = await CategoryRepository.get_breadcrumb(category_id, session)
        breadcrumb_str = " > ".join([c.name for c in breadcrumb[:-1]]) if len(breadcrumb) > 1 else ""

        msg = Localizator.get_text(BotEntity.USER, "select_quantity").format(
            category_name=breadcrumb_str if breadcrumb_str else "Root",
            product_name=product.name,
            price=product.price,
            currency_sym=Localizator.get_currency_symbol(),
            description=product.description or "",
            quantity=available_qty
        )

        kb_builder = InlineKeyboardBuilder()

        # Quantity buttons (1-5, or up to available qty)
        max_buttons = min(5, available_qty)
        for qty in range(1, max_buttons + 1):
            kb_builder.button(
                text=str(qty),
                callback_data=AllCategoriesCallback.create(
                    level=unpacked_cb.level + 1,
                    category_id=category_id,
                    quantity=qty,
                    page=0
                )
            )

        kb_builder.adjust(5)

        # Back button to parent category
        if product.parent_id is not None:
            back_cb = AllCategoriesCallback.create(
                level=unpacked_cb.level - 1,
                category_id=product.parent_id,
                page=0
            )
        else:
            back_cb = AllCategoriesCallback.create(
                level=0,
                category_id=-1,
                page=0
            )

        kb_builder.row(unpacked_cb.get_back_button(lvl=unpacked_cb.level - 1))

        return msg, kb_builder, product.image_file_id

    @staticmethod
    async def get_add_to_cart_buttons(
        callback: CallbackQuery,
        session: AsyncSession | Session
    ) -> tuple[str, InlineKeyboardBuilder, str | None]:
        """
        Get add to cart confirmation buttons.

        Returns:
            tuple: (message_text, keyboard_builder, image_file_id or None)
        """
        unpacked_cb = AllCategoriesCallback.unpack(callback.data)
        category_id = unpacked_cb.category_id
        quantity = unpacked_cb.quantity

        product = await CategoryRepository.get_by_id(category_id, session)
        if product is None or not product.is_product:
            return Localizator.get_text(BotEntity.USER, "no_categories"), InlineKeyboardBuilder(), None

        # Build breadcrumb for context
        breadcrumb = await CategoryRepository.get_breadcrumb(category_id, session)
        breadcrumb_str = " > ".join([c.name for c in breadcrumb[:-1]]) if len(breadcrumb) > 1 else ""

        total_price = product.price * quantity

        msg = Localizator.get_text(BotEntity.USER, "buy_confirmation").format(
            category_name=breadcrumb_str if breadcrumb_str else "Root",
            product_name=product.name,
            price=product.price,
            currency_sym=Localizator.get_currency_symbol(),
            description=product.description or "",
            quantity=quantity,
            total_price=total_price
        )

        kb_builder = InlineKeyboardBuilder()

        # Confirm button
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "confirm"),
            callback_data=AllCategoriesCallback.create(
                level=unpacked_cb.level + 1,
                category_id=category_id,
                quantity=quantity,
                confirmation=True,
                page=0
            )
        )

        # Cancel button - back to quantity selection
        kb_builder.button(
            text=Localizator.get_text(BotEntity.COMMON, "cancel"),
            callback_data=AllCategoriesCallback.create(
                level=unpacked_cb.level - 1,
                category_id=category_id,
                quantity=0,
                page=0
            )
        )

        kb_builder.adjust(2)

        return msg, kb_builder, product.image_file_id
