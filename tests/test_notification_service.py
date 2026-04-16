import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from types import SimpleNamespace

from services.notification import NotificationService


def _privacy_error() -> TelegramBadRequest:
    return TelegramBadRequest(
        method=SendMessage(chat_id=1, text="test"),
        message="Telegram server says - Bad Request: BUTTON_USER_PRIVACY_RESTRICTED"
    )


def test_strip_privacy_restricted_buttons_keeps_safe_buttons():
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="User", url="tg://user?id=123"),
        InlineKeyboardButton(text="Explorer", url="https://example.com/tx/1"),
        InlineKeyboardButton(text="Callback", callback_data="keep-me"),
    ]])

    sanitized = NotificationService._strip_privacy_restricted_buttons(markup)

    assert sanitized is not None
    assert len(sanitized.inline_keyboard[0]) == 2
    assert sanitized.inline_keyboard[0][0].text == "Explorer"
    assert sanitized.inline_keyboard[0][1].callback_data == "keep-me"


@pytest.mark.asyncio
async def test_privacy_fallback_retries_once_with_sanitized_markup():
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="User", url="tg://user?id=123"),
        InlineKeyboardButton(text="Safe", callback_data="ok"),
    ]])
    calls = []

    async def _execute(current_markup):
        calls.append(current_markup)
        if len(calls) == 1:
            raise _privacy_error()
        return "ok"

    result = await NotificationService._execute_with_privacy_fallback(
        operation_name="test",
        execute=_execute,
        reply_markup=markup,
        chat_id=42
    )

    assert result == "ok"
    assert len(calls) == 2
    assert calls[1] is not None
    assert len(calls[1].inline_keyboard[0]) == 1
    assert calls[1].inline_keyboard[0][0].callback_data == "ok"


@pytest.mark.asyncio
async def test_non_privacy_errors_are_not_swallowed():
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Safe", callback_data="ok"),
    ]])

    async def _execute(current_markup):
        raise TelegramBadRequest(
            method=SendMessage(chat_id=1, text="test"),
            message="Telegram server says - Bad Request: CHAT_NOT_FOUND"
        )

    with pytest.raises(TelegramBadRequest):
        await NotificationService._execute_with_privacy_fallback(
            operation_name="test",
            execute=_execute,
            reply_markup=markup,
            chat_id=42
        )


@pytest.mark.asyncio
async def test_preferred_user_link_uses_tgid_when_private_forwards_allowed(monkeypatch):
    class _Bot:
        def __init__(self, *args, **kwargs):
            self.session = SimpleNamespace(close=self._close)

        async def get_chat(self, user_id):
            return SimpleNamespace(has_private_forwards=False)

        async def _close(self):
            return None

    monkeypatch.setattr("services.notification.create_bot", lambda token: _Bot())

    link = await NotificationService.get_preferred_user_link(
        SimpleNamespace(telegram_id=123, telegram_username="demo")
    )

    assert link == "tg://user?id=123"


@pytest.mark.asyncio
async def test_preferred_user_link_falls_back_to_username(monkeypatch):
    class _Bot:
        def __init__(self, *args, **kwargs):
            self.session = SimpleNamespace(close=self._close)

        async def get_chat(self, user_id):
            return SimpleNamespace(has_private_forwards=True)

        async def _close(self):
            return None

    monkeypatch.setattr("services.notification.create_bot", lambda token: _Bot())

    link = await NotificationService.get_preferred_user_link(
        SimpleNamespace(telegram_id=123, telegram_username="demo")
    )

    assert link == "https://t.me/demo"
