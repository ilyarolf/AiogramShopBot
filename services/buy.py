from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from models.buy import BuyDTO
from models.user import UserDTO
from repositories.buy import BuyRepository
from repositories.item import ItemRepository
from repositories.user import UserRepository
from services.message import MessageService
from services.notification import NotificationService
from utils.localizator import Localizator


class BuyService:

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
    async def get_purchase(callback: CallbackQuery) -> tuple[str, InlineKeyboardBuilder]:
        unpacked_cb = MyProfileCallback.unpack(callback.data)
        items = await ItemRepository.get_by_buy_id(unpacked_cb.args_for_action)
        msg = MessageService.create_message_with_bought_items(items)
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(unpacked_cb.get_back_button())
        return msg, kb_builder
