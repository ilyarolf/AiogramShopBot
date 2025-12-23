from json import load
from pathlib import Path

from aiogram.types import InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from callbacks import AddType, AllCategoriesCallback
from db import session_commit
from enums.announcement_type import AnnouncementType
from enums.bot_entity import BotEntity
from enums.item_type import ItemType
from enums.language import Language
from models.item import ItemDTO
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from utils.utils import get_text, get_bot_photo_id


class ItemService:

    @staticmethod
    async def create_announcement_message(announcement_type: AnnouncementType,
                                          session: AsyncSession,
                                          language: Language):
        if announcement_type == AnnouncementType.CURRENT_STOCK:
            items = await ItemRepository.get_in_stock(session)
            header = get_text(language, BotEntity.ADMIN, "current_stock_header")
        else:
            items = await ItemRepository.get_new(session)
            header = get_text(language, BotEntity.ADMIN, "restocking_message_header")
        filtered_items = {}
        for item in items:
            category = await CategoryRepository.get_by_id(item.category_id, session)
            subcategory = await SubcategoryRepository.get_by_id(item.subcategory_id, session)
            if category.name not in filtered_items:
                filtered_items[category.name] = {}
            if subcategory.name not in filtered_items[category.name]:
                filtered_items[category.name][subcategory.name] = []
            filtered_items[category.name][subcategory.name].append(item)
        message = header
        for category, subcategory_item_dict in filtered_items.items():
            message += get_text(language, BotEntity.ADMIN, "restocking_message_category").format(
                category=category)
            for subcategory, item in subcategory_item_dict.items():
                message += get_text(language, BotEntity.USER, "subcategory_button").format(
                    subcategory_name=subcategory,
                    available_quantity=len(item),
                    subcategory_price=item[0].price,
                    currency_sym=config.CURRENCY.get_localized_symbol()) + "\n"
        message = f"<b>{message}</b>"
        return message

    @staticmethod
    async def parse_items_json(path_to_file: str, session: AsyncSession | Session):
        with open(path_to_file, 'r', encoding='utf-8') as file:
            items = load(file)
            items_list = []
            for item in items:
                item_type = ItemType(item['item_type'].upper())
                category = await CategoryRepository.get_or_create(item['category'], session)
                subcategory = await SubcategoryRepository.get_or_create(item['subcategory'], session)
                item.pop('item_type')
                item.pop('category')
                item.pop('subcategory')
                if item_type == ItemType.PHYSICAL:
                    item.pop('private_data')
                items_list.append(ItemDTO(
                    item_type=item_type,
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    **item
                ))
            return items_list

    @staticmethod
    async def parse_items_txt(path_to_file: str, session: AsyncSession | Session):
        with open(path_to_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            items_list = []
            for line in lines:
                item_type, category_name, subcategory_name, description, price, private_data = line.split(';')
                item_type = ItemType(item_type.upper())
                if item_type == ItemType.PHYSICAL:
                    private_data = None
                category = await CategoryRepository.get_or_create(category_name, session)
                subcategory = await SubcategoryRepository.get_or_create(subcategory_name, session)
                items_list.append(ItemDTO(
                    item_type=item_type,
                    category_id=category.id,
                    subcategory_id=subcategory.id,
                    price=float(price),
                    description=description,
                    private_data=private_data
                ))
            return items_list

    @staticmethod
    async def add_items(path_to_file: str,
                        add_type: AddType,
                        session: AsyncSession | Session,
                        language: Language) -> str:
        try:
            items = []
            if add_type == AddType.JSON:
                items += await ItemService.parse_items_json(path_to_file, session)
            else:
                items += await ItemService.parse_items_txt(path_to_file, session)
            await ItemRepository.add_many(items, session)
            await session_commit(session)
            return get_text(language, BotEntity.ADMIN, "add_items_success").format(adding_result=len(items))
        except Exception as e:
            return get_text(language, BotEntity.ADMIN, "add_items_err").format(adding_result=e)
        finally:
            Path(path_to_file).unlink(missing_ok=True)

    @staticmethod
    async def get_all_types(callback_data: AllCategoriesCallback,
                            session: AsyncSession,
                            language: Language) -> tuple[InputMediaPhoto, InlineKeyboardBuilder]:
        callback_data = callback_data or AllCategoriesCallback.create(0)
        kb_builder = InlineKeyboardBuilder()
        available_item_types = await ItemRepository.get_available_item_types(session)
        for item_type in available_item_types:
            kb_builder.button(
                text=item_type.get_localized(language),
                callback_data=callback_data.model_copy(update={"level": callback_data.level + 1,
                                                               "item_type": item_type})
            )
        kb_builder.button(
            text=get_text(language, BotEntity.USER, "pick_all_item_types"),
            callback_data=callback_data.model_copy(update={"level": callback_data.level + 1,
                                                           "item_type": None})
        )
        kb_builder.adjust(1)
        caption = get_text(language, BotEntity.USER, "pick_item_type")
        bot_photo_id = get_bot_photo_id()
        return InputMediaPhoto(media=bot_photo_id, caption=caption), kb_builder
