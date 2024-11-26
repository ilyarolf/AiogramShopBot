import math
from json import load
from pathlib import Path

from sqlalchemy import select, func, update, distinct, delete
import config
from callbacks import AddType
from db import session_execute, session_commit, get_db_session
from models.buyItem import BuyItem
from models.category import Category
from models.item import Item, ItemDTO
from models.subcategory import Subcategory
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.localizator import Localizator, BotEntity


class ItemService:

    @staticmethod
    async def get_by_primary_key(item_id: int) -> Item:
        async with get_db_session() as session:
            stmt = select(Item).where(Item.id == item_id)
            item = await session_execute(stmt, session)
            return item.scalar()

    @staticmethod
    async def get_available_quantity(subcategory_id: int, category_id: int) -> int:
        async with get_db_session() as session:
            stmt = select(func.count(Item.id)).where(Item.subcategory_id == subcategory_id,
                                                     Item.is_sold == 0, Item.category_id == category_id)
            available_quantity = await session_execute(stmt, session)
            return available_quantity.scalar()

    @staticmethod
    async def get_description(subcategory_id: int, category_id) -> str:
        async with get_db_session() as session:
            stmt = select(Item.description).where(Item.subcategory_id == subcategory_id,
                                                  Item.category_id == category_id).limit(1)
            description = await session_execute(stmt, session)
            return description.scalar()

    @staticmethod
    async def get_bought_items(category_id: int, subcategory_id: int, quantity: int):
        async with get_db_session() as session:
            stmt = select(Item).where(Item.subcategory_id == subcategory_id,
                                      Item.category_id == category_id,
                                      Item.is_sold == 0).limit(quantity)
            result = await session_execute(stmt, session)
            bought_items = result.scalars().all()
            return list(bought_items)

    @staticmethod
    async def set_items_sold(sold_items: list[Item]):
        async with get_db_session() as session:
            for item in sold_items:
                stmt = update(Item).where(Item.id == item.id).values(is_sold=1)
                await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def get_items_by_buy_id(buy_id: int) -> list:
        async with get_db_session() as session:
            stmt = (
                select(Item)
                .join(BuyItem, BuyItem.item_id == Item.id)
                .where(BuyItem.buy_id == buy_id)
            )
            result = await session_execute(stmt, session)
            items = result.scalars().all()
            return items

    @staticmethod
    async def get_unsold_subcategories_by_category(category_id: int, page) -> \
            list[Item]:
        async with get_db_session() as session:
            stmt = select(Item).join(Subcategory, Subcategory.id == Item.subcategory_id).where(
                Item.category_id == category_id, Item.is_sold == 0).group_by(Subcategory.name).limit(
                config.PAGE_ENTRIES).offset(config.PAGE_ENTRIES * page)
            subcategories = await session_execute(stmt, session)
            return subcategories.scalars().all()

    @staticmethod
    async def get_maximum_page(category_id: int):
        async with get_db_session() as session:
            subquery = select(Item.subcategory_id).where(Item.category_id == category_id, Item.is_sold == 0)
            stmt = select(func.count(distinct(subquery.c.subcategory_id)))
            maximum_page = await session_execute(stmt, session)
            maximum_page = maximum_page.scalar_one()
            if maximum_page % config.PAGE_ENTRIES == 0:
                return maximum_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(maximum_page / config.PAGE_ENTRIES)

    @staticmethod
    async def get_price_by_subcategory(subcategory_id: int, category_id: int) -> float:
        async with get_db_session() as session:
            stmt = select(Item.price).where(Item.subcategory_id == subcategory_id, Item.category_id == category_id)
            price = await session_execute(stmt, session)
            return price.scalar()

    @staticmethod
    async def set_items_not_new():
        async with get_db_session() as session:
            stmt = update(Item).where(Item.is_new == 1).values(is_new=0)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def delete_unsold_with_category_id(category_id: int):
        async with get_db_session() as session:
            stmt = delete(Item).where(Item.category_id == category_id, Item.is_sold == 0)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def delete_with_subcategory_id(subcategory_id):
        async with get_db_session() as session:
            stmt = delete(Item).where(Item.subcategory_id == subcategory_id, Item.is_sold == 0)
            await session_execute(stmt, session)
            await session_commit(session)

    @staticmethod
    async def add_many(new_items: list[Item]):
        async with get_db_session() as session:
            session.add_all(new_items)
            await session_commit(session)

    @staticmethod
    async def get_new_items() -> list[Item]:
        async with get_db_session() as session:
            stmt = select(Item).where(Item.is_new == 1)
            new_items = await session_execute(stmt, session)
            new_items = new_items.scalars().all()
            return new_items

    @staticmethod
    async def get_in_stock_items():
        async with get_db_session() as session:
            stmt = select(Item).where(Item.is_sold == 0)
            items = await session_execute(stmt, session)
            items = items.scalars().all()
            return items

    @staticmethod
    async def parse_items_json(path_to_file):
        with open(path_to_file, 'r', encoding='utf-8') as file:
            items = load(file)
            items_list = []
            for item in items:
                category = await CategoryRepository.get_or_create(item['category'])
                subcategory = await SubcategoryRepository.get_or_create(item['subcategory'])
                item.pop('category')
                item.pop('subcategory')
                items_list.append(ItemDTO(
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    **item
                ))
            return items_list

    @staticmethod
    async def parse_items_txt(path_to_file):
        with open(path_to_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            items_list = []
            for line in lines:
                category_name, subcategory_name, description, price, private_data = line.split(';')
                category = await CategoryRepository.get_or_create(category_name)
                subcategory = await SubcategoryRepository.get_or_create(subcategory_name)
                items_list.append(ItemDTO(
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    price=float(price),
                    description=description,
                    private_data=private_data
                ))
            return items_list

    @staticmethod
    async def add_items(path_to_file: str, add_type: AddType) -> str:
        try:
            items = []
            if add_type == AddType.JSON:
                items += await ItemService.parse_items_json(path_to_file)
            else:
                items += await ItemService.parse_items_txt(path_to_file)
            await ItemRepository.add_many(items)
            return Localizator.get_text(BotEntity.ADMIN, "add_items_success").format(adding_result=len(items))
        except Exception as e:
            return Localizator.get_text(BotEntity.ADMIN, "add_items_err").format(adding_result=e)
        finally:
            Path(path_to_file).unlink(missing_ok=True)
