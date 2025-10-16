from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

import config
from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from enums.payment import PaymentType
from models.invoice import InvoiceDTO
from models.payment import ProcessingPaymentDTO
from repositories.invoice import InvoiceRepository


class InvoiceService:

    @staticmethod
    async def create_invoice_with_kryptoexpress(
        order_id: int,
        fiat_amount: float,
        fiat_currency: Currency,
        crypto_currency: Cryptocurrency,
        session: AsyncSession | Session
    ) -> InvoiceDTO:
        """
        Erstellt Invoice mit KryptoExpress API

        Returns:
            InvoiceDTO mit payment_address, payment_amount_crypto, etc.
        """

        # KryptoExpress API Call
        payment_dto = ProcessingPaymentDTO(
            paymentType=PaymentType.PAYMENT,  # PAYMENT (nicht DEPOSIT!)
            fiatCurrency=fiat_currency,
            fiatAmount=fiat_amount,
            cryptoCurrency=crypto_currency
        )

        headers = {
            "X-Api-Key": config.KRYPTO_EXPRESS_API_KEY,
            "Content-Type": "application/json"
        }

        response_data = await CryptoApiWrapper.fetch_api_request(
            f"{config.KRYPTO_EXPRESS_API_URL}/payment",
            method="POST",
            data=payment_dto.model_dump_json(exclude_none=True),
            headers=headers
        )

        payment_response = ProcessingPaymentDTO.model_validate(response_data)

        # Generiere Invoice-Nummer
        invoice_number = await InvoiceRepository.get_next_invoice_number(session)

        # Erstelle Invoice
        invoice_dto = InvoiceDTO(
            order_id=order_id,
            invoice_number=invoice_number,
            payment_address=payment_response.address,
            payment_amount_crypto=payment_response.cryptoAmount,
            payment_crypto_currency=crypto_currency,
            payment_processing_id=payment_response.id,
            fiat_amount=fiat_amount,
            fiat_currency=fiat_currency
        )

        await InvoiceRepository.create(invoice_dto, session)

        return invoice_dto