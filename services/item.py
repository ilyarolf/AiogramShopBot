from json import load
from pathlib import Path
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from callbacks import AddType
from db import session_commit
from enums.bot_entity import BotEntity
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from utils.localizator import Localizator


class ItemService:
    """
    Service for item management including import with backwards compatibility.

    Supports two import formats:
    1. NEW FORMAT (path-based):
       - JSON: {"path": ["Tea", "Green", "Tea Widow"], "price": 50, "description": "...", "private_data": "..."}
       - TXT: Tea|Green|Tea Widow;50.0;Description;private_data

    2. LEGACY FORMAT (category/subcategory - for backwards compatibility):
       - JSON: {"category": "Tea", "subcategory": "Tea Widow", "price": 50, "description": "...", "private_data": "..."}
       - TXT: CATEGORY;SUBCATEGORY;DESCRIPTION;PRICE;PRIVATE_DATA
    """

    @staticmethod
    async def get_new(session: AsyncSession | Session) -> list[ItemDTO]:
        return await ItemRepository.get_new(session)

    @staticmethod
    async def get_in_stock_items(session: AsyncSession | Session):
        return await ItemRepository.get_in_stock(session)

    @staticmethod
    async def parse_items_json(path_to_file: str, session: AsyncSession | Session) -> List[ItemDTO]:
        """
        Parse JSON file with items.

        Supports both new path-based format and legacy category/subcategory format.
        """
        with open(path_to_file, 'r', encoding='utf-8') as file:
            items = load(file)
            items_list = []

            for item in items:
                # Detect format
                if 'path' in item:
                    # NEW FORMAT: path-based
                    path = item['path']
                    if isinstance(path, str):
                        # Handle pipe-separated string: "Tea|Green|Tea Widow"
                        path = [p.strip() for p in path.split('|')]

                    price = item.get('price')
                    description = item.get('description')
                    private_data = item.get('private_data', '')

                    # Create category path (last element is product)
                    product_category = await CategoryRepository.get_or_create_path(
                        path=path,
                        is_last_product=True,
                        price=price,
                        description=description,
                        session=session
                    )

                    items_list.append(ItemDTO(
                        category_id=product_category.id,
                        private_data=private_data
                    ))

                elif 'category' in item and 'subcategory' in item:
                    # LEGACY FORMAT: category/subcategory (backwards compatibility)
                    category_name = item['category']
                    subcategory_name = item['subcategory']
                    price = item.get('price')
                    description = item.get('description')
                    private_data = item.get('private_data', '')

                    # Convert to path: [category, subcategory]
                    path = [category_name, subcategory_name]

                    product_category = await CategoryRepository.get_or_create_path(
                        path=path,
                        is_last_product=True,
                        price=price,
                        description=description,
                        session=session
                    )

                    items_list.append(ItemDTO(
                        category_id=product_category.id,
                        private_data=private_data
                    ))

                else:
                    raise ValueError(f"Invalid item format. Expected 'path' or 'category'/'subcategory' keys: {item}")

            return items_list

    @staticmethod
    async def parse_items_txt(path_to_file: str, session: AsyncSession | Session) -> List[ItemDTO]:
        """
        Parse TXT file with items.

        Supports both formats:
        - NEW: Tea|Green|Tea Widow;50.0;Description;private_data
        - LEGACY: CATEGORY;SUBCATEGORY;DESCRIPTION;PRICE;PRIVATE_DATA
        """
        with open(path_to_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            items_list = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(';')

                if len(parts) == 4:
                    # NEW FORMAT: path;price;description;private_data
                    path_str, price_str, description, private_data = parts
                    path = [p.strip() for p in path_str.split('|')]
                    price = float(price_str)

                elif len(parts) == 5:
                    # LEGACY FORMAT: category;subcategory;description;price;private_data
                    category_name, subcategory_name, description, price_str, private_data = parts
                    path = [category_name.strip(), subcategory_name.strip()]
                    price = float(price_str)

                else:
                    raise ValueError(f"Invalid line format. Expected 4 or 5 semicolon-separated values: {line}")

                product_category = await CategoryRepository.get_or_create_path(
                    path=path,
                    is_last_product=True,
                    price=price,
                    description=description.strip(),
                    session=session
                )

                items_list.append(ItemDTO(
                    category_id=product_category.id,
                    private_data=private_data.strip()
                ))

            return items_list

    @staticmethod
    async def add_items(path_to_file: str, add_type: AddType, session: AsyncSession | Session) -> str:
        try:
            items = []
            if add_type == AddType.JSON:
                items += await ItemService.parse_items_json(path_to_file, session)
            else:
                items += await ItemService.parse_items_txt(path_to_file, session)
            await ItemRepository.add_many(items, session)
            await session_commit(session)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(adding_result=len(items))
        except Exception as e:
            return Localizator.get_text(BotEntity.ADMIN, "add_items_err").format(adding_result=e)
        finally:
            Path(path_to_file).unlink(missing_ok=True)
