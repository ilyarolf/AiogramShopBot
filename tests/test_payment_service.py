from decimal import Decimal
from types import SimpleNamespace

import pytest

from enums.bot_entity import BotEntity
from enums.cryptocurrency import Cryptocurrency
from enums.language import Language
from handlers.user.constants import UserStates
from handlers.user.my_profile import receive_top_up_amount
from services.payment import PaymentService
from utils.utils import get_text


class _State:
    def __init__(self, data=None):
        self._data = data or {}

    async def get_data(self):
        return dict(self._data)

    async def set_state(self, value=None):
        self._data["state"] = value

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def get_state(self):
        return self._data.get("state")


class _Bot:
    def __init__(self):
        self.edits = []

    async def edit_message_media(self, **kwargs):
        self.edits.append(kwargs)


class _Message:
    def __init__(self, text: str):
        self.text = text
        self.html_text = text
        self.bot = _Bot()
        self.from_user = SimpleNamespace(id=1)


@pytest.mark.parametrize(
    ("raw_amount", "expected"),
    [
        ("10", Decimal("10")),
        (" 10.50 ", Decimal("10.50")),
        ("-1", None),
        ("0", None),
        ("1.234", None),
        ("1e3", None),
        ("abc", None),
        ("", None),
    ],
)
def test_parse_fiat_amount_handles_invalid_values(raw_amount, expected):
    assert PaymentService._parse_fiat_amount(raw_amount) == expected


@pytest.mark.asyncio
async def test_receive_top_up_amount_answers_media_when_no_placeholder_message(monkeypatch):
    message = _Message("-10")
    state = _State()
    called = {}

    async def _fake_create(*args, **kwargs):
        return "media-object", SimpleNamespace(as_markup=lambda: "markup")

    async def _fake_answer_media(current_message, media, reply_markup):
        called["message"] = current_message
        called["media"] = media
        called["reply_markup"] = reply_markup

    monkeypatch.setattr("handlers.user.my_profile.PaymentService.create", _fake_create)
    monkeypatch.setattr("handlers.user.my_profile.NotificationService.answer_media", _fake_answer_media)

    await receive_top_up_amount(message, state, session=None, language=Language.EN)

    assert called["message"] is message
    assert called["media"] == "media-object"
    assert called["reply_markup"] == "markup"
    assert message.bot.edits == []


@pytest.mark.asyncio
async def test_stablecoin_invalid_amount_returns_localized_retry_screen(monkeypatch):
    state = _State({
        "cryptocurrency": Cryptocurrency.USDT_ERC20.value,
        "state": UserStates.top_up_amount
    })
    message = _Message("-10")

    async def _fake_get_by_tgid(*args, **kwargs):
        return SimpleNamespace(id=1)

    async def _fake_unexpired(*args, **kwargs):
        return 0

    monkeypatch.setattr("services.payment.UserRepository.get_by_tgid", _fake_get_by_tgid)
    monkeypatch.setattr("services.payment.PaymentRepository.get_unexpired_unpaid_payments", _fake_unexpired)

    media, _ = await PaymentService.create(message, None, state, session=None, language=Language.EN)

    assert get_text(Language.EN, BotEntity.USER, "top_up_balance_invalid_fiat_amount").split("\n")[0] in media.caption
