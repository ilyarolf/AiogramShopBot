import io
import qrcode
from aiogram.types import Message, InputMediaPhoto, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

import config
from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from db import session_commit
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.payment import PaymentType
from models.payment import ProcessingPaymentDTO
from repositories.payment import PaymentRepository
from repositories.user import UserRepository
from utils.localizator import Localizator


class PaymentService:
    @staticmethod
    async def create(cryptocurrency: Cryptocurrency,
                     message: Message,
                     session: AsyncSession) -> InputMediaPhoto | str:
        user = await UserRepository.get_by_tgid(message.chat.id, session)
        unexpired_payments_count = await PaymentRepository.get_unexpired_unpaid_payments(user.id, session)
        if unexpired_payments_count >= 5:
            return Localizator.get_text(BotEntity.USER, "too_many_payment_request")
        else:
            payment_dto = ProcessingPaymentDTO(
                paymentType=PaymentType.DEPOSIT,
                fiatCurrency=config.CURRENCY,
                cryptoCurrency=cryptocurrency
            )
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
            if payment_dto:
                await PaymentRepository.create(payment_dto.id, user.id, message.message_id, session)
                await session_commit(session)
                caption = Localizator.get_text(BotEntity.USER, "top_up_balance_msg").format(
                    crypto_name=payment_dto.cryptoCurrency.name,
                    addr=payment_dto.address,
                    crypto_amount=payment_dto.cryptoAmount,
                    fiat_amount=payment_dto.fiatAmount,
                    currency_text=config.CURRENCY.get_localized_text(),
                    status=Localizator.get_text(BotEntity.USER, "status_pending")
                )
                qr = qrcode.QRCode()
                qr.add_data(f"{payment_dto.cryptoCurrency.get_coingecko_name()}:{payment_dto.address}")
                qr.make(fit=True)
                img = qr.make_image()
                buffer = io.BytesIO()
                img.save(buffer)
                buffer.seek(0)
                qr_code_file = BufferedInputFile(
                    file=buffer.getvalue(),
                    filename=f"{payment_dto.address}.png"
                )
                return InputMediaPhoto(media=qr_code_file, caption=caption)
