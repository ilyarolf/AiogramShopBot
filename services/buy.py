import datetime
import math

from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
import config
from callbacks import MyProfileCallback
from db import session_execute, session_commit, session_refresh, get_db_session
from enums.bot_entity import BotEntity
from models.buy import Buy, BuyDTO
from models.user import User, UserDTO
from repositories.buy import BuyRepository
from repositories.item import ItemRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from utils.localizator import Localizator


class BuyService:

    @staticmethod
    async def get_buys_by_buyer_id(buyer_id: int, page: int):
        async with get_db_session() as session:
            stmt = select(Buy).where(Buy.buyer_id == buyer_id).limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES)
            buys = await session_execute(stmt, session)
            return buys.scalars().all()

    @staticmethod
    async def get_max_page_purchase_history(buyer_id: int):
        async with get_db_session() as session:
            stmt = select(func.count(Buy.id)).where(Buy.buyer_id == buyer_id)
            max_page = await session_execute(stmt, session)
            max_page = max_page.scalar_one()
            if max_page % config.PAGE_ENTRIES == 0:
                return max_page / config.PAGE_ENTRIES - 1
            else:
                return math.trunc(max_page / config.PAGE_ENTRIES)

    @staticmethod
    async def insert_new(user: User, quantity: int, total_price: float) -> int:
        async with get_db_session() as session:
            new_buy = Buy(buyer_id=user.id, quantity=quantity, total_price=total_price)
            session.add(new_buy)
            await session_commit(session)
            await session_refresh(session, new_buy)
            return new_buy.id

    @staticmethod
    async def get_not_refunded_buy_ids(page: int):
        async with get_db_session() as session:
            stmt = select(Buy.id).where(Buy.is_refunded == 0).limit(config.PAGE_ENTRIES).offset(
                page * config.PAGE_ENTRIES)
            not_refunded_buys = await session_execute(stmt, session)
            return not_refunded_buys.scalars().all()

    @staticmethod
    async def refund(buy_dto: BuyDTO) -> str:
        refund_data = await BuyRepository.get_refund_data_single(buy_dto.id)
        buy = await BuyRepository.get_by_id(buy_dto.id)
        buy.is_refunded = True
        await BuyRepository.update(buy)
        user = await UserRepository.get_by_tgid(UserDTO(telegram_id=refund_data.telegram_id))
        user.consume_records = user.consume_records - refund_data.total_price
        await UserRepository.update(user)
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
    async def get_new_buys_by_timedelta(timedelta_int):
        async with get_db_session() as session:
            current_time = datetime.datetime.now()
            one_day_interval = datetime.timedelta(days=int(timedelta_int))
            time_to_subtract = current_time - one_day_interval
            stmt = select(Buy).where(Buy.buy_datetime >= time_to_subtract)
            buys = await session_execute(stmt, session)
            return buys.scalars().all()

    @staticmethod
    async def get_purchase(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        items = await ItemRepository.get_by_buy_id(unpacked_cb.args_for_action)
        msg = MessageService.create_message_with_bought_items(items)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(unpacked_cb.get_back_button())
        return msg, kb_builder
