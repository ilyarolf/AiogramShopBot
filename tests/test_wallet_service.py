import pytest

from callbacks import MyProfileCallback
from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from services.user import UserService
from services.wallet import WalletService
from utils.utils import get_text


class _State:
    def __init__(self):
        self.cleared = False

    async def clear(self):
        self.cleared = True

    async def get_data(self):
        return {"cryptocurrency": Cryptocurrency.BTC.value}

    async def update_data(self, **kwargs):
        return None


class _Message:
    def __init__(self, text: str):
        self.text = text


@pytest.mark.asyncio
async def test_wallet_cancel_uses_localized_text():
    state = _State()
    message = _Message(get_text(Language.EN, BotEntity.COMMON, "cancel"))

    text, _ = await WalletService.calculate_withdrawal(message, state, Language.EN)

    assert state.cleared is True
    assert "Cancelled" in text


def test_wallet_validates_new_currency_addresses():
    assert WalletService.validate_withdrawal_address("D8BFXqDM7MHf3A4j3kC8wWEN8DqRLVQjax", Cryptocurrency.DOGE)


def test_wallet_rejects_empty_address_without_exception():
    assert WalletService.validate_withdrawal_address(None, Cryptocurrency.BTC) is False
    assert WalletService.validate_withdrawal_address("", Cryptocurrency.BTC) is False


@pytest.mark.asyncio
async def test_top_up_buttons_include_supported_currencies():
    _, keyboard = await UserService.get_top_up_buttons(
        MyProfileCallback.create(level=1),
        Language.EN
    )

    button_texts = [
        button.text
        for row in keyboard.as_markup().inline_keyboard
        for button in row
        if getattr(button, "text", None)
    ]

    assert "₿ BTC" in button_texts
    assert "USDT ERC-20" in button_texts


@pytest.mark.asyncio
async def test_admin_withdraw_menu_shows_supported_currencies(monkeypatch):
    async def _fake_wallet_balance():
        return {
            Cryptocurrency.BTC: 1.25,
            Cryptocurrency.USDT_ERC20: 20,
        }

    monkeypatch.setattr(
        "services.wallet.CryptoApiWrapper.get_wallet_balance",
        _fake_wallet_balance
    )

    text, keyboard = await WalletService.get_withdraw_menu(Language.EN)
    button_texts = [
        button.text
        for row in keyboard.as_markup().inline_keyboard
        for button in row
        if getattr(button, "text", None)
    ]

    assert "BTC" in text
    assert "USDT ERC20" in text
    assert "₿ BTC" in button_texts
    assert "USDT ERC-20" in button_texts
