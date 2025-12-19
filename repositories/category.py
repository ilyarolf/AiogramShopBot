import math
from typing import List, Set

from sqlalchemy import select, func, and_, update, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from db import session_execute, session_flush
from models.category import Category, CategoryDTO
from models.item import Item


class CategoryRepository:
    """
    Repository for tree-based category operations.
    Supports unlimited hierarchy depth via parent_id self-reference.
    """

    # ==================== INTERNAL HELPERS ====================

    @staticmethod
    async def _get_categories_with_stock_ids(session: Session | AsyncSession) -> Set[int]:
        """
        Get all category IDs that have available items in their subtree.
        Uses recursive CTE to find product categories with stock and all their ancestors.

        This enables DB-level filtering for correct pagination.
        """
        cte_query = text("""
            WITH RECURSIVE
            -- Step 1: Find all product categories with unsold items
            products_with_stock AS (
                SELECT DISTINCT c.id
                FROM categories c
                JOIN items i ON i.category_id = c.id
                WHERE c.is_product = 1 AND i.is_sold = 0
            ),
            -- Step 2: Recursively find all ancestors of those products
            ancestors AS (
                -- Base case: start with product categories that have stock
                SELECT id, parent_id
                FROM categories
                WHERE id IN (SELECT id FROM products_with_stock)

                UNION

                -- Recursive case: get parent of each category
                SELECT c.id, c.parent_id
                FROM categories c
                INNER JOIN ancestors a ON c.id = a.parent_id
                WHERE c.id IS NOT NULL
            )
            -- Return all category IDs (products with stock + all their ancestors)
            SELECT DISTINCT id FROM ancestors
        """)

        result = await session_execute(cte_query, session)
        return {row[0] for row in result.fetchall()}

    # ==================== READ OPERATIONS ====================

    @staticmethod
    async def get_roots(page: int, session: Session | AsyncSession) -> List[CategoryDTO]:
        """
        Get root categories that have available items in subtree.
        Filters at DB level for correct pagination.
        """
        # Get all category IDs with stock in subtree
        valid_ids = await CategoryRepository._get_categories_with_stock_ids(session)

        if not valid_ids:
            return []

        # Query only valid root categories with proper pagination
        stmt = (
            select(Category)
            .where(and_(
                Category.parent_id.is_(None),
                Category.id.in_(valid_ids)
            ))
            .order_by(Category.id)
            .limit(config.PAGE_ENTRIES)
            .offset(page * config.PAGE_ENTRIES)
        )
        result = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(c, from_attributes=True) for c in result.scalars().all()]

    @staticmethod
    async def get_children(parent_id: int, page: int, session: Session | AsyncSession) -> List[CategoryDTO]:
        """
        Get child categories of a given parent that have available items.
        Filters at DB level for correct pagination.
        """
        # Get all category IDs with stock in subtree
        valid_ids = await CategoryRepository._get_categories_with_stock_ids(session)

        if not valid_ids:
            return []

        # Query only valid children with proper pagination
        stmt = (
            select(Category)
            .where(and_(
                Category.parent_id == parent_id,
                Category.id.in_(valid_ids)
            ))
            .order_by(Category.id)
            .limit(config.PAGE_ENTRIES)
            .offset(page * config.PAGE_ENTRIES)
        )
        result = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(c, from_attributes=True) for c in result.scalars().all()]

    @staticmethod
    async def get_all_roots(session: Session | AsyncSession) -> List[CategoryDTO]:
        """Get ALL root categories (for admin view, not filtered by stock)."""
        stmt = select(Category).where(Category.parent_id.is_(None))
        result = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(c, from_attributes=True) for c in result.scalars().all()]

    @staticmethod
    async def get_all_children(parent_id: int, session: Session | AsyncSession) -> List[CategoryDTO]:
        """Get ALL children (for admin view, not filtered by stock)."""
        stmt = select(Category).where(Category.parent_id == parent_id)
        result = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(c, from_attributes=True) for c in result.scalars().all()]

    @staticmethod
    async def has_available_items(category_id: int, session: Session | AsyncSession) -> bool:
        """
        Check if a category or any of its descendants has unsold items.
        Uses recursive CTE for efficient single-query traversal.
        """
        cte_query = text("""
            WITH RECURSIVE category_tree AS (
                SELECT id, is_product FROM categories WHERE id = :category_id
                UNION ALL
                SELECT c.id, c.is_product
                FROM categories c
                INNER JOIN category_tree ct ON c.parent_id = ct.id
            )
            SELECT COUNT(*) FROM items
            WHERE category_id IN (
                SELECT id FROM category_tree WHERE is_product = 1
            ) AND is_sold = 0
        """)

        result = await session_execute(cte_query, session, {"category_id": category_id})
        count = result.scalar() or 0
        return count > 0

    @staticmethod
    async def get_available_qty(category_id: int, session: Session | AsyncSession) -> int:
        """Get count of unsold items for a product category."""
        stmt = (
            select(func.count())
            .select_from(Item)
            .where(and_(Item.category_id == category_id, Item.is_sold == False))
        )
        result = await session_execute(stmt, session)
        return result.scalar() or 0

    @staticmethod
    async def get_by_id(category_id: int, session: Session | AsyncSession) -> CategoryDTO | None:
        """Get single category by ID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await session_execute(stmt, session)
        category = result.scalar()
        if category is None:
            return None
        return CategoryDTO.model_validate(category, from_attributes=True)

    @staticmethod
    async def get_breadcrumb(category_id: int, session: Session | AsyncSession) -> List[CategoryDTO]:
        """Get full path from root to this category (for navigation display)."""
        breadcrumb = []
        current_id = category_id

        while current_id is not None:
            cat = await CategoryRepository.get_by_id(current_id, session)
            if cat is None:
                break
            breadcrumb.insert(0, cat)
            current_id = cat.parent_id

        return breadcrumb

    @staticmethod
    async def count_children(category_id: int, session: Session | AsyncSession) -> int:
        """Count direct children of a category."""
        stmt = select(func.count()).select_from(Category).where(Category.parent_id == category_id)
        result = await session_execute(stmt, session)
        return result.scalar() or 0

    # ==================== PAGINATION ====================

    @staticmethod
    async def get_maximum_page_roots(session: Session | AsyncSession) -> int:
        """Get max page for root categories with available items."""
        # Get all category IDs with stock in subtree
        valid_ids = await CategoryRepository._get_categories_with_stock_ids(session)

        if not valid_ids:
            return 0

        # Count valid root categories
        stmt = (
            select(func.count())
            .select_from(Category)
            .where(and_(
                Category.parent_id.is_(None),
                Category.id.in_(valid_ids)
            ))
        )
        result = await session_execute(stmt, session)
        count = result.scalar() or 0

        if count == 0:
            return 0
        if count % config.PAGE_ENTRIES == 0:
            return count // config.PAGE_ENTRIES - 1
        return math.trunc(count / config.PAGE_ENTRIES)

    @staticmethod
    async def get_maximum_page_children(parent_id: int, session: Session | AsyncSession) -> int:
        """Get max page for children of a category."""
        # Get all category IDs with stock in subtree
        valid_ids = await CategoryRepository._get_categories_with_stock_ids(session)

        if not valid_ids:
            return 0

        # Count valid children
        stmt = (
            select(func.count())
            .select_from(Category)
            .where(and_(
                Category.parent_id == parent_id,
                Category.id.in_(valid_ids)
            ))
        )
        result = await session_execute(stmt, session)
        count = result.scalar() or 0

        if count == 0:
            return 0
        if count % config.PAGE_ENTRIES == 0:
            return count // config.PAGE_ENTRIES - 1
        return math.trunc(count / config.PAGE_ENTRIES)

    @staticmethod
    async def get_maximum_page(session: Session | AsyncSession) -> int:
        """Legacy method - get max page for root categories."""
        return await CategoryRepository.get_maximum_page_roots(session)

    # ==================== ADMIN OPERATIONS ====================

    @staticmethod
    async def get_to_delete(page: int, session: Session | AsyncSession) -> List[CategoryDTO]:
        """Get categories that can be deleted (have unsold items)."""
        subquery = (
            select(Item.category_id)
            .where(Item.is_sold == False)
            .distinct()
        )
        stmt = (
            select(Category)
            .where(and_(Category.is_product == True, Category.id.in_(subquery)))
            .limit(config.PAGE_ENTRIES)
            .offset(page * config.PAGE_ENTRIES)
        )
        result = await session_execute(stmt, session)
        return [CategoryDTO.model_validate(c, from_attributes=True) for c in result.scalars().all()]

    @staticmethod
    async def get_maximum_page_to_delete(session: Session | AsyncSession) -> int:
        """Get max page for deletable categories."""
        subquery = (
            select(Item.category_id)
            .where(Item.is_sold == False)
            .distinct()
        )
        stmt = (
            select(func.count())
            .select_from(Category)
            .where(and_(Category.is_product == True, Category.id.in_(subquery)))
        )
        result = await session_execute(stmt, session)
        count = result.scalar() or 0

        if count == 0:
            return 0
        if count % config.PAGE_ENTRIES == 0:
            return count // config.PAGE_ENTRIES - 1
        return math.trunc(count / config.PAGE_ENTRIES)

    # ==================== CREATE/UPDATE OPERATIONS ====================

    @staticmethod
    async def get_or_create(
        name: str,
        parent_id: int | None,
        is_product: bool,
        price: float | None,
        description: str | None,
        session: Session | AsyncSession
    ) -> Category:
        """
        Get existing category or create new one.
        Handles race conditions via IntegrityError retry.
        """
        if parent_id is None:
            stmt = select(Category).where(
                and_(Category.name == name, Category.parent_id.is_(None))
            )
        else:
            stmt = select(Category).where(
                and_(Category.name == name, Category.parent_id == parent_id)
            )

        result = await session_execute(stmt, session)
        category = result.scalar()

        if category is None:
            try:
                category = Category(
                    name=name,
                    parent_id=parent_id,
                    is_product=is_product,
                    price=price if is_product else None,
                    description=description if is_product else None
                )
                session.add(category)
                await session_flush(session)
            except IntegrityError:
                await session.rollback()
                result = await session_execute(stmt, session)
                category = result.scalar()
                if category is None:
                    raise
        elif is_product and not category.is_product:
            category.is_product = True
            category.price = price
            category.description = description
            await session_flush(session)

        return category

    @staticmethod
    async def get_or_create_path(
        path: List[str],
        is_last_product: bool,
        price: float | None,
        description: str | None,
        session: Session | AsyncSession
    ) -> Category:
        """
        Get or create a full category path.
        Example: path=["Tea", "Green", "Tea Widow"]
        """
        parent_id = None
        category = None

        for i, name in enumerate(path):
            is_last = (i == len(path) - 1)
            is_product = is_last and is_last_product

            category = await CategoryRepository.get_or_create(
                name=name,
                parent_id=parent_id,
                is_product=is_product,
                price=price if is_product else None,
                description=description if is_product else None,
                session=session
            )
            parent_id = category.id

        return category

    @staticmethod
    async def update_description(category_id: int, description: str, session: Session | AsyncSession):
        """Update product description."""
        stmt = update(Category).where(Category.id == category_id).values(description=description)
        await session_execute(stmt, session)

    @staticmethod
    async def update_price(category_id: int, price: float, session: Session | AsyncSession):
        """Update product price."""
        stmt = update(Category).where(Category.id == category_id).values(price=price)
        await session_execute(stmt, session)

    @staticmethod
    async def update_image(category_id: int, image_file_id: str, session: Session | AsyncSession):
        """Update product image."""
        stmt = update(Category).where(Category.id == category_id).values(image_file_id=image_file_id)
        await session_execute(stmt, session)

    @staticmethod
    async def exists_at_level(name: str, parent_id: int | None, session: Session | AsyncSession) -> bool:
        """Check if a category with this name exists at this level."""
        if parent_id is None:
            stmt = select(Category).where(
                and_(Category.name == name, Category.parent_id.is_(None))
            )
        else:
            stmt = select(Category).where(
                and_(Category.name == name, Category.parent_id == parent_id)
            )
        result = await session_execute(stmt, session)
        return result.scalar() is not None

    @staticmethod
    async def create_category(
        name: str,
        parent_id: int | None,
        is_product: bool,
        price: float | None,
        description: str | None,
        session: Session | AsyncSession
    ) -> Category:
        """Create a new category."""
        category = Category(
            name=name,
            parent_id=parent_id,
            is_product=is_product,
            price=price if is_product else None,
            description=description if is_product else None
        )
        session.add(category)
        await session_flush(session)
        return category
