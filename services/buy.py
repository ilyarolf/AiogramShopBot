from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from callbacks import MyProfileCallback
from db import session_commit
from enums.bot_entity import BotEntity
from models.buy import BuyDTO
from repositories.buy import BuyRepository
from repositories.category import CategoryRepository
from repositories.item import ItemRepository
from repositories.subcategory import SubcategoryRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from utils.localizator import Localizator


class BuyService:

    @staticmethod
    async def refund(buy_dto: BuyDTO, session: AsyncSession | Session) -> str:
        refund_data = await BuyRepository.get_refund_data_single(buy_dto.id, session)
        buy = await BuyRepository.get_by_id(buy_dto.id, session)
        buy.is_refunded = True
        await BuyRepository.update(buy, session)
        user = await UserRepository.get_by_tgid(refund_data.telegram_id, session)
        user.consume_records = user.consume_records - refund_data.total_price
        await UserRepository.update(user, session)
        await session_commit(session)
        await NotificationService.refund(refund_data)
        if refund_data.telegram_username:
            return Localizator.get_text(BotEntity.ADMIN, "successfully_refunded_with_username").format(
                total_price=refund_data.total_price,
                telegram_username=refund_data.telegram_username,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                currency_sym=Localizator.get_currency_symbol())
        else:
            return Localizator.get_text(BotEntity.ADMIN, "successfully_refunded_with_tgid").format(
                total_price=refund_data.total_price,
                telegram_id=refund_data.telegram_id,
                quantity=refund_data.quantity,
                subcategory=refund_data.subcategory_name,
                currency_sym=Localizator.get_currency_symbol())

    @staticmethod
    async def get_purchase(callback_data: MyProfileCallback,
                           session: AsyncSession) -> tuple[str, InlineKeyboardBuilder]:
        buy = await BuyRepository.get_by_id(callback_data.buy_id, session)
        items = await ItemRepository.get_by_buy_id(callback_data.buy_id, session)
        purchased_items_msg = MessageService.create_message_with_bought_items(items)
        category = await CategoryRepository.get_by_id(items[0].category_id, session)
        subcategory = await SubcategoryRepository.get_by_id(items[0].subcategory_id, session)
        us_datetime_12h = buy.buy_datetime.strftime("%m/%d/%Y, %I:%M %p")
        msg = Localizator.get_text(BotEntity.USER, "purchase_details").format(
            category_name=category.name,
            subcategory_name=subcategory.name,
            currency_sym=Localizator.get_currency_symbol(),
            total_fiat_price=items[0].price*len(items),
            fiat_price=items[0].price,
            qty=len(items),
            purchase_datetime=us_datetime_12h,
            purchased_items=purchased_items_msg
        )
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(callback_data.get_back_button())
        return msg, kb_builder
