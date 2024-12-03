from json import load
from pathlib import Path
from callbacks import AddType
from enums.bot_entity import BotEntity
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.localizator import Localizator


class ItemService:

    @staticmethod
    async def get_new() -> list[ItemDTO]:
        return await ItemRepository.get_new()

    @staticmethod
    async def get_in_stock_items():
        return await ItemRepository.get_in_stock()

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
