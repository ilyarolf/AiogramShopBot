import pytest

from crypto_api.CryptoApiWrapper import CryptoApiWrapper
from enums.cryptocurrency import Cryptocurrency
from enums.currency import Currency
from enums.payment import PaymentType
from models.payment import ProcessingPaymentDTO


class _FakePaymentsResource:
    def __init__(self):
        self.created_payment = None
        self.created_deposit = None

    async def create_payment(self, **kwargs):
        self.created_payment = kwargs
        return type("Payment", (), {
            "id": 11,
            "payment_type": type("PaymentType", (), {"value": "PAYMENT"})(),
            "fiat_currency": type("FiatCurrency", (), {"value": "USD"})(),
            "fiat_amount": 15.0,
            "crypto_amount": 0.001,
            "crypto_currency": type("CryptoCurrency", (), {"value": "BTC"})(),
            "expire_datetime": 1,
            "create_datetime": 2,
            "address": "btc-address",
            "is_paid": False,
            "is_withdrawn": False,
            "hash": "hash",
            "callback_url": "https://example.com/callback",
        })()

    async def create_deposit(self, **kwargs):
        self.created_deposit = kwargs
        return type("Payment", (), {
            "id": 12,
            "payment_type": type("PaymentType", (), {"value": "DEPOSIT"})(),
            "fiat_currency": type("FiatCurrency", (), {"value": "USD"})(),
            "fiat_amount": None,
            "crypto_amount": None,
            "crypto_currency": type("CryptoCurrency", (), {"value": "BTC"})(),
            "expire_datetime": 1,
            "create_datetime": 2,
            "address": "btc-address",
            "is_paid": False,
            "is_withdrawn": False,
            "hash": "hash",
            "callback_url": "https://example.com/callback",
        })()


class _FakeWalletResource:
    def __init__(self):
        self.last_call = None

    async def calculate_single(self, **kwargs):
        self.last_call = ("calculate_single", kwargs)
        return type("Withdrawal", (), {
            "withdraw_type": type("WithdrawType", (), {"value": "SINGLE"})(),
            "crypto_currency": type("CryptoCurrency", (), {"value": "BTC"})(),
            "to_address": kwargs["to_address"],
            "tx_id_list": [],
            "receiving_amount": 0.9,
            "blockchain_fee_amount": 0.1,
            "service_fee_amount": 0.0,
            "only_calculate": True,
            "total_withdrawal_amount": 1.0,
            "payment_id": kwargs["payment_id"],
        })()


class _FakeClient:
    def __init__(self):
        self.payments = _FakePaymentsResource()
        self.wallet = _FakeWalletResource()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.asyncio
async def test_create_invoice_uses_sdk_payment_resource(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr("crypto_api.CryptoApiWrapper.CryptoApiWrapper._build_client", lambda: fake_client)

    payment = await CryptoApiWrapper.create_invoice(ProcessingPaymentDTO(
        paymentType=PaymentType.PAYMENT,
        fiatCurrency=Currency.USD,
        fiatAmount=15.0,
        cryptoCurrency=Cryptocurrency.BTC,
        callbackUrl="https://example.com/callback",
        callbackSecret="secret",
    ))

    assert payment.id == 11
    assert fake_client.payments.created_payment["fiat_amount"] == 15.0
    assert fake_client.payments.created_payment["crypto_currency"].value == "BTC"


@pytest.mark.asyncio
async def test_withdrawal_uses_sdk_calculate_single(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr("crypto_api.CryptoApiWrapper.CryptoApiWrapper._build_client", lambda: fake_client)

    withdrawal = await CryptoApiWrapper.withdrawal(
        cryptocurrency=Cryptocurrency.BTC,
        to_address="bc1destination",
        only_calculate=True,
        payment_id=99,
    )

    assert withdrawal.withdrawType.value == "SINGLE"
    assert fake_client.wallet.last_call[0] == "calculate_single"
    assert fake_client.wallet.last_call[1]["payment_id"] == 99
