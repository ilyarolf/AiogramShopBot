import io
import re
from datetime import datetime, timezone
import qrcode
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputMediaPhoto, BufferedInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

import config
from callbacks import MyProfileCallback
from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from enums.payment import PaymentType
from handlers.user.constants import UserStates
from models.payment import ProcessingPaymentDTO
from repositories.payment import PaymentRepository
from repositories.user import UserRepository
from utils.utils import get_text, get_bot_photo_id


class PaymentService:
    AMOUNT_RE = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d{1,2})?$")

    @staticmethod
    def __create_qr_code(payment_dto: ProcessingPaymentDTO):
        qr = qrcode.QRCode()
        if payment_dto.cryptoCurrency == Cryptocurrency.BNB:
            qr_data = payment_dto.address
        elif payment_dto.paymentType == PaymentType.PAYMENT:
            qr_data = f"{payment_dto.cryptoCurrency.get_coingecko_name()}:{payment_dto.address}?amount={payment_dto.cryptoAmount}&value={payment_dto.cryptoAmount}"
        else:
            qr_data = f"{payment_dto.cryptoCurrency.get_coingecko_name()}:{payment_dto.address}"
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image()
        buffer = io.BytesIO()
        img.save(buffer)
        buffer.seek(0)
        return BufferedInputFile(
            file=buffer.getvalue(),
            filename=f"{payment_dto.address}.png"
        )

    @staticmethod
    async def __create_invoice(payment_dto: ProcessingPaymentDTO) -> ProcessingPaymentDTO:
        headers = {
            "X-Api-Key": config.KRYPTO_EXPRESS_API_KEY,
            "Content-Type": "application/json"
        }
        payment_dto = await CryptoApiWrapper.fetch_api_request(
            f"{config.KRYPTO_EXPRESS_API_URL}/payment",
            method="POST",
            data=payment_dto.model_dump_json(exclude_none=True),
            headers=headers
        )
        payment_dto = ProcessingPaymentDTO.model_validate(payment_dto, from_attributes=True)
        return payment_dto

    @staticmethod
    def __request_fiat_amount(kb_builder: InlineKeyboardBuilder, language: Language):
        kb_builder.button(
            text=get_text(language, BotEntity.COMMON, "back_button"),
            callback_data=MyProfileCallback.create(level=1)
        )
        bot_photo_id = get_bot_photo_id()
        caption = get_text(language, BotEntity.USER, "top_up_balance_request_fiat").format(
            currency_text=config.CURRENCY.get_localized_text()
        )
        media = InputMediaPhoto(media=bot_photo_id, caption=caption)
        return media, kb_builder

    @staticmethod
    async def create(callback: CallbackQuery | Message,
                     callback_data: MyProfileCallback | None,
                     state: FSMContext,
                     session: AsyncSession,
                     language: Language) -> tuple[InputMediaPhoto | str, InlineKeyboardBuilder]:
        user = await UserRepository.get_by_tgid(callback.from_user.id, session)
        unexpired_payments_count = await PaymentRepository.get_unexpired_unpaid_payments(user.id, session)
        state_data = await state.get_data()
        current_state = await state.get_state()
        if callback_data is None:
            cryptocurrency = Cryptocurrency(state_data.get('cryptocurrency'))
        else:
            cryptocurrency = callback_data.cryptocurrency
        kb_builder = InlineKeyboardBuilder()
        if unexpired_payments_count >= 15:
            kb_builder.row(callback_data.get_back_button(language))
            return get_text(language, BotEntity.USER, "too_many_payment_request"), kb_builder
        elif cryptocurrency in Cryptocurrency.get_stablecoins() and current_state is None:
            await state.set_state(UserStates.top_up_amount)
            await state.update_data(cryptocurrency=cryptocurrency.value)
            return PaymentService.__request_fiat_amount(kb_builder, language)
        elif cryptocurrency in Cryptocurrency.get_stablecoins() and current_state == UserStates.top_up_amount:
            message: Message = callback
            fiat_amount = message.html_text
            if PaymentService.AMOUNT_RE.fullmatch(fiat_amount):
                fiat_amount = float(fiat_amount)
                if 5 <= fiat_amount < 1_000_000:
                    await state.set_state()
                    payment_dto = ProcessingPaymentDTO(
                        paymentType=PaymentType.PAYMENT,
                        fiatCurrency=config.CURRENCY,
                        cryptoCurrency=cryptocurrency,
                        fiatAmount=fiat_amount
                    )
                    message = await message.answer(text=get_text(language, BotEntity.USER, "loading"))
                    await state.update_data(msg_id=message.message_id, chat_id=message.chat.id)
                    payment_dto = await PaymentService.__create_invoice(payment_dto)
                    await PaymentRepository.create(payment_dto.id, user.id, message.message_id, session)
                    await session_commit(session)
                    timestamp_s = payment_dto.expireDatetime / 1000
                    dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                    formatted = dt.strftime('%H:%M UTC on %B %d, %Y')
                    caption = get_text(language, BotEntity.USER, "top_up_balance_payment_msg").format(
                        crypto_name=payment_dto.cryptoCurrency.name,
                        addr=payment_dto.address,
                        crypto_amount=payment_dto.cryptoAmount,
                        fiat_amount=payment_dto.fiatAmount,
                        currency_text=config.CURRENCY.get_localized_text(),
                        status=get_text(language, BotEntity.USER, "status_pending"),
                        payment_lifetime=formatted
                    )
                    qr_code_file = PaymentService.__create_qr_code(payment_dto)
                    return InputMediaPhoto(media=qr_code_file, caption=caption), kb_builder
                else:
                    return PaymentService.__request_fiat_amount(kb_builder, language)
            else:
                return PaymentService.__request_fiat_amount(kb_builder, language)
        else:
            message = await callback.message.edit_caption(caption=get_text(language, BotEntity.USER, "loading"))
            payment_dto = ProcessingPaymentDTO(
                paymentType=PaymentType.DEPOSIT,
                fiatCurrency=config.CURRENCY,
                cryptoCurrency=cryptocurrency
            )
            payment_dto = await PaymentService.__create_invoice(payment_dto)
            await PaymentRepository.create(payment_dto.id, user.id, message.message_id, session)
            await session_commit(session)
            timestamp_s = payment_dto.expireDatetime / 1000
            dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
            formatted = dt.strftime('%H:%M UTC on %B %d, %Y')
            caption = get_text(language, BotEntity.USER, "top_up_balance_deposit_msg").format(
                crypto_name=payment_dto.cryptoCurrency.name,
                addr=payment_dto.address,
                currency_text=config.CURRENCY.get_localized_text(),
                status=get_text(language, BotEntity.USER, "status_pending"),
                payment_lifetime=formatted
            )
            qr_code_file = PaymentService.__create_qr_code(payment_dto)
            return InputMediaPhoto(media=qr_code_file, caption=caption), kb_builder
