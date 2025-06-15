import datetime
import hashlib
import hmac
import re

from fastapi import APIRouter, Request, HTTPException

import config
from db import get_db_session, session_commit
from models.deposit import DepositDTO
from models.payment import ProcessingPaymentDTO
from repositories.deposit import DepositRepository
from repositories.payment import PaymentRepository
from repositories.user import UserRepository
from services.notification import NotificationService

processing_router = APIRouter(prefix=f"{config.WEBHOOK_PATH}cryptoprocessing")


def __security_check(x_signature_header: str | None, payload: bytes):
    if x_signature_header is None:
        return True
    else:
        secret_key = config.KRYPTO_EXPRESS_API_SECRET.encode("utf-8")
        hmac_sha512 = hmac.new(secret_key, re.sub(rb'\s+', b'', payload), hashlib.sha512)
        generated_signature = hmac_sha512.hexdigest()
        return hmac.compare_digest(generated_signature, x_signature_header)


@processing_router.post("/event")
async def fetch_crypto_event(payment_dto: ProcessingPaymentDTO, request: Request):
    request_body = await request.body()
    print(f"EVENT RECEIVED:{request_body}")
    is_security_pass = __security_check(request.headers.get("X-Signature"), request_body)
    if is_security_pass is False:
        raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        async with get_db_session() as session:
            user = await PaymentRepository.get_user_by_payment_id(payment_dto.id, session)
            table_payment_dto = await PaymentRepository.get_by_processing_payment_id(payment_dto.id, session)
            if payment_dto.isPaid is True and table_payment_dto.is_paid is False:
                user.top_up_amount += payment_dto.fiatAmount
                await UserRepository.update(user, session)
                table_payment_dto.is_paid = True
                await PaymentRepository.update(table_payment_dto, session)
                await DepositRepository.create(DepositDTO(
                    user_id=user.id,
                    network=payment_dto.cryptoCurrency,
                    amount=int(payment_dto.cryptoAmount*pow(10, payment_dto.cryptoCurrency.get_divider())),
                    deposit_datetime=datetime.datetime.now()
                ), session)
                await session_commit(session)
                await NotificationService.new_deposit(payment_dto, user, table_payment_dto)
            elif payment_dto.isPaid is False:
                await NotificationService.payment_expired(user, payment_dto, table_payment_dto)
            else:
                pass
            return "200"
