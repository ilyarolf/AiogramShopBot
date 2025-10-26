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

        # Check if API keys are configured (not placeholders)
        use_mock = (
            not config.KRYPTO_EXPRESS_API_KEY or
            config.KRYPTO_EXPRESS_API_KEY.startswith("${") or
            config.KRYPTO_EXPRESS_API_KEY == ""
        )

        if use_mock:
            # MOCK MODE: Generate fake payment data for testing
            payment_response = InvoiceService._generate_mock_payment_response(
                fiat_amount, fiat_currency, crypto_currency
            )
        else:
            # REAL API MODE: Call KryptoExpress
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

    @staticmethod
    async def create_wallet_only_invoice(
        order_id: int,
        fiat_amount: float,
        fiat_currency: Currency,
        session: AsyncSession | Session
    ) -> InvoiceDTO:
        """
        Creates invoice for wallet-only orders (no crypto payment needed).
        Invoice is created for tracking/reference purposes only.

        Args:
            order_id: Order ID
            fiat_amount: Total amount paid (from wallet)
            fiat_currency: Currency (EUR)
            session: DB session

        Returns:
            InvoiceDTO with invoice_number but no payment details
        """
        # Generate invoice number
        invoice_number = await InvoiceRepository.get_next_invoice_number(session)

        # Create invoice without payment details (wallet-only)
        invoice_dto = InvoiceDTO(
            order_id=order_id,
            invoice_number=invoice_number,
            payment_address=None,  # No crypto payment
            payment_amount_crypto=None,
            payment_crypto_currency=None,
            payment_processing_id=None,
            fiat_amount=fiat_amount,
            fiat_currency=fiat_currency
        )

        await InvoiceRepository.create(invoice_dto, session)

        return invoice_dto

    @staticmethod
    def _generate_mock_payment_response(
        fiat_amount: float,
        fiat_currency: Currency,
        crypto_currency: Cryptocurrency
    ) -> ProcessingPaymentDTO:
        """
        Generiert Mock-Payment-Response für Testing ohne echte API.

        Returns fake but realistic payment data based on crypto type.
        """
        import random

        # Mock crypto amounts (simplified conversion rates)
        crypto_rates = {
            Cryptocurrency.BTC: 50000,
            Cryptocurrency.ETH: 3000,
            Cryptocurrency.LTC: 100,
            Cryptocurrency.SOL: 150,
            Cryptocurrency.BNB: 400,
            Cryptocurrency.USDT_TRC20: 1,
            Cryptocurrency.USDT_ERC20: 1,
            Cryptocurrency.USDC_ERC20: 1,
        }

        rate = crypto_rates.get(crypto_currency, 1000)
        crypto_amount = fiat_amount / rate

        # Generate fake addresses based on crypto type
        mock_addresses = {
            Cryptocurrency.BTC: f"bc1qmock{random.randint(100000, 999999)}test{random.randint(10, 99)}",
            Cryptocurrency.ETH: f"0xMOCK{random.randint(100000, 999999):06x}TEST{random.randint(1000, 9999):04x}",
            Cryptocurrency.LTC: f"ltc1qmock{random.randint(100000, 999999)}test{random.randint(10, 99)}",
            Cryptocurrency.SOL: f"MOCK{random.randint(10000000, 99999999)}TEST{random.randint(1000, 9999)}Sol",
            Cryptocurrency.BNB: f"0xMOCK{random.randint(100000, 999999):06x}BNB{random.randint(1000, 9999):04x}",
            Cryptocurrency.USDT_TRC20: f"TMOCK{random.randint(10000000, 99999999)}TRC20{random.randint(100, 999)}",
            Cryptocurrency.USDT_ERC20: f"0xMOCK{random.randint(100000, 999999):06x}USDT{random.randint(1000, 9999):04x}",
            Cryptocurrency.USDC_ERC20: f"0xMOCK{random.randint(100000, 999999):06x}USDC{random.randint(1000, 9999):04x}",
        }

        mock_address = mock_addresses.get(
            crypto_currency,
            f"MOCK_{crypto_currency.value}_{random.randint(100000, 999999)}"
        )

        # Create mock payment response
        return ProcessingPaymentDTO(
            id=random.randint(100000, 999999),  # Fake payment ID
            address=mock_address,
            cryptoAmount=round(crypto_amount, 8),
            cryptoCurrency=crypto_currency,
            fiatAmount=fiat_amount,
            fiatCurrency=fiat_currency,
            paymentType=PaymentType.PAYMENT
        )

    @staticmethod
    async def create_partial_payment_invoice(
        order_id: int,
        parent_invoice_id: int,
        remaining_crypto_amount: float,
        remaining_fiat_amount: float,
        crypto_currency: Cryptocurrency,
        fiat_currency: Currency,
        payment_attempt: int,
        session: AsyncSession | Session
    ) -> InvoiceDTO:
        """
        Creates a partial payment invoice for underpayment retry.

        Called after first underpayment to create a new invoice for
        the remaining amount.

        Args:
            order_id: Order ID
            parent_invoice_id: ID of original invoice
            remaining_crypto_amount: Remaining amount in crypto
            remaining_fiat_amount: Remaining amount in fiat
            crypto_currency: Cryptocurrency
            fiat_currency: Fiat currency
            payment_attempt: Payment attempt (1 or 2)
            session: Database session

        Returns:
            InvoiceDTO with new payment address for remaining amount
        """
        import logging

        logging.info(f"📋 Creating partial payment invoice for order {order_id}")
        logging.info(f"   Remaining: {remaining_crypto_amount} {crypto_currency.value} (€{remaining_fiat_amount:.2f})")
        logging.info(f"   Payment attempt: {payment_attempt}")

        # Check if API keys are configured
        use_mock = (
            not config.KRYPTO_EXPRESS_API_KEY or
            config.KRYPTO_EXPRESS_API_KEY.startswith("${") or
            config.KRYPTO_EXPRESS_API_KEY == ""
        )

        if use_mock:
            # MOCK MODE: Generate fake payment data
            payment_response = InvoiceService._generate_mock_payment_response(
                remaining_fiat_amount, fiat_currency, crypto_currency
            )
        else:
            # REAL API MODE: Call KryptoExpress for new payment
            payment_dto = ProcessingPaymentDTO(
                paymentType=PaymentType.PAYMENT,
                fiatCurrency=fiat_currency,
                fiatAmount=remaining_fiat_amount,
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

        # Generate new invoice number
        invoice_number = await InvoiceRepository.get_next_invoice_number(session)

        # Create partial payment invoice
        invoice_dto = InvoiceDTO(
            order_id=order_id,
            invoice_number=invoice_number,
            payment_address=payment_response.address,
            payment_amount_crypto=remaining_crypto_amount,  # Use calculated remaining amount
            payment_crypto_currency=crypto_currency,
            payment_processing_id=payment_response.id,
            fiat_amount=remaining_fiat_amount,
            fiat_currency=fiat_currency,
            is_partial_payment=1,  # 1 = first partial payment
            parent_invoice_id=parent_invoice_id,
            payment_attempt=payment_attempt
        )

        await InvoiceRepository.create(invoice_dto, session)

        logging.info(f"✅ Created partial invoice {invoice_number} (Payment ID: {payment_response.id})")
        logging.info(f"   New payment address: {payment_response.address}")

        return invoice_dto